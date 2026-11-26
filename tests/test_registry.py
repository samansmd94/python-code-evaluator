import pytest

from evaluator.registry import (
    available_functions,
    get_function,
    register_function,
)


def test_default_registry_exposes_only_named_project_functions():
    functions = available_functions()
    assert set(functions) == {"add", "divide", "greet"}
    assert functions["add"](2, 3) == 5


def test_registered_function_can_be_retrieved():
    def custom_example(value):
        return value

    register_function("custom_example_for_test", custom_example)
    assert get_function("custom_example_for_test") is custom_example


def test_registry_rejects_invalid_and_duplicate_entries():
    with pytest.raises(ValueError, match="identifier"):
        register_function("unsafe.name", lambda: None)
    with pytest.raises(ValueError, match="already registered"):
        register_function("add", lambda: None)
    with pytest.raises(TypeError, match="callable"):
        register_function("not_callable", None)
