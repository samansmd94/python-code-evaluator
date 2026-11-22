from .runner import run_function
from .comparator import compare_results


def evaluate(function, test_cases):

    results = []

    for test_case in test_cases:

        # Extract input
        arguments = test_case['input']
        # Extract expected result
        expected = test_case['expected']

        # Execute function
        actual = run_function(function, arguments)

        # Compare results
        passed = compare_results(actual, expected)

        # Store evaluation result
        results.append({
            "input": arguments,
            "expected": expected,
            "actual": actual,
            "passed": passed
        })

    return results
