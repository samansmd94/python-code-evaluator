from .runner import run_function
from .comparator import compare_results


def evaluate(function, test_cases):
    results = []

    for test_case in test_cases:
        arguments = test_case['input']
        expected = test_case['expected']

        execution = run_function(function, arguments)

        actual = execution["result"]
        error = execution["error"]

        if error is not None:
            passed = False
        else:
            passed = compare_results(actual, expected)

        results.append({
            "input": arguments,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "error": error
        })

    return results