"""Command-line interface for evaluating registered trusted functions."""

import argparse
import logging
import math
import sys
from typing import Optional, Sequence

from .engine import evaluate
from .loader import load_test_cases
from .registry import available_functions, get_function
from .reporter import generate_report, report_json


def build_parser() -> argparse.ArgumentParser:
    """Create the command parser used by ``python -m evaluator``."""
    parser = argparse.ArgumentParser(
        prog="python -m evaluator",
        description="Evaluate trusted, project-defined Python functions.",
    )
    parser.add_argument("--verbose", action="store_true", help="show execution logs")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="run an evaluation")
    run_parser.add_argument(
        "--function", required=True, choices=sorted(available_functions()),
        help="registered function to evaluate",
    )
    run_parser.add_argument("--tests", required=True, help="path to a JSON test-case file")
    run_parser.add_argument(
        "--tolerance", type=_non_negative_float, default=None,
        help="optional numeric tolerance; default comparison is exact",
    )
    run_parser.add_argument(
        "--format", choices=("text", "json"), default="text",
        help="report format (default: text)",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        function = get_function(args.function)
        test_cases = load_test_cases(args.tests)
    except (FileNotFoundError, ValueError, KeyError) as error:
        print("Error: {}".format(error), file=sys.stderr)
        return 2

    results = evaluate(function, test_cases, tolerance=args.tolerance)
    if args.format == "json":
        print(report_json(results))
    else:
        generate_report(results)
    return 0 if all(result["passed"] for result in results) else 1


def _non_negative_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number")
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite, non-negative number")
    return number
