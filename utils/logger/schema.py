from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentRunRecord:
    """
    Structured record representing one complete agent request.
    """

    request_id: str
    timestamp: str
    question: str

    # ---------------------------------------------------------
    # LLM information
    # ---------------------------------------------------------

    provider: str | None = None
    model: str | None = None

    llm_api_calls: int = 0
    llm_latencies: list[float] = field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Tool information
    # ---------------------------------------------------------

    tool_calls: int = 0

    tool_latencies: dict[str, list[float]] = field(
        default_factory=dict
    )

    tools_used: list[str] = field(
        default_factory=list
    )

    # ---------------------------------------------------------
    # Agent execution
    # ---------------------------------------------------------

    iterations: int = 0

    total_llm_latency: float = 0.0
    total_tool_latency: float = 0.0
    total_latency: float = 0.0

    # ---------------------------------------------------------
    # Status
    # ---------------------------------------------------------

    status: str | None = None
    error: str | None = None

    # ---------------------------------------------------------
    # Guardrails
    # ---------------------------------------------------------

    guardrail: dict[str, Any] | None = None

    # ---------------------------------------------------------
    # Tool errors / recovery
    # ---------------------------------------------------------

    tool_error_count: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    recovery_attempts: int = 0
    recovered: bool = False

    # ---------------------------------------------------------
    # Reviewer / multi-agent execution
    # ---------------------------------------------------------

    analyst_retry_count: int = 0
    review: dict[str, Any] | None = None

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the record into a JSON-serializable dictionary.
        """

        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "question": self.question,

            "provider": self.provider,
            "model": self.model,

            "llm_api_calls": self.llm_api_calls,
            "llm_latencies": self.llm_latencies,

            "tool_calls": self.tool_calls,
            "tool_latencies": self.tool_latencies,
            "tools_used": self.tools_used,

            "iterations": self.iterations,

            "total_llm_latency": self.total_llm_latency,
            "total_tool_latency": self.total_tool_latency,
            "total_latency": self.total_latency,

            "status": self.status,
            "error": self.error,

            "guardrail": self.guardrail,

            "tool_error_count": self.tool_error_count,
            "errors": self.errors,
            "recovery_attempts": self.recovery_attempts,
            "recovered": self.recovered,

            "analyst_retry_count": self.analyst_retry_count,
            "review": self.review,
        }