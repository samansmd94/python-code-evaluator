from evaluator.engine import evaluate

def add(a, b):
    return a + b

def test_evaluate_all_passing_cases():
    test_cases = [
        {"input": (2, 3), "expected": 5},
        {"input": (10, 20), "expected": 30},
    ]

    results = evaluate(add, test_cases)

    assert len(results) == 2
    assert results[0]["passed"] is True
    assert results[1]["passed"] is True
    assert results[0]["error"] is None
    assert results[1]["error"] is None
    assert all("error" in result for result in results)

def test_evaluate_with_failing_cases():
    test_cases = [
        {"input": (2, 3), "expected": 5},
        {"input": (10, 20), "expected": 10},
    ]

    results = evaluate(add, test_cases)

    assert results[0]["passed"] is True
    assert results[1]["passed"] is False
    assert results[0]["error"] is None
    assert results[1]["error"] is None

def test_evaluate_returns_correct_actual_value():
    test_cases = [
        {"input": (4, 6), "expected": 10},
    ]

    results = evaluate(add, test_cases)

    assert results[0]["actual"] == 10
    assert results[0]["error"] is None

def test_evaluate_handles_execution_error():
    def divide(a, b):
        return a / b

    test_cases = [
        {"input": (10, 0), "expected": 5},
    ]

    results = evaluate(divide, test_cases)

    assert results[0]["passed"] is False
    assert results[0]["actual"] is None
    assert results[0]["error"] is not None

def test_evaluate_accepts_string_that_looks_like_error():
    def get_message():
        return "division by zero"

    test_cases = [
        {"input": (), "expected": "division by zero"},
    ]

    results = evaluate(get_message, test_cases)

    assert results[0]["passed"] is True
    assert results[0]["actual"] == "division by zero"
    assert results[0]["error"] is None

def test_evaluate_string_function():
    def greet(name):
        return f"Hello {name}"

    test_cases = [
        {
            "input": ["Saman"],
            "expected": "Hello Saman"
        }
    ]

    results = evaluate(greet, test_cases)

    assert results[0]["actual"] == "Hello Saman"
    assert results[0]["passed"] is True
    assert results[0]["error"] is None

def test_evaluate_none_returning_function():
    def do_nothing():
        return None

    test_cases = [
        {
            "input": [],
            "expected": None
        }
    ]

    results = evaluate(do_nothing, test_cases)

    assert results[0]["actual"] is None
    assert results[0]["passed"] is True
    assert results[0]["error"] is None
