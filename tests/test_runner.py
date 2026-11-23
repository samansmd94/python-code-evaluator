from evaluator.runner import run_function


def test_run_function_with_two_arguments():
    def add(a, b):
        return a + b

    result = run_function(add, (2, 3))

    assert result["result"] == 5
    assert result["error"] is None


def test_run_function_with_string_arguments():
    def greet(name):
        return f"Hello, {name}!"

    result = run_function(greet, ("Sam",))

    assert result["result"] == "Hello, Sam!"
    assert result["error"] is None


def test_run_function_handles_zero_division():
    def divide(a, b):
        return a / b

    result = run_function(divide, (10, 0))

    assert result["result"] is None
    assert result["error"] == "division by zero"


def test_run_function_handles_invalid_operation():
    def convert(value):
        return int(value)

    result = run_function(convert, ("hello",))

    assert result["result"] is None
    assert "invalid literal" in result["error"]