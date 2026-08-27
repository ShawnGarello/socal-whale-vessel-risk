"""Command-line boundary for the offline analysis package."""

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build the package command-line parser."""
    return argparse.ArgumentParser(
        prog="whale-vessel-analysis",
        description=(
            "Validate inputs and configuration for the Southern California "
            "whale-vessel overlap processing workflow."
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    build_parser().parse_args(argv)
    return 0
