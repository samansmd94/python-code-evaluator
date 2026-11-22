from evaluator.engine import evaluate
from evaluator.reporter import generate_report
from exercises.basic_exercises import add

test_cases = [
    {"input": (2, 3), "expected": 5},
    {"input": (10, 20), "expected": 30},
    {"input": (-5, 5), "expected": 0},
    {"input": (0, 0), "expected": 0},
    {"input": (2, 3), "expected": 10}
]

results = evaluate(add, test_cases)

generate_report(results)

# from evaluator.comparator import compare_results

# print(compare_results(5, 5))
# print(compare_results(10, 20))
# print(compare_results("hello", "hello"))

# from exercises.basic_exercises import add
# from evaluator.runner import run_function

# result = run_function(add, (2, 3))

# print(result)

# test_cases = [
#     {"input": (2, 3), "expected": 5},
#     {"input": (10, 20), "expected": 30},
#     {"input": (-5, 5), "expected": 0},
#     {"input": (0, 0), "expected": 0},
#     {"input": (2, 3), "expected": 10}
# ]

# print('='*40)

# print('         EVALUATION REPORT')

# print('='*40)

# passed=0
# failed=0

# for i, case in enumerate(test_cases, start=1):
#     result = add(*case["input"])
    
#     print(f'\nTest {i}:')
#     print(f'Input: {case["input"]}')
#     print(f'Expected: {case["expected"]}')
#     print(f'Actual: {result}')
    
#     if result == case["expected"]:
#         print('Status: PASSED')
#         passed+=1
#     else:
#         print('Status: FAILED')
#         failed+=1

# total_tests = len(test_cases)
# success_rate=(passed/total_tests)*100

# print("\n" + '=' * 40)
# print(f'Total_tests = {total_tests}')
# print('Passed: ', passed)
# print('Failed: ', failed)
# print(f'Success rate: {success_rate:.2f}')
# print('=' * 40)