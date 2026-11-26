"""Read and validate JSON test-case files."""

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Union

PathLike = Union[str, Path]


def load_test_cases(file_path: PathLike) -> List[Dict[str, Any]]:
    """Load non-empty test cases with positional inputs and expected values.

    Each case must contain exactly ``input`` (a non-empty JSON array) and
    ``expected`` (any JSON value). Errors identify the relevant file or case.
    """
    path = Path(file_path)
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise FileNotFoundError("Test cases file not found: {}".format(path))
    except OSError as error:
        raise ValueError("Could not read test cases file {}: {}".format(path, error))

    if not contents.strip():
        raise ValueError("Test cases file is empty: {}".format(path))

    try:
        test_cases = json.loads(contents, parse_constant=_reject_non_json_number)
    except json.JSONDecodeError as error:
        raise ValueError("Invalid JSON format in {}: {}".format(path, error))
    except ValueError as error:
        raise ValueError("Invalid JSON format in {}: {}".format(path, error))

    if not isinstance(test_cases, list):
        raise ValueError("Test cases file must contain a list")
    if not test_cases:
        raise ValueError("Test cases file cannot be empty")

    for index, test_case in enumerate(test_cases, start=1):
        _validate_test_case(test_case, index)
    return test_cases


def _validate_test_case(test_case: Any, index: int) -> None:
    """Validate one decoded case and include its one-based position in errors."""
    prefix = "Test case {}".format(index)
    if not isinstance(test_case, dict):
        raise ValueError("{} must be a dictionary".format(prefix))

    missing = {"input", "expected"} - test_case.keys()
    if missing:
        raise ValueError(
            "{} must contain required field(s): {}".format(
                prefix, ", ".join(sorted(missing))
            )
        )
    unexpected = test_case.keys() - {"input", "expected"}
    if unexpected:
        raise ValueError(
            "{} has Unexpected keys: {}".format(
                prefix, ", ".join(sorted(unexpected))
            )
        )

    arguments = test_case["input"]
    if not isinstance(arguments, list):
        raise ValueError("{}: 'input' must be a list".format(prefix))
    if not arguments:
        raise ValueError("{}: 'input' cannot be empty".format(prefix))
    if not all(_is_json_value(value) for value in arguments):
        raise ValueError("{}: 'input' contains an unsupported value".format(prefix))
    if not _is_json_value(test_case["expected"]):
        raise ValueError("{}: 'expected' contains an unsupported value".format(prefix))


def _is_json_value(value: Any) -> bool:
    """Return whether a value is composed only of standard JSON value types."""
    if value is None or isinstance(value, (str, bool, int)):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False


def _reject_non_json_number(value: str) -> None:
    raise ValueError("non-standard numeric value {!r}".format(value))
