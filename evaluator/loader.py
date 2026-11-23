import json


def load_test_cases(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            test_cases = json.load(file)

        if not isinstance(test_cases, list):
            raise ValueError("Test cases file must contain a list")

        if not test_cases:
            raise ValueError("Test cases file cannot be empty")

        for test_case in test_cases:
            if not isinstance(test_case, dict):
                raise ValueError("Each test case must be a dictionary")

            if "input" not in test_case or "expected" not in test_case:
                raise ValueError("Each test case must contain 'input' and 'expected'")

            unexpected_keys = test_case.keys() - {"input", "expected"}

            if unexpected_keys:
                raise ValueError(
                    f"Unexpected keys in test case: {', '.join(sorted(unexpected_keys))}"
                )

            if not isinstance(test_case["input"], list):
                raise ValueError("'input' must be a list")

            if not test_case["input"]:
                raise ValueError("'input' cannot be empty")

        return test_cases

    except FileNotFoundError:
        raise FileNotFoundError(f"Test cases file not found: {file_path}")

    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON format in {file_path}: {error}")