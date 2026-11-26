"""Comparison helpers for actual and expected function results."""

import math
from typing import Any, Optional


def compare_results(
    actual: Any, expected: Any, *, tolerance: Optional[float] = None
) -> bool:
    """Compare values exactly by default, optionally allowing numeric tolerance.

    When tolerance is provided, numeric leaves in lists and dictionaries are
    compared with :func:`math.isclose`; containers must have matching shape
    and keys. Booleans are not treated as numbers for tolerance comparison.
    """
    if tolerance is None:
        return actual == expected
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")

    if _is_number(actual) and _is_number(expected):
        return math.isclose(actual, expected, rel_tol=tolerance, abs_tol=tolerance)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            compare_results(a, e, tolerance=tolerance)
            for a, e in zip(actual, expected)
        )
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            compare_results(actual[key], expected[key], tolerance=tolerance)
            for key in actual
        )
    return type(actual) is type(expected) and actual == expected


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


