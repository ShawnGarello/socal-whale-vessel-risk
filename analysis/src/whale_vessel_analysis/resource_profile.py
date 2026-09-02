"""Direct-process resource profiling for development evidence.

This module is not an analytical processing step. It imports a Python CLI in an
isolated child, pauses after imports to establish a baseline, and writes a
path-free JSON resource report. The optional psutil benchmark dependency is
required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, TypedDict

import psutil

_READY_LINE = "WHALERESOURCEPROFILE_READY"
_GIB = 1024**3
_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
_MODULE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
_BOOTSTRAP = f"""
import importlib
import json
import sys

module = importlib.import_module(sys.argv[1])
arguments = json.loads(sys.argv[2])
sys.stdout.write({_READY_LINE!r} + "\\n")
sys.stdout.flush()
if sys.stdin.readline().strip() != "GO":
    raise SystemExit(125)
result = module.main(arguments)
raise SystemExit(0 if result is None else result)
"""


class _ProcessMemory(TypedDict):
    rss: int
    private: int | None
    os_peak_working_set: int | None


class _TreeSample(TypedDict):
    root: _ProcessMemory
    application: _ProcessMemory
    application_pid: int
    descendants_rss: int
    descendants_private: int | None
    tree_rss: int
    tree_private: int | None
    descendant_count: int


class ResourcePreflightError(ValueError):
    """Raised before the target starts when required headroom is unavailable."""


def _memory(process: psutil.Process) -> _ProcessMemory:
    info = process.memory_info()
    private = getattr(info, "private", None)
    os_peak = getattr(info, "peak_wset", None)
    return {
        "rss": int(info.rss),
        "private": None if private is None else int(private),
        "os_peak_working_set": None if os_peak is None else int(os_peak),
    }


def _sum_optional(values: list[int | None]) -> int | None:
    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def _sample_tree(root: psutil.Process) -> _TreeSample:
    root_memory = _memory(root)
    descendants: list[tuple[psutil.Process, _ProcessMemory]] = []
    for process in root.children(recursive=True):
        try:
            descendants.append((process, _memory(process)))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    candidates = [(root, root_memory), *descendants]
    application_process, application_memory = max(
        candidates,
        key=lambda item: (
            item[1]["private"] if item[1]["private"] is not None else item[1]["rss"]
        ),
    )
    descendant_memories = [memory for _, memory in descendants]
    private_values = [
        root_memory["private"],
        *[m["private"] for m in descendant_memories],
    ]
    return {
        "root": root_memory,
        "application": application_memory,
        "application_pid": application_process.pid,
        "descendants_rss": sum(memory["rss"] for memory in descendant_memories),
        "descendants_private": _sum_optional(
            [memory["private"] for memory in descendant_memories]
        ),
        "tree_rss": root_memory["rss"]
        + sum(memory["rss"] for memory in descendant_memories),
        "tree_private": _sum_optional(private_values),
        "descendant_count": len(descendants),
    }


def _disk_bytes(root: Path | None) -> int | None:
    if root is None:
        return None
    total = 0
    if not root.exists():
        return total
    for directory, _, files in os.walk(root):
        for filename in files:
            try:
                total += (Path(directory) / filename).stat().st_size
            except FileNotFoundError:
                continue
    return total


def _maximum(current: int | None, candidate: int | None) -> int | None:
    if current is None:
        return candidate
    if candidate is None:
        return current
    return max(current, candidate)


def _write_console(stream: Any, value: str) -> None:
    encoding = stream.encoding or "utf-8"
    stream.write(value.encode(encoding, errors="replace").decode(encoding))


def _existing_ancestor(path: Path) -> Path:
    candidate = path.resolve()
    while not candidate.exists():
        if candidate.parent == candidate:
            raise ResourcePreflightError("no existing ancestor for disk preflight")
        candidate = candidate.parent
    return candidate


def _preflight(
    *,
    disk_path: Path,
    minimum_free_memory_bytes: int,
    minimum_free_disk_bytes: int,
) -> dict[str, int]:
    available_memory = int(psutil.virtual_memory().available)
    free_disk = int(shutil.disk_usage(_existing_ancestor(disk_path)).free)
    if available_memory < minimum_free_memory_bytes:
        raise ResourcePreflightError(
            "resource preflight refused the target: available memory is below "
            f"the required {minimum_free_memory_bytes} bytes"
        )
    if free_disk < minimum_free_disk_bytes:
        raise ResourcePreflightError(
            "resource preflight refused the target: free disk is below "
            f"the required {minimum_free_disk_bytes} bytes"
        )
    return {
        "available_memory_bytes": available_memory,
        "free_disk_bytes": free_disk,
        "minimum_free_memory_bytes": minimum_free_memory_bytes,
        "minimum_free_disk_bytes": minimum_free_disk_bytes,
    }


def _profile(
    *,
    module: str,
    module_arguments: list[str],
    output_path: Path,
    label: str,
    disk_root: Path | None,
    spill_root: Path | None,
    sample_interval_seconds: float = 0.1,
    baseline_samples: int = 20,
    minimum_free_memory_bytes: int = 0,
    minimum_free_disk_bytes: int = 0,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"profile output already exists: {output_path}")
    if _MODULE_PATTERN.fullmatch(module) is None:
        raise ValueError("target module must be a dotted Python module name")
    if _LABEL_PATTERN.fullmatch(label) is None:
        raise ValueError("profile label must be a short non-sensitive identifier")
    if sample_interval_seconds < 0.05:
        raise ValueError("sample interval must be at least 0.05 seconds")
    if baseline_samples < 3:
        raise ValueError("baseline samples must be at least 3")

    preflight = _preflight(
        disk_path=disk_root if disk_root is not None else output_path.parent,
        minimum_free_memory_bytes=minimum_free_memory_bytes,
        minimum_free_disk_bytes=minimum_free_disk_bytes,
    )

    disk_baseline = _disk_bytes(disk_root)
    spill_baseline = _disk_bytes(spill_root)
    started = time.perf_counter()
    child = subprocess.Popen(
        [sys.executable, "-c", _BOOTSTRAP, module, json.dumps(module_arguments)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert child.stdout is not None
    ready = child.stdout.readline().rstrip("\r\n")
    if ready != _READY_LINE:
        stdout, stderr = child.communicate()
        raise RuntimeError(
            "profile target did not reach its post-import readiness barrier; "
            f"exit={child.returncode}, stdout_bytes={len(ready + stdout)}, "
            f"stderr_bytes={len(stderr)}"
        )

    root = psutil.Process(child.pid)
    baseline: list[_TreeSample] = []
    for _ in range(baseline_samples):
        baseline.append(_sample_tree(root))
        time.sleep(0.05)

    application_pid = statistics.mode(sample["application_pid"] for sample in baseline)
    application_baseline_rss = int(
        statistics.median(
            sample["application"]["rss"]
            for sample in baseline
            if sample["application_pid"] == application_pid
        )
    )
    baseline_private_values = [
        sample["application"]["private"]
        for sample in baseline
        if sample["application_pid"] == application_pid
        and sample["application"]["private"] is not None
    ]
    application_baseline_private = (
        int(statistics.median(baseline_private_values))
        if baseline_private_values
        else None
    )
    tree_baseline_rss = int(statistics.median(s["tree_rss"] for s in baseline))
    root_baseline_rss = int(
        statistics.median(sample["root"]["rss"] for sample in baseline)
    )
    root_baseline_private_values = [
        sample["root"]["private"]
        for sample in baseline
        if sample["root"]["private"] is not None
    ]
    root_baseline_private = (
        int(statistics.median(root_baseline_private_values))
        if root_baseline_private_values
        else None
    )
    tree_private_values = [
        sample["tree_private"]
        for sample in baseline
        if sample["tree_private"] is not None
    ]
    tree_baseline_private = (
        int(statistics.median(tree_private_values)) if tree_private_values else None
    )

    application_peak_rss = application_baseline_rss
    application_peak_private = application_baseline_private
    application_os_peak = next(
        (
            sample["application"]["os_peak_working_set"]
            for sample in reversed(baseline)
            if sample["application_pid"] == application_pid
        ),
        None,
    )
    root_peak_rss = max(sample["root"]["rss"] for sample in baseline)
    root_os_peak = baseline[-1]["root"]["os_peak_working_set"]
    root_peak_private = _maximum(
        None,
        max(
            (
                sample["root"]["private"]
                for sample in baseline
                if sample["root"]["private"] is not None
            ),
            default=None,
        ),
    )
    tree_peak_rss = max(sample["tree_rss"] for sample in baseline)
    tree_peak_private = max(
        (
            sample["tree_private"]
            for sample in baseline
            if sample["tree_private"] is not None
        ),
        default=None,
    )
    maximum_descendants = max(sample["descendant_count"] for sample in baseline)
    descendants_peak_rss = max(sample["descendants_rss"] for sample in baseline)
    descendants_peak_private = max(
        (
            sample["descendants_private"]
            for sample in baseline
            if sample["descendants_private"] is not None
        ),
        default=None,
    )
    disk_peak = disk_baseline
    spill_peak = spill_baseline
    profiler = psutil.Process()
    profiler_peak_rss = profiler.memory_info().rss
    operation_started = time.perf_counter()
    assert child.stdin is not None
    assert child.stderr is not None
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def drain(stream: Any, chunks: list[str]) -> None:
        while chunk := stream.read(8192):
            chunks.append(chunk)

    stdout_thread = threading.Thread(
        target=drain, args=(child.stdout, stdout_chunks), daemon=True
    )
    stderr_thread = threading.Thread(
        target=drain, args=(child.stderr, stderr_chunks), daemon=True
    )
    stdout_thread.start()
    stderr_thread.start()
    child.stdin.write("GO\n")
    child.stdin.flush()
    child.stdin.close()

    sample_count = 0
    while child.poll() is None:
        try:
            sample = _sample_tree(root)
        except psutil.NoSuchProcess:
            break
        sample_count += 1
        if sample["application_pid"] == application_pid:
            application_peak_rss = max(
                application_peak_rss, sample["application"]["rss"]
            )
            application_peak_private = _maximum(
                application_peak_private, sample["application"]["private"]
            )
            application_os_peak = _maximum(
                application_os_peak,
                sample["application"]["os_peak_working_set"],
            )
        root_peak_rss = max(root_peak_rss, sample["root"]["rss"])
        root_peak_private = _maximum(root_peak_private, sample["root"]["private"])
        root_os_peak = _maximum(root_os_peak, sample["root"]["os_peak_working_set"])
        tree_peak_rss = max(tree_peak_rss, sample["tree_rss"])
        tree_peak_private = _maximum(tree_peak_private, sample["tree_private"])
        maximum_descendants = max(maximum_descendants, sample["descendant_count"])
        descendants_peak_rss = max(descendants_peak_rss, sample["descendants_rss"])
        descendants_peak_private = _maximum(
            descendants_peak_private, sample["descendants_private"]
        )
        disk_peak = _maximum(disk_peak, _disk_bytes(disk_root))
        spill_peak = _maximum(spill_peak, _disk_bytes(spill_root))
        profiler_peak_rss = max(profiler_peak_rss, profiler.memory_info().rss)
        time.sleep(sample_interval_seconds)

    operation_elapsed = time.perf_counter() - operation_started
    child.wait()
    stdout_thread.join()
    stderr_thread.join()
    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)
    disk_final = _disk_bytes(disk_root)
    spill_final = _disk_bytes(spill_root)
    disk_peak = _maximum(disk_peak, disk_final)
    spill_peak = _maximum(spill_peak, spill_final)
    if stdout:
        _write_console(sys.stdout, stdout)
    if stderr:
        _write_console(sys.stderr, stderr)

    report: dict[str, Any] = {
        "contract": "resource-profile-v1",
        "label": label,
        "target_module": module,
        "exit_code": child.returncode,
        "preflight": preflight,
        "measurement": {
            "platform": sys.platform,
            "sample_interval_ms": round(sample_interval_seconds * 1000),
            "sample_count": sample_count,
            "baseline_barrier_samples": baseline_samples,
            "baseline_definition": (
                "median application memory after target-module import while paused "
                "before the operation"
            ),
            "rss_definition": "operating-system resident working set",
            "private_definition": (
                "Windows committed private bytes; null when unavailable"
            ),
            "process_tree_sum_warning": (
                "per-process RSS sums can double-count shared pages"
            ),
            "profiler_process_excluded_from_target_and_tree": True,
            "operation_elapsed_seconds": operation_elapsed,
            "elapsed_seconds_including_import_and_barrier": (
                time.perf_counter() - started
            ),
        },
        "memory_bytes": {
            "application_baseline_rss": application_baseline_rss,
            "application_peak_sampled_rss": application_peak_rss,
            "application_peak_os_counter_working_set": application_os_peak,
            "application_peak_rss_increase_over_baseline": (
                application_peak_rss - application_baseline_rss
            ),
            "application_baseline_private": application_baseline_private,
            "application_peak_sampled_private": application_peak_private,
            "application_pid_is_direct_spawn_root": application_pid == child.pid,
            "direct_spawn_root_baseline_rss": root_baseline_rss,
            "direct_spawn_root_peak_sampled_rss": root_peak_rss,
            "direct_spawn_root_peak_os_counter_working_set": root_os_peak,
            "direct_spawn_root_baseline_private": root_baseline_private,
            "direct_spawn_root_peak_sampled_private": root_peak_private,
            "descendants_peak_sampled_rss_sum": descendants_peak_rss,
            "descendants_peak_sampled_private_sum": descendants_peak_private,
            "process_tree_baseline_rss_sum": tree_baseline_rss,
            "process_tree_peak_sampled_rss_sum": tree_peak_rss,
            "process_tree_peak_rss_increase_over_baseline": (
                tree_peak_rss - tree_baseline_rss
            ),
            "process_tree_baseline_private_sum": tree_baseline_private,
            "process_tree_peak_sampled_private_sum": tree_peak_private,
            "peak_tree_minus_peak_application_rss": (
                tree_peak_rss - application_peak_rss
            ),
            "maximum_live_descendant_count": maximum_descendants,
            "profiler_peak_rss": profiler_peak_rss,
        },
        "disk_bytes": {
            "baseline": disk_baseline,
            "peak_sampled": disk_peak,
            "final": disk_final,
            "peak_increase": (
                None
                if disk_peak is None or disk_baseline is None
                else disk_peak - disk_baseline
            ),
        },
        "spill_bytes": {
            "baseline": spill_baseline,
            "peak_sampled": spill_peak,
            "final": spill_final,
            "peak_increase": (
                None
                if spill_peak is None or spill_baseline is None
                else spill_peak - spill_baseline
            ),
        },
        "target_output": {
            "stdout_bytes": len(stdout.encode("utf-8")),
            "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
            "stderr_bytes": len(stderr.encode("utf-8")),
            "stderr_sha256": hashlib.sha256(stderr.encode("utf-8")).hexdigest(),
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    return report


def _module_name(value: str) -> str:
    if _MODULE_PATTERN.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("must be a dotted Python module name")
    return value


def _profile_label(value: str) -> str:
    if _LABEL_PATTERN.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("must be a short non-sensitive identifier")
    return value


def _nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _sample_interval_ms(value: str) -> int:
    parsed = int(value)
    if not 50 <= parsed <= 1000:
        raise argparse.ArgumentTypeError("must be between 50 and 1000")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--module",
        required=True,
        type=_module_name,
        help="Python CLI module to import",
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label", required=True, type=_profile_label)
    parser.add_argument("--disk-root", type=Path)
    parser.add_argument("--spill-root", type=Path)
    parser.add_argument(
        "--expected-exit-code",
        type=int,
        action="append",
        default=[0],
        help="target exit code treated as a successful profiling run; repeatable",
    )
    parser.add_argument(
        "--minimum-free-memory-gib", type=_nonnegative_float, default=0.0
    )
    parser.add_argument("--minimum-free-disk-gib", type=_nonnegative_float, default=0.0)
    parser.add_argument("--sample-interval-ms", type=_sample_interval_ms, default=100)
    parser.add_argument(
        "target_arguments",
        nargs=argparse.REMAINDER,
        help="target arguments after --",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target_arguments = list(args.target_arguments)
    if target_arguments[:1] == ["--"]:
        target_arguments.pop(0)
    report = _profile(
        module=args.module,
        module_arguments=target_arguments,
        output_path=args.output,
        label=args.label,
        disk_root=args.disk_root,
        spill_root=args.spill_root,
        sample_interval_seconds=args.sample_interval_ms / 1000,
        minimum_free_memory_bytes=round(args.minimum_free_memory_gib * _GIB),
        minimum_free_disk_bytes=round(args.minimum_free_disk_gib * _GIB),
    )
    target_exit_code = int(report["exit_code"])
    return 0 if target_exit_code in args.expected_exit_code else target_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
