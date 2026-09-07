import re

from .schemas import GuardrailResult


# -------------------------------------------------------------
# SQL keywords that must never appear as executable statements
# -------------------------------------------------------------

FORBIDDEN_SQL_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "REPLACE",
    "MERGE",
    "COPY",
    "ATTACH",
    "DETACH",
    "INSTALL",
    "LOAD",
}


def _remove_sql_literals_and_comments(sql: str) -> str:
    """
    Remove quoted literals and SQL comments before inspecting
    executable SQL keywords.

    This prevents false positives such as:

        SELECT 'DROP TABLE orders'

    or:

        SELECT 'delete from orders'
    """

    # Remove single-quoted SQL strings.
    sql = re.sub(
        r"'(?:''|[^'])*'",
        " ",
        sql,
    )

    # Remove double-quoted identifiers.
    sql = re.sub(
        r'"(?:""|[^"])*"',
        " ",
        sql,
    )

    # Remove backtick-quoted identifiers.
    sql = re.sub(
        r"`(?:``|[^`])*`",
        " ",
        sql,
    )

    # Remove -- comments.
    sql = re.sub(
        r"--[^\n]*",
        " ",
        sql,
    )

    # Remove /* ... */ comments.
    sql = re.sub(
        r"/\*.*?\*/",
        " ",
        sql,
        flags=re.DOTALL,
    )

    return sql


def _normalize_sql(sql: str) -> str:
    """
    Normalize escaped whitespace and surrounding whitespace.
    """

    sql = (
        sql
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\r", "\r")
        .strip()
    )

    return sql


def _has_multiple_statements(sql: str) -> bool:
    """
    Detect multiple SQL statements.

    A single trailing semicolon is allowed.
    """

    stripped = sql.rstrip()

    if not stripped:
        return False

    # Remove one trailing semicolon.
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()

    # Any remaining semicolon represents another statement.
    return ";" in stripped


def validate_sql(query: str) -> GuardrailResult:
    """
    Validate that SQL is safe for read-only analytical execution.

    Allowed:
        SELECT ...
        WITH ... SELECT ...

    Blocked:
        INSERT
        UPDATE
        DELETE
        DROP
        ALTER
        CREATE
        TRUNCATE
        ATTACH
        DETACH
        INSTALL
        LOAD
        COPY
        multiple statements
    """

    if not isinstance(query, str):

        return GuardrailResult.block(
            guardrail_type="sql",
            reason="SQL query must be a string.",
        )

    query = _normalize_sql(query)

    if not query:

        return GuardrailResult.block(
            guardrail_type="sql",
            reason="SQL query cannot be empty.",
        )

    if _has_multiple_statements(query):

        return GuardrailResult.block(
            guardrail_type="sql",
            reason=(
                "Multiple SQL statements are not allowed. "
                "Only one read-only query may be executed."
            ),
        )

    executable_sql = _remove_sql_literals_and_comments(
        query
    ).strip()

    if not executable_sql:

        return GuardrailResult.block(
            guardrail_type="sql",
            reason="SQL query contains no executable statement.",
        )

    # ---------------------------------------------------------
    # Only SELECT / WITH queries are permitted.
    # ---------------------------------------------------------

    first_keyword_match = re.match(
        r"^\s*([A-Za-z_][A-Za-z0-9_]*)\b",
        executable_sql,
    )

    if first_keyword_match is None:

        return GuardrailResult.block(
            guardrail_type="sql",
            reason="Unable to identify the SQL statement type.",
        )

    first_keyword = (
        first_keyword_match.group(1).upper()
    )

    if first_keyword not in {"SELECT", "WITH"}:

        return GuardrailResult.block(
            guardrail_type="sql",
            reason=(
                "Only SELECT or WITH queries are allowed."
            ),
        )

    # ---------------------------------------------------------
    # Search executable SQL for forbidden operations.
    # ---------------------------------------------------------

    tokens = re.findall(
        r"\b[A-Za-z_][A-Za-z0-9_]*\b",
        executable_sql.upper(),
    )

    for token in tokens:

        if token in FORBIDDEN_SQL_KEYWORDS:

            return GuardrailResult.block(
                guardrail_type="sql",
                reason=(
                    f"Forbidden SQL operation detected: "
                    f"{token}."
                ),
            )

    return GuardrailResult.allow(
        guardrail_type="sql",
    )