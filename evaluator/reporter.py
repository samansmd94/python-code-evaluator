def generate_report(results):

    passed = 0
    failed = 0
    errors = 0

    print("=" * 40)
    print("         EVALUATION REPORT")
    print("=" * 40)

    for test_number, result in enumerate(results, start=1):

        print(f"\nTest {test_number}:")
        print(f'Input: {result["input"]}')
        print(f'Expected: {result["expected"]}')
        print(f'Actual: {result["actual"]}')
        if result.get("error") is not None:
            print(f'Error: {result["error"]}')
            errors += 1

        if result["passed"]:
            print("Status: PASSED")
            passed += 1
        else:
            print("Status: FAILED")
            failed += 1

    total_tests = len(results)
    success_rate = (passed/total_tests)*100 if total_tests else 0

    print("\n" + "=" * 40)
    print(f'Total tests: {total_tests}')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print(f'Errors: {errors}')
    print(f'Success rate: {success_rate:.2f}%')
    print("=" * 40)

def generate_overall_summary(all_results):
    total_tests = 0
    passed = 0
    failed = 0
    errors = 0

    for results in all_results:
        total_tests += len(results)

        for result in results:
            if result["passed"]:
                passed += 1
            else:
                failed += 1

            if result.get("error") is not None:
                errors += 1

    success_rate = (passed / total_tests) * 100 if total_tests else 0

    print("\n" + "=" * 40)
    print("         OVERALL SUMMARY")
    print("=" * 40)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print(f"Success rate: {success_rate:.2f}%")
    print("=" * 40)