"""Build machine-readable evaluation summaries and print readable reports."""

import json
from typing import Any, Dict, Iterable, Mapping


def summarize_results(results: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Return deterministic counts and individual results for one evaluation."""
    result_list = [dict(result) for result in results]
    errors = sum(1 for result in result_list if result.get("error") is not None)
    passed = sum(1 for result in result_list if result.get("passed", False))
    failed = sum(
        1 for result in result_list
        if not result.get("passed", False) and result.get("error") is None
    )
    total = len(result_list)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "success_rate": (passed / total * 100) if total else 0.0,
        "results": result_list,
    }


def generate_report(results: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Print a readable report and return its structured summary."""
    summary = summarize_results(results)
    print("=" * 40)
    print("         EVALUATION REPORT")
    print("=" * 40)

    for number, result in enumerate(summary["results"], start=1):
        print("\nTest {}:".format(number))
        print("Input: {}".format(result.get("input")))
        print("Expected: {}".format(result.get("expected")))
        print("Actual: {}".format(result.get("actual")))
        if result.get("error") is not None:
            print("Error: {}".format(result["error"]))
        status = result.get("status")
        if status is None:
            status = "passed" if result.get("passed", False) else "failed"
        print("Status: {}".format(status.upper()))

    _print_summary(summary)
    return summary


def generate_overall_summary(
    all_results: Iterable[Iterable[Mapping[str, Any]]],
) -> Dict[str, Any]:
    """Print and return counts combined across multiple evaluations."""
    combined = [result for results in all_results for result in results]
    summary = summarize_results(combined)
    print("\n" + "=" * 40)
    print("         OVERALL SUMMARY")
    print("=" * 40)
    _print_summary_lines(summary)
    return summary


def report_json(results: Iterable[Mapping[str, Any]], *, indent: int = 2) -> str:
    """Serialize a report as stable JSON for other tools."""
    return json.dumps(
        summarize_results(results),
        ensure_ascii=False,
        allow_nan=False,
        indent=indent,
        sort_keys=True,
    )


def _print_summary(summary: Mapping[str, Any]) -> None:
    print("\n" + "=" * 40)
    _print_summary_lines(summary)


def _print_summary_lines(summary: Mapping[str, Any]) -> None:
    print("Total tests: {}".format(summary["total"]))
    print("Passed: {}".format(summary["passed"]))
    print("Failed: {}".format(summary["failed"]))
    print("Errors: {}".format(summary["errors"]))
    print("Success rate: {:.2f}%".format(summary["success_rate"]))
    print("=" * 40)
