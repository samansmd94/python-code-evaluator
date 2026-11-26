import json

from evaluator.reporter import (
    generate_report,
    generate_overall_summary,
    report_json,
    summarize_results,
)


def test_reporter_displays_passed_and_failed_counts(capsys):
    results = [
        {
            "input": (2, 3),
            "expected": 5,
            "actual": 5,
            "passed": True,
        },
        {
            "input": (2, 3),
            "expected": 10,
            "actual": 5,
            "passed": False,
        },
    ]

    generate_report(results)

    captured = capsys.readouterr()

    assert "Total tests: 2" in captured.out
    assert "Passed: 1" in captured.out
    assert "Failed: 1" in captured.out
    assert "Success rate: 50.00%" in captured.out

def test_reporter_displays_execution_errors(capsys):
    results = [
        {
            "input": (10, 0),
            "expected": 5,
            "actual": None,
            "passed": False,
            "error": "division by zero",
        }
    ]

    generate_report(results)

    captured = capsys.readouterr()

    assert "Error: division by zero" in captured.out
    assert "Failed: 0" in captured.out
    assert "Errors: 1" in captured.out

def test_generate_overall_summary(capsys):
    all_results = [
        [
            {"passed": True, "error": None},
            {"passed": False, "error": None},
        ],
        [
            {"passed": True, "error": None},
            {"passed": False, "error": "division by zero"},
        ],
    ]

    generate_overall_summary(all_results)

    captured = capsys.readouterr()

    assert "Total tests: 4" in captured.out
    assert "Passed: 2" in captured.out
    assert "Failed: 1" in captured.out
    assert "Errors: 1" in captured.out
    assert "Success rate: 50.00%" in captured.out


def test_summary_counts_execution_errors_separately():
    summary = summarize_results([
        {"passed": True, "error": None, "status": "passed"},
        {"passed": False, "error": None, "status": "failed"},
        {"passed": False, "error": "bad call", "status": "error"},
    ])

    assert summary["total"] == 3
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["errors"] == 1
    assert (
        summary["passed"] + summary["failed"] + summary["errors"]
        == summary["total"]
    )


def test_json_report_is_deterministic_and_consumable():
    results = [{"input": [1], "expected": 1, "actual": 1, "passed": True, "error": None}]
    first = report_json(results)
    assert first == report_json(results)
    assert json.loads(first)["success_rate"] == 100.0
