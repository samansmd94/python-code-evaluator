"""Coordinate isolated execution, trusted comparison, and history persistence."""

import logging
import time
from typing import Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from evaluator.comparator import compare_results

from ..execution.docker_runner import (
    ContainerOutputLimitError,
    ContainerTimedOutError,
    ExecutionInfrastructureError,
)
from ..execution.limits import MAX_SOURCE_BYTES
from ..execution.protocol import CaseExecution, CaseInput
from ..models import EvaluationRun, Submission, TestCase, TestResult, TestSuite
from ..schemas import EvaluationRead, SubmissionCreate, TestResultRead

ERROR_MESSAGES = {
    "syntax_error": "Submitted source contains a syntax error.",
    "missing_function": "The required exercise function was not defined.",
    "runtime_error": "The submitted function raised an exception.",
    "timeout": "Execution exceeded the configured time limit.",
    "output_limit": "Execution output exceeded the configured limit.",
}
ERROR_STATUSES = set(ERROR_MESSAGES)
INVALID_SUBMISSION_STATUSES = {"syntax_error", "missing_function"}
logger = logging.getLogger(__name__)


class ExecutionRunner(Protocol):
    """Small interface implemented by the fixed Docker execution adapter."""

    def execute(
        self,
        source_code: str,
        function_name: str,
        test_cases: Sequence[CaseInput],
    ) -> list[CaseExecution]: ...


class SuiteNotFoundError(Exception):
    """The requested official suite does not exist."""


class ExecutionUnavailableError(Exception):
    """The isolated infrastructure failed; the evaluation ID is retained."""

    def __init__(self, evaluation_id: int) -> None:
        super().__init__("Isolated execution is unavailable.")
        self.evaluation_id = evaluation_id


