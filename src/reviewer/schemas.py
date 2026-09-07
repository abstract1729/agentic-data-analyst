from typing import Literal

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    """A single issue identified by the Reviewer."""

    type: Literal[
        "semantic",
        "calculation",
        "evidence",
        "completeness",
        "tool_usage",
        "other",
    ]

    description: str = Field(
        description="Clear explanation of the identified issue."
    )


class ReviewResult(BaseModel):
    """Structured output produced by the Reviewer Agent."""

    status: Literal["PASS", "FAIL"] = Field(
        description="Whether the Analyst's result is acceptable."
    )

    issues: list[ReviewIssue] = Field(
        default_factory=list,
        description="Issues identified in the Analyst's analysis or answer.",
    )

    correction: str = Field(
        default="",
        description=(
            "Specific correction instructions for the Analyst. "
            "Required when status is FAIL."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Reviewer's confidence in the verdict."
    )