from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    """
    Result of a deterministic guardrail validation.

    Attributes:
        allowed:
            Whether the operation is allowed to continue.

        guardrail_type:
            Category of guardrail that produced the result.

        reason:
            Human-readable explanation for logging/debugging.
    """

    allowed: bool
    guardrail_type: str
    reason: str

    @classmethod
    def allow(
        cls,
        guardrail_type: str,
        reason: str = "Operation allowed.",
    ) -> "GuardrailResult":

        return cls(
            allowed=True,
            guardrail_type=guardrail_type,
            reason=reason,
        )

    @classmethod
    def block(
        cls,
        guardrail_type: str,
        reason: str,
    ) -> "GuardrailResult":

        return cls(
            allowed=False,
            guardrail_type=guardrail_type,
            reason=reason,
        )