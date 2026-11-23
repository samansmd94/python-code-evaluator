from evaluator.engine import evaluate
from evaluator.reporter import generate_report, generate_overall_summary
from evaluator.loader import load_test_cases
from exercises.basic_exercises import add, divide, greet


def main():
    # Load test cases
    add_test_cases = load_test_cases("test_cases/addition.json")
    divide_test_cases = load_test_cases("test_cases/division.json")
    greeting_test_cases = load_test_cases("test_cases/greeting.json")

    # Evaluate functions
    add_results = evaluate(add, add_test_cases)
    divide_results = evaluate(divide, divide_test_cases)
    greeting_results = evaluate(greet, greeting_test_cases)

    # Generate individual reports
    print("\nADDITION RESULTS")
    generate_report(add_results)

    print("\nDIVISION RESULTS")
    generate_report(divide_results)

    print("\nGREETING RESULTS")
    generate_report(greeting_results)

    # Generate overall summary
    all_results = [
        add_results,
        divide_results,
        greeting_results
    ]

    generate_overall_summary(all_results)


if __name__ == "__main__":
    main()