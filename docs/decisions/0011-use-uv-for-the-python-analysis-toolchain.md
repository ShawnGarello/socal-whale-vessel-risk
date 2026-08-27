# 0011 — Use uv for the Python analysis toolchain

**Status:** Accepted
**Date:** 2026-08-26

## Context

M3 introduces the repository's first real Python package. The package needs one
reproducible way to declare, lock, install, check, test, and build its code. The
choice is constraining because later processing sessions need to share one
dependency graph and one set of commands rather than create slice-specific
environments.

The author's machine has Python 3.13.7 and uv 0.12.6. The ignored root virtual
environment was created while preparing this M3 foundation and contains useful
packages, but it is not a dependency declaration and cannot make a clean clone
reproducible.
Version 1 does not include CI or containers, so the local workflow itself must
be explicit and checkable.

## Decision

The analysis is a src-based Python 3.13 package under `analysis/`, managed by
uv. `analysis/pyproject.toml` is the dependency and tool configuration; the
generated `analysis/uv.lock` is committed. Runtime dependencies are separate
from development and benchmark dependency groups.

The local quality gates are:

- Ruff for formatting and linting;
- mypy in strict mode for package source;
- pytest for tests with answers known by construction;
- Hatchling as the PEP 517 build backend; and
- a real package module and console entry point for command-line work.

The supported runtime is `>=3.13,<3.14`. `python -m uv sync --locked` creates
the environment without changing the lock, and `python -m uv lock --check`
proves that the declaration and lock agree.

## Consequences

- A clean clone can reproduce the environment from two committed files without
  relying on the author's exploratory environment.
- Later slices add dependencies to the owning group and update the lock in the
  same commit. A package is not treated as available merely because it happens
  to be installed locally.
- Supporting only Python 3.13 keeps the initial matrix honest and small, but it
  excludes contributors on earlier Python versions. Expanding support requires
  running the complete checks on those versions first.
- Ruff replaces separate formatter, import-sorter, and linter dependencies.
- No automated remote gate exists. The commands remain local until a later
  milestone demonstrates a need for CI and records that scope change.

## Alternatives considered

**`venv`, pip, and requirements files.** Standard-library environment creation
is attractive, but separating direct requirements from a fully resolved lock
would require another tool or a hand-maintained pair of files. uv supplies both
from one project declaration.

**Poetry or PDM.** Both can manage and lock a package, but neither is installed,
and this package does not need their additional project-management surface.

**Black, isort, and Flake8.** Familiar and effective, but three tools and three
configurations provide no concrete benefit over Ruff for this package.

**The standard-library `unittest` runner.** It would avoid a development
dependency. Pytest was selected because concise parameterized tests and clear
failure output materially help the synthetic validation cases planned for M3;
the runner is not shipped at runtime.