class EvaluationService:
    """Execute one source submission against a suite and store its report."""

    def __init__(self, runner: ExecutionRunner) -> None:
        self._runner = runner

    def submit(
        self, session: Session, request: SubmissionCreate
    ) -> EvaluationRead:
        """Validate catalog membership, execute, compare, and persist a run."""
        source_size = len(request.source_code.encode("utf-8"))
        if source_size > MAX_SOURCE_BYTES:
            raise ValueError("Source code exceeds the configured limit")

        suite = session.scalar(
            select(TestSuite)
            .where(TestSuite.slug == request.test_suite_slug)
            .options(
                joinedload(TestSuite.exercise),
                selectinload(TestSuite.test_cases),
            )
        )
        if suite is None:
            raise SuiteNotFoundError

        test_cases = sorted(suite.test_cases, key=lambda case: case.case_number)
        if not test_cases:
            raise SuiteNotFoundError

        submission = Submission(
            exercise_id=suite.exercise_id,
            test_suite_id=suite.id,
            source_code=request.source_code,
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)

        started = time.monotonic()
        try:
            runner_cases = [
                CaseInput(case_number=case.case_number, input_data=case.input_data)
                for case in test_cases
            ]
            outcomes = self._runner.execute(
                request.source_code,
                suite.exercise.function_name,
                runner_cases,
            )
        except ContainerTimedOutError:
            duration_ms = _elapsed_ms(started)
            outcomes = [
                CaseExecution(
                    case_number=case.case_number,
                    status="timeout",
                    duration_ms=0,
                )
                for case in test_cases
            ]
            try:
                return self._persist_completed(
                    session, submission, suite, test_cases, outcomes,
                    run_status="timed_out", duration_ms=duration_ms,
                )
            except Exception as error:
                return self._persist_internal_failure(
                    session, submission.id, duration_ms, error
                )
        except ContainerOutputLimitError:
            duration_ms = _elapsed_ms(started)
            outcomes = [
                CaseExecution(
                    case_number=case.case_number,
                    status="output_limit",
                    duration_ms=0,
                )
                for case in test_cases
            ]
            try:
                return self._persist_completed(
                    session, submission, suite, test_cases, outcomes,
                    run_status="completed", duration_ms=duration_ms,
                )
            except Exception as error:
                return self._persist_internal_failure(
                    session, submission.id, duration_ms, error
                )
        except ExecutionInfrastructureError as error:
            duration_ms = _elapsed_ms(started)
            saved = self._persist_failure(
                session,
                submission.id,
                status="infrastructure_error",
                failure_message="Isolated execution is unavailable.",
                duration_ms=duration_ms,
            )
            # Do not surface the underlying Docker/OS exception to the API.
            raise ExecutionUnavailableError(saved.id) from error
        except Exception as error:
            return self._persist_internal_failure(
                session, submission.id, _elapsed_ms(started), error
            )

        duration_ms = _elapsed_ms(started)
        try:
            self._validate_outcomes(outcomes, test_cases)
        except Exception as error:
            return self._persist_internal_failure(
                session, submission.id, duration_ms, error
            )
        has_invalid_source = any(
            outcome.status in INVALID_SUBMISSION_STATUSES for outcome in outcomes
        )
        run_status = "invalid_submission" if has_invalid_source else "completed"
        try:
            return self._persist_completed(
                session,
                submission,
                suite,
                test_cases,
                outcomes,
                run_status=run_status,
                duration_ms=duration_ms,
            )
        except Exception as error:
            return self._persist_internal_failure(
                session, submission.id, duration_ms, error
            )

    def _persist_internal_failure(
        self,
        session: Session,
        submission_id: int,
        duration_ms: int,
        error: Exception,
    ) -> EvaluationRead:
        """Store a safe terminal record after an unexpected evaluation failure."""
        logger.error(
            "Evaluation failed internally for submission %s (%s)",
            submission_id,
            type(error).__name__,
        )
        return self._persist_failure(
            session,
            submission_id,
            status="internal_error",
            failure_message="Evaluation could not be completed.",
            duration_ms=duration_ms,
        )

    @staticmethod
    def _persist_failure(
        session: Session,
        submission_id: int,
        *,
        status: str,
        failure_message: str,
        duration_ms: int,
    ) -> EvaluationRead:
        """Replace partial results with one safe, terminal failure record."""
        session.rollback()
        submission = session.scalar(
            select(Submission)
            .where(Submission.id == submission_id)
            .options(
                joinedload(Submission.exercise),
                joinedload(Submission.test_suite),
            )
        )
        if submission is None:
            raise RuntimeError("Accepted submission record is missing")

        run = session.scalar(
            select(EvaluationRun)
            .where(EvaluationRun.submission_id == submission_id)
            .options(selectinload(EvaluationRun.test_results))
        )
        if run is None:
            run = EvaluationRun(submission_id=submission_id)
            session.add(run)
        else:
            run.test_results.clear()

        run.status = status
        run.total_tests = 0
        run.passed_tests = 0
        run.failed_tests = 0
        run.error_tests = 0
        run.success_rate = 0.0
        run.duration_ms = duration_ms
        run.failure_message = failure_message
        session.commit()
        session.refresh(run)
        return _evaluation_read(run, submission=submission)

    def get_evaluation(self, session: Session, evaluation_id: int) -> EvaluationRead | None:
        """Load one persisted report, including its source and test snapshots."""
        run = session.scalar(
            select(EvaluationRun)
            .where(EvaluationRun.id == evaluation_id)
            .options(
                joinedload(EvaluationRun.submission).joinedload(Submission.exercise),
                joinedload(EvaluationRun.submission).joinedload(Submission.test_suite),
                selectinload(EvaluationRun.test_results),
            )
        )
        return _evaluation_read(run) if run is not None else None

    def _persist_completed(
        self,
        session: Session,
        submission: Submission,
        suite: TestSuite,
        test_cases: Sequence[TestCase],
        outcomes: Sequence[CaseExecution],
        *,
        run_status: str,
        duration_ms: int,
    ) -> EvaluationRead:
        cases_by_number = {case.case_number: case for case in test_cases}
        passed = failed = errors = 0
        records = []
        for outcome in outcomes:
            case = cases_by_number[outcome.case_number]
            if outcome.status == "returned":
                is_match = compare_results(outcome.actual, case.expected_output)
                status = "passed" if is_match else "failed"
                error_message = None
                actual_output = outcome.actual
                if is_match:
                    passed += 1
                else:
                    failed += 1
            else:
                status = outcome.status
                error_message = ERROR_MESSAGES[status]
                actual_output = None
                errors += 1
            records.append(
                TestResult(
                    test_case_id=case.id,
                    case_number=case.case_number,
                    input_data=case.input_data,
                    expected_output=case.expected_output,
                    actual_output=actual_output,
                    status=status,
                    error_message=error_message,
                    duration_ms=outcome.duration_ms,
                )
            )

        total = len(test_cases)
        run = EvaluationRun(
            submission_id=submission.id,
            status=run_status,
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            success_rate=(passed / total * 100.0) if total else 0.0,
            duration_ms=duration_ms,
            test_results=records,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return _evaluation_read(run, submission=submission, suite=suite)

    @staticmethod
    def _validate_outcomes(
        outcomes: Sequence[CaseExecution], test_cases: Sequence[TestCase]
    ) -> None:
        actual_numbers = [outcome.case_number for outcome in outcomes]
        expected_numbers = [case.case_number for case in test_cases]
        if sorted(actual_numbers) != sorted(expected_numbers):
            raise RuntimeError("Execution adapter returned an incomplete result set")


def _evaluation_read(
    run: EvaluationRun,
    *,
    submission: Submission | None = None,
    suite: TestSuite | None = None,
) -> EvaluationRead:
    submission = submission or run.submission
    suite = suite or submission.test_suite
    return EvaluationRead(
        id=run.id,
        submission_id=submission.id,
        exercise_slug=submission.exercise.slug,
        test_suite_slug=suite.slug,
        source_code=submission.source_code,
        status=run.status,
        total_tests=run.total_tests,
        passed_tests=run.passed_tests,
        failed_tests=run.failed_tests,
        error_tests=run.error_tests,
        success_rate=run.success_rate,
        duration_ms=run.duration_ms,
        failure_message=run.failure_message,
        created_at=run.created_at,
        test_results=[
            TestResultRead.model_validate(result)
            for result in sorted(run.test_results, key=lambda row: row.case_number)
        ],
    )


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))
