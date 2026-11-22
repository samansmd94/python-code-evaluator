def generate_report(results):

    passed = 0
    failed = 0

    print("=" * 40)
    print("         EVALUATION REPORT")
    print("=" * 40)

    for test_number, result in enumerate(results, start=1):

        print(f"\nTest {test_number}:")
        print(f'Input: {result["input"]}')
        print(f'Expected: {result["expected"]}')
        print(f'Actual: {result["actual"]}')

        if result["passed"]:
            print("Status: PASSED")
            # Update passed counter
            passed+=1
        else:
            print("Status: FAILED")
            # Update failed counter
            failed+=1

    # Calculate total tests
    total_tests = len(results)
    # Calculate success rate
    success_rate = (passed/total_tests)*100 if total_tests else 0

    print("\n" + "=" * 40)
    # Print summary
    print(f'Total tests: {total_tests}')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print(f'Success rate: {success_rate:.2f}%')
    print("=" * 40)