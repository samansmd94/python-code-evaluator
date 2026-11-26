import json
import subprocess
import sys
from pathlib import Path

import pytest

from evaluator.cli import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_cli_text_report_and_success_exit_code(capsys):
    exit_code = main([
        "run", "--function", "greet", "--tests", "test_cases/greeting.json"
    ])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Total tests: 2" in captured.out
    assert "100.00%" in captured.out


def test_cli_returns_failure_code_for_failed_tests(capsys):
    exit_code = main([
        "run", "--function", "add", "--tests", "test_cases/addition.json"
    ])
    assert exit_code == 1
    assert "FAILED" in capsys.readouterr().out


def test_cli_json_output(capsys):
    exit_code = main([
        "run", "--function", "greet", "--tests", "test_cases/greeting.json",
        "--format", "json",
    ])
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["passed"] == 2


def test_cli_unknown_function_is_rejected():
    with pytest.raises(SystemExit) as error:
        main(["run", "--function", "builtins.eval", "--tests", "anything.json"])
    assert error.value.code == 2


def test_cli_missing_test_file_has_clear_error(capsys):
    exit_code = main([
        "run", "--function", "greet", "--tests", "not-a-real-file.json"
    ])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Test cases file not found" in captured.err


def test_module_cli_integration():
    completed = subprocess.run(
        [sys.executable, "-m", "evaluator", "run", "--function", "greet",
         "--tests", "test_cases/greeting.json", "--format", "json"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["total"] == 2
