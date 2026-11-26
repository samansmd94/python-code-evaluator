"""Coordinate execution and comparison for a collection of test cases."""

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Optional

from .runner import run_function
from .comparator import compare_results


def evaluate(
    function: Callable[..., Any],
    test_cases: Iterable[Mapping[str, Any]],
    *,
    tolerance: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Evaluate ``function`` against cases with ``input`` and ``expected``.

    Each result retains the original public fields and adds a ``status`` value
    of ``passed``, ``failed``, or ``error``.
    """
    results = []

    for test_number, test_case in enumerate(test_cases, start=1):
        arguments = test_case["input"]
        expected = test_case["expected"]

        execution = run_function(function, arguments)

        actual = execution["result"]
        error = execution["error"]

        if error is not None:
            passed = False
            status = "error"
        else:
            passed = compare_results(actual, expected, tolerance=tolerance)
            status = "passed" if passed else "failed"

        results.append({
            "input": arguments,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "error": error,
            "status": status,
            "test_number": test_number,
        })

    return results
