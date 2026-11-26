"""Registry of trusted functions that the CLI is allowed to evaluate."""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Any, Dict

from exercises.basic_exercises import add, divide, greet

_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "add": add,
    "divide": divide,
    "greet": greet,
}


def register_function(name: str, function: Callable[..., Any]) -> None:
    """Register a trusted local function under a safe CLI identifier."""
    if not name or not name.isidentifier():
        raise ValueError("Function name must be a non-empty Python identifier")
    if name in _FUNCTIONS:
        raise ValueError("Function {!r} is already registered".format(name))
    if not callable(function):
        raise TypeError("Registered function must be callable")
    _FUNCTIONS[name] = function


def get_function(name: str) -> Callable[..., Any]:
    """Return a registered trusted function or raise a clear lookup error."""
    try:
        return _FUNCTIONS[name]
    except KeyError:
        raise KeyError("Unknown function {!r}".format(name))


def available_functions() -> Mapping[str, Callable[..., Any]]:
    """Return a read-only snapshot of registered functions."""
    return MappingProxyType(dict(_FUNCTIONS))
