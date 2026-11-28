"""Pydantic response schemas for the read-only catalog API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .execution.limits import MAX_SOURCE_BYTES

Difficulty = Literal["beginner", "intermediate", "advanced"]


class ExerciseExample(BaseModel):
    """A public example input and output shown with an exercise."""

    input: list[Any]
    output: Any


class ExerciseRead(BaseModel):
    """Exercise metadata returned by list and detail endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    description: str
    function_name: str
    function_signature: str
    difficulty: Difficulty
    requirements: list[str]
    examples: list[ExerciseExample]
    created_at: datetime


class TestSuiteRead(BaseModel):
    """Test suite metadata with a computed count of its official cases."""

    id: int
    slug: str
    exercise_slug: str
    name: str
    description: str
    version: int
    case_count: int = Field(ge=0)
    created_at: datetime


class TestCaseRead(BaseModel):
    """A public official case, returned only by read-only endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    test_suite_id: int
    case_number: int
    input_data: list[Any]
    expected_output: Any
    created_at: datetime


class SubmissionCreate(BaseModel):
    """Validated request for one source submission against a known suite."""

    model_config = ConfigDict(extra="forbid")

    test_suite_slug: str = Field(min_length=1, max_length=100)
    source_code: str = Field(min_length=1, max_length=MAX_SOURCE_BYTES)

    @field_validator("source_code")
    @classmethod
    def source_must_fit_utf8_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_SOURCE_BYTES:
            raise ValueError("source code exceeds the maximum allowed size")
        return value


TestOutcomeStatus = Literal[
    "passed",
    "failed",
    "syntax_error",
    "missing_function",
    "runtime_error",
    "timeout",
    "output_limit",
]
RunStatus = Literal[
    "completed",
    "invalid_submission",
    "timed_out",
    "infrastructure_error",
    "internal_error",
]


class TestResultRead(BaseModel):
    """One persisted result with input and expected-value snapshots."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    test_case_id: int | None
    case_number: int
    input_data: list[Any]
    expected_output: Any
    actual_output: Any
    status: TestOutcomeStatus
    error_message: str | None
    duration_ms: int


class EvaluationRead(BaseModel):
    """Evaluation response and history detail representation."""

    id: int
    submission_id: int
    exercise_slug: str
    test_suite_slug: str
    source_code: str
    status: RunStatus
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    success_rate: float
    duration_ms: int
    failure_message: str | None
    created_at: datetime
    test_results: list[TestResultRead]


class ExecutionFailureDetail(BaseModel):
    """Safe public detail for isolated-runner infrastructure failures."""

    message: str
    evaluation_id: int
