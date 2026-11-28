"""Submission request, evaluation response, and history API tests."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from backend.app.execution.docker_runner import (
    ContainerFailureError,
    ContainerOutputLimitError,
    ContainerTimedOutError,
    DockerUnavailableError,
)
from backend.app.execution.protocol import CaseExecution
from backend.app.main import create_app
from backend.app.models import EvaluationRun, Submission


class StubRunner:
    def __init__(self, *, statuses=None, actual_values=None, error=None):
        self.statuses = statuses or {}
        self.actual_values = actual_values or {}
        self.error = error
        self.calls = []

    def execute(self, source_code, function_name, test_cases):
        self.calls.append((source_code, function_name, test_cases))
        if self.error is not None:
            raise self.error
        return [
            CaseExecution(
                case_number=case.case_number,
                status=self.statuses.get(case.case_number, "returned"),
                actual=self.actual_values.get(case.case_number, 0),
                duration_ms=4,
            )
            for case in test_cases
        ]


def _client(database_url, runner):
    return TestClient(
        create_app(database_url, execution_runner=runner)
    )


def _post(client, **overrides):
    payload = {
        "test_suite_slug": "addition-default-v1",
        "source_code": "def add(a, b):\n    return a + b\n",
    }
    payload.update(overrides)
    return client.post("/api/submissions", json=payload)


def test_correct_submission_is_compared_and_history_is_retrievable(database_url, migrated_database):
    runner = StubRunner(actual_values={1: 5, 2: 30, 3: 0, 4: 0})
    with _client(migrated_database, runner) as client:
        response = _post(client)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "completed"
        assert body["total_tests"] == 4
        assert body["passed_tests"] == 4
        assert body["failed_tests"] == 0
        assert body["error_tests"] == 0
        assert body["success_rate"] == 100.0
        assert runner.calls[0][1] == "add"
        assert [case.case_number for case in runner.calls[0][2]] == [1, 2, 3, 4]

        history = client.get("/api/evaluations/{}".format(body["id"]))
        assert history.status_code == 200
        assert history.json()["source_code"] == body["source_code"]
        assert history.json()["test_results"][0]["expected_output"] == 5
        assert history.json()["test_results"][0]["actual_output"] == 5


def test_incorrect_answer_is_a_failed_test(migrated_database):
    runner = StubRunner(actual_values={1: 4, 2: 30, 3: 0, 4: 0})
    with _client(migrated_database, runner) as client:
        body = _post(client).json()
        assert body["status"] == "completed"
        assert body["passed_tests"] == 3
        assert body["failed_tests"] == 1
        assert body["error_tests"] == 0
        assert body["test_results"][0]["status"] == "failed"


def test_syntax_and_missing_function_are_invalid_submissions(migrated_database):
    syntax_runner = StubRunner(statuses={1: "syntax_error", 2: "syntax_error", 3: "syntax_error", 4: "syntax_error"})
    with _client(migrated_database, syntax_runner) as client:
        syntax = _post(client, source_code="def add(:\n").json()
        assert syntax["status"] == "invalid_submission"
        assert syntax["passed_tests"] == 0
        assert syntax["error_tests"] == 4
        assert syntax["test_results"][0]["error_message"] == "Submitted source contains a syntax error."

    missing_runner = StubRunner(statuses={1: "missing_function", 2: "missing_function", 3: "missing_function", 4: "missing_function"})
    with _client(migrated_database, missing_runner) as client:
        missing = _post(client, source_code="def other():\n    return 0\n").json()
        assert missing["status"] == "invalid_submission"
        assert missing["test_results"][0]["status"] == "missing_function"


def test_runtime_errors_remain_errors_not_passes(migrated_database):
    runner = StubRunner(statuses={1: "runtime_error", 2: "runtime_error", 3: "runtime_error", 4: "runtime_error"})
    with _client(migrated_database, runner) as client:
        body = _post(client).json()
        assert body["passed_tests"] == 0
        assert body["failed_tests"] == 0
        assert body["error_tests"] == 4
        assert body["test_results"][0]["status"] == "runtime_error"
        assert "exception" in body["test_results"][0]["error_message"]


def test_timeouts_and_output_limits_are_distinct(migrated_database):
    with _client(migrated_database, StubRunner(error=ContainerTimedOutError())) as client:
        timed_out = _post(client).json()
        assert timed_out["status"] == "timed_out"
        assert timed_out["error_tests"] == 4
        assert timed_out["test_results"][0]["status"] == "timeout"

    with _client(migrated_database, StubRunner(error=ContainerOutputLimitError())) as client:
        limited = _post(client).json()
        assert limited["status"] == "completed"
        assert limited["error_tests"] == 4
        assert limited["test_results"][0]["status"] == "output_limit"


def test_unknown_suite_and_invalid_request_are_rejected(migrated_database):
    with _client(migrated_database, StubRunner()) as client:
        assert _post(client, test_suite_slug="unknown").status_code == 404
        assert _post(client, source_code="").status_code == 422
        too_many_bytes = "é" * 16385
        assert _post(client, source_code=too_many_bytes).status_code == 422
        assert _post(client, docker_args=["--privileged"]).status_code == 422
        assert _post(client, function_name="eval").status_code == 422
        assert client.get("/api/evaluations/99999").status_code == 404


def test_docker_unavailable_returns_safe_503_and_persists_attempt(migrated_database):
    runner = StubRunner(error=DockerUnavailableError("private socket detail"))
    with _client(migrated_database, runner) as client:
        response = _post(client)
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["message"] == "Isolated execution is unavailable."
        assert "private socket detail" not in response.text
        history = client.get("/api/evaluations/{}".format(detail["evaluation_id"]))
        assert history.status_code == 200
        assert history.json()["status"] == "infrastructure_error"
        assert history.json()["total_tests"] == 0


def test_container_failure_is_infrastructure_error(migrated_database):
    runner = StubRunner(error=ContainerFailureError("container internals"))
    with _client(migrated_database, runner) as client:
        response = _post(client)
        assert response.status_code == 503
        assert "container internals" not in response.text


def test_unexpected_runner_exception_gets_terminal_history(migrated_database):
    with _client(migrated_database, StubRunner(error=RuntimeError("private detail"))) as client:
        response = _post(client)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "internal_error"
        assert body["total_tests"] == 0
        assert body["failure_message"] == "Evaluation could not be completed."
        assert "private detail" not in response.text
        assert client.get("/api/evaluations/{}".format(body["id"])).json()["status"] == "internal_error"

    _assert_terminal_failure_persisted(migrated_database)


def test_invalid_runner_result_set_gets_terminal_history(migrated_database):
    class IncompleteRunner:
        def execute(self, _source_code, _function_name, _test_cases):
            return [CaseExecution(case_number=1, status="returned", actual=5, duration_ms=1)]

    with _client(migrated_database, IncompleteRunner()) as client:
        response = _post(client)
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "internal_error"
        assert body["test_results"] == []
        assert body["failure_message"] == "Evaluation could not be completed."

    _assert_terminal_failure_persisted(migrated_database)


def _assert_terminal_failure_persisted(database_url):
    engine = create_engine(database_url)
    try:
        with Session(engine) as session:
            assert session.scalar(select(func.count(Submission.id))) == 1
            assert session.scalar(select(func.count(EvaluationRun.id))) == 1
            run = session.scalar(select(EvaluationRun))
            assert run.status == "internal_error"
            assert run.total_tests == 0
            assert run.test_results == []
    finally:
        engine.dispose()
