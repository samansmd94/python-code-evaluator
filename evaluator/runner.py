"""Execute one trusted, project-defined function call."""

import logging
from collections.abc import Callable, Sequence
from typing import Any

logger = logging.getLogger(__name__)


def run_function(
    function: Callable[..., Any], arguments: Sequence[Any]
) -> dict[str, Any]:
    """Run ``function`` with positional arguments and capture ordinary errors.

    This helper is for trusted local functions; catching exceptions does not
    make arbitrary Python code safe to execute.
    """
    try:
        result = function(*arguments)

        return {
            "result": result,
            "error": None,
        }

    except Exception as error:
        function_name = getattr(function, "__name__", type(function).__name__)
        logger.warning("Execution failed for %s: %s", function_name, error)
        return {
            "result": None,
            "error": str(error),
        }
