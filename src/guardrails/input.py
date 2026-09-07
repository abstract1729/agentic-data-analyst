import re

from .schemas import GuardrailResult


# -------------------------------------------------------------
# Prompt-injection patterns
# -------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = [
    re.compile(
        r"\bignore\s+(all\s+)?previous\s+instructions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bignore\s+(all\s+)?prior\s+instructions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(all\s+)?previous\s+instructions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\boverride\s+(the\s+)?system\s+instructions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\breveal\s+(the\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bshow\s+(me\s+)?(the\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bprint\s+(the\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\breveal\s+(your\s+)?hidden\s+instructions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bshow\s+(your\s+)?hidden\s+instructions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdeveloper\s+message\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbypass\s+(the\s+)?guardrails\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisable\s+(the\s+)?guardrails\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisable\s+(the\s+)?safety\b",
        re.IGNORECASE,
    ),
]


# -------------------------------------------------------------
# Database mutation patterns
# -------------------------------------------------------------

DATABASE_MUTATION_PATTERNS = [
    re.compile(
        r"\bdrop\s+(table|view|schema|database)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btruncate\s+(table|schema)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdelete\s+from\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bupdate\s+\w+\s+set\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\binsert\s+into\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\balter\s+(table|schema|database)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcreate\s+(table|view|schema|database)\b",
        re.IGNORECASE,
    ),
]


def validate_user_input(question: str) -> GuardrailResult:
    """
    Validate a user question before it is passed to the Analyst.

    This is a deterministic input-level guardrail.

    It is intentionally conservative: normal analytical questions
    should pass, while obvious prompt-injection and database-mutation
    requests are blocked.
    """

    if not isinstance(question, str):

        return GuardrailResult.block(
            guardrail_type="input",
            reason="User question must be a string.",
        )

    question = question.strip()

    if not question:

        return GuardrailResult.block(
            guardrail_type="input",
            reason="User question cannot be empty.",
        )

    for pattern in PROMPT_INJECTION_PATTERNS:

        if pattern.search(question):

            return GuardrailResult.block(
                guardrail_type="input",
                reason=(
                    "Potential prompt-injection attempt "
                    "detected."
                ),
            )

    for pattern in DATABASE_MUTATION_PATTERNS:

        if pattern.search(question):

            return GuardrailResult.block(
                guardrail_type="input",
                reason=(
                    "Database modification requests are not "
                    "permitted. This agent is read-only."
                ),
            )

    return GuardrailResult.allow(
        guardrail_type="input",
    )