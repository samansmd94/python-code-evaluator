import json
import pytest
from evaluator.loader import load_test_cases


def test_load_test_cases(tmp_path):
    test_data = [
        {"input": [2, 3], "expected": 5},
        {"input": [10, 20], "expected": 30}
    ]

    file_path = tmp_path / "test_cases.json"

    with open(file_path, "w") as file:
        json.dump(test_data, file)

    result = load_test_cases(file_path)

    assert result == test_data


def test_load_test_cases_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_test_cases("test_cases/nonexistent.json")

def test_load_test_cases_invalid_json(tmp_path):
    file_path = tmp_path / "invalid.json"

    file_path.write_text('{"input": [2, 3], "expected": 5,}')

    with pytest.raises(ValueError, match="Invalid JSON format"):
        load_test_cases(file_path)

def test_load_test_cases_missing_keys(tmp_path):
    file_path = tmp_path / "missing_keys.json"
    file_path.write_text('[{"input": [2, 3]}]')

    with pytest.raises(ValueError, match="must contain"):
        load_test_cases(file_path)

def test_load_test_cases_invalid_input_type(tmp_path):
    file_path = tmp_path / "invalid_input.json"
    file_path.write_text('[{"input": 5, "expected": 5}]')

    with pytest.raises(ValueError, match="'input' must be a list"):
        load_test_cases(file_path)

def test_load_test_cases_invalid_structure(tmp_path):
    file_path = tmp_path / "invalid_structure.json"
    file_path.write_text('[5]')

    with pytest.raises(ValueError, match="must be a dictionary"):
        load_test_cases(file_path)

def test_load_test_cases_not_a_list(tmp_path):
    file_path = tmp_path / "not_a_list.json"
    file_path.write_text('{"input": [2, 3], "expected": 5}')

    with pytest.raises(ValueError, match="must contain a list"):
        load_test_cases(file_path)

def test_load_test_cases_empty_list(tmp_path):
    file_path = tmp_path / "empty.json"
    file_path.write_text("[]")

    with pytest.raises(ValueError, match="cannot be empty"):
        load_test_cases(file_path)

def test_load_test_cases_empty_input(tmp_path):
    file_path = tmp_path / "empty_input.json"
    file_path.write_text('[{"input": [], "expected": 5}]')

    with pytest.raises(ValueError, match="'input' cannot be empty"):
        load_test_cases(file_path)

def test_load_test_cases_unexpected_keys(tmp_path):
    file_path = tmp_path / "unexpected_keys.json"
    file_path.write_text(
        '[{"input": [2, 3], "expected": 5, "result": 10}]'
    )

    with pytest.raises(ValueError, match="Unexpected keys"):
        load_test_cases(file_path)

def test_load_test_cases_expected_none(tmp_path):
    file_path = tmp_path / "expected_none.json"

    file_path.write_text('[{"input": [2, 3], "expected": null}]')

    result = load_test_cases(file_path)

    assert result[0]["expected"] is None

def test_load_test_cases_expected_string(tmp_path):
    file_path = tmp_path / "expected_string.json"

    file_path.write_text(
        '[{"input": ["Saman"], "expected": "Hello Saman"}]'
    )

    result = load_test_cases(file_path)

    assert result[0]["expected"] == "Hello Saman"