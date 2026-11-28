"""Strict models for data crossing the Docker process boundary."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CaseInput(BaseModel):
    """One trusted test case input sent into the container."""

    model_config = ConfigDict(extra="forbid")

    case_number: int = Field(ge=1)
    input_data: list[Any]


class CaseExecution(BaseModel):
    """A bounded execution result returned by the trusted in-container worker."""

    model_config = ConfigDict(extra="forbid")

    case_number: int = Field(ge=1)
    status: Literal[
        "returned",
        "syntax_error",
        "missing_function",
        "runtime_error",
        "timeout",
        "output_limit",
    ]
    actual: Any = None
    duration_ms: int = Field(ge=0)


class WorkerResponse(BaseModel):
    """The complete JSON response from the fixed execution image."""

    model_config = ConfigDict(extra="forbid")

    results: list[CaseExecution]
