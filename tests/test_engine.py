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

def test_evaluate_with_failing_cases():
    test_cases = [
        {"input": (2, 3), "expected": 5},
        {"input": (10, 20), "expected": 10},
    ]

    results = evaluate(add, test_cases)

    assert results[0]["passed"] is True
    assert results[1]["passed"] is False

def test_evaluate_returns_correct_actual_value():
    test_cases = [
        {"input": (4, 6), "expected": 10},
    ]

    results = evaluate(add, test_cases)

    assert results[0]["actual"] == 10