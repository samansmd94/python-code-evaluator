"""Read-only endpoints for exercises, suites, and official test cases."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .database import get_db
from .models import Exercise, TestCase, TestSuite
from .schemas import (
    EvaluationRead,
    ExerciseRead,
    SubmissionCreate,
    TestCaseRead,
    TestSuiteRead,
)
from .services.evaluation_service import (
    EvaluationService,
    ExecutionUnavailableError,
    SuiteNotFoundError,
)

router = APIRouter(prefix="/api")


@router.get("/exercises", response_model=list[ExerciseRead])
def list_exercises(session: Session = Depends(get_db)) -> list[Exercise]:
    """List exercises in a stable title order."""
    return list(session.scalars(select(Exercise).order_by(Exercise.title)))


@router.get("/exercises/{exercise_slug}", response_model=ExerciseRead)
def get_exercise(exercise_slug: str, session: Session = Depends(get_db)) -> Exercise:
    """Return one exercise by its stable slug."""
    exercise = session.scalar(
        select(Exercise).where(Exercise.slug == exercise_slug)
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return exercise


@router.get(
    "/exercises/{exercise_slug}/test-suites",
    response_model=list[TestSuiteRead],
)
def list_exercise_suites(
    exercise_slug: str, session: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    """List versioned suites belonging to an exercise."""
    exercise = session.scalar(
        select(Exercise).where(Exercise.slug == exercise_slug)
    )
    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return _suite_rows(session, Exercise.slug == exercise_slug)


@router.get("/test-suites", response_model=list[TestSuiteRead])
def list_test_suites(
    exercise_slug: str | None = None,
    session: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """List suites, optionally filtered by exercise slug."""
    if exercise_slug is not None:
        exists = session.scalar(
            select(Exercise.id).where(Exercise.slug == exercise_slug)
        )
        if exists is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
    condition = Exercise.slug == exercise_slug if exercise_slug else None
    return _suite_rows(session, condition)


@router.get("/test-suites/{suite_slug}", response_model=TestSuiteRead)
def get_test_suite(suite_slug: str, session: Session = Depends(get_db)) -> dict[str, Any]:
    """Return suite metadata and its current official case count."""
    row = _suite_row(session, suite_slug)
    if row is None:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return row


@router.get(
    "/test-suites/{suite_slug}/test-cases",
    response_model=list[TestCaseRead],
)
def list_test_cases(
    suite_slug: str, session: Session = Depends(get_db)
) -> list[TestCase]:
    """Return official cases in order; this API exposes no write operation."""
    suite_id = session.scalar(
        select(TestSuite.id).where(TestSuite.slug == suite_slug)
    )
    if suite_id is None:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return list(
        session.scalars(
            select(TestCase)
            .where(TestCase.test_suite_id == suite_id)
            .order_by(TestCase.case_number)
        )
    )


@router.post(
    "/submissions",
    response_model=EvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_submission(
    payload: SubmissionCreate,
    request: Request,
    session: Session = Depends(get_db),
) -> EvaluationRead:
    """Evaluate source in Docker; function name and cases come from the suite."""
    service: EvaluationService = request.app.state.evaluation_service
    try:
        return service.submit(session, payload)
    except SuiteNotFoundError:
        raise HTTPException(status_code=404, detail="Test suite not found")
    except ExecutionUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "Isolated execution is unavailable.",
                "evaluation_id": error.evaluation_id,
            },
        )


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationRead)
def get_evaluation(
    evaluation_id: int,
    request: Request,
    session: Session = Depends(get_db),
) -> EvaluationRead:
    """Retrieve a persisted evaluation and its per-test history."""
    service: EvaluationService = request.app.state.evaluation_service
    evaluation = service.get_evaluation(session, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


def _suite_rows(
    session: Session, exercise_condition: Any = None
) -> list[dict[str, Any]]:
    statement = (
        select(TestSuite, func.count(TestCase.id).label("case_count"))
        .join(TestSuite.exercise)
        .outerjoin(TestSuite.test_cases)
        .options(joinedload(TestSuite.exercise))
        .group_by(TestSuite.id)
        .order_by(Exercise.title, TestSuite.version)
    )
    if exercise_condition is not None:
        statement = statement.where(exercise_condition)
    return [
        _suite_payload(suite, case_count)
        for suite, case_count in session.execute(statement).all()
    ]


def _suite_row(session: Session, suite_slug: str) -> dict[str, Any] | None:
    row = (
        session.execute(
            select(TestSuite, func.count(TestCase.id).label("case_count"))
            .join(TestSuite.exercise)
            .outerjoin(TestSuite.test_cases)
            .options(joinedload(TestSuite.exercise))
            .where(TestSuite.slug == suite_slug)
            .group_by(TestSuite.id)
        )
        .first()
    )
    if row is None:
        return None
    suite, case_count = row
    return _suite_payload(suite, case_count)


def _suite_payload(suite: TestSuite, case_count: int) -> dict[str, Any]:
    return {
        "id": suite.id,
        "slug": suite.slug,
        "exercise_slug": suite.exercise.slug,
        "name": suite.name,
        "description": suite.description,
        "version": suite.version,
        "case_count": case_count,
        "created_at": suite.created_at,
    }
