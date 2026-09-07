import ast

from .schemas import GuardrailResult


# -------------------------------------------------------------
# Modules that must never be accessed from the Python sandbox
# -------------------------------------------------------------

FORBIDDEN_MODULES = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "pathlib",
    "shutil",
    "requests",
    "httpx",
    "urllib",
    "urllib3",
    "ftplib",
    "telnetlib",
    "ctypes",
    "multiprocessing",
    "threading",
    "pickle",
    "builtins",
}


# -------------------------------------------------------------
# Dangerous builtins / dynamic execution mechanisms
# -------------------------------------------------------------

FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
}


# -------------------------------------------------------------
# Pandas / NumPy operations that can access external files
# -------------------------------------------------------------

FORBIDDEN_LIBRARY_CALLS = {
    "read_csv",
    "read_excel",
    "read_json",
    "read_pickle",
    "read_parquet",
    "read_feather",
    "read_fwf",
    "read_html",
    "read_xml",
    "read_sql",
    "read_sql_query",
    "read_sql_table",
    "to_pickle",
    "to_csv",
    "to_excel",
    "to_json",
    "to_parquet",
}


def _module_root(name: str) -> str:
    """
    Return the root module from a dotted name.

    Example:

        os.path.join -> os
        pandas.read_csv -> pandas
    """

    return name.split(".", 1)[0]


def _get_attribute_chain(node: ast.AST) -> list[str]:
    """
    Extract an attribute chain from an AST node.

    Example:

        os.path.join

    becomes:

        ["os", "path", "join"]
    """

    chain = []

    current = node

    while isinstance(current, ast.Attribute):

        chain.append(current.attr)
        current = current.value

    if isinstance(current, ast.Name):

        chain.append(current.id)

    return list(reversed(chain))


def validate_python(code: str) -> GuardrailResult:
    """
    Validate Python/Pandas/NumPy analysis code.

    The execution environment is intended only for analytical
    operations over `pd`, `np`, and `query(sql)`.

    The validator therefore blocks:

        - imports
        - dynamic code execution
        - filesystem access
        - network access
        - subprocess execution
        - dangerous module access
        - obvious Python escape mechanisms
    """

    if not isinstance(code, str):

        return GuardrailResult.block(
            guardrail_type="python",
            reason="Python code must be a string.",
        )

    code = (
        code
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\r", "\r")
    )

    if not code.strip():

        return GuardrailResult.block(
            guardrail_type="python",
            reason="Python code cannot be empty.",
        )

    # ---------------------------------------------------------
    # Parse code
    # ---------------------------------------------------------

    try:

        tree = ast.parse(code)

    except SyntaxError as exc:

        return GuardrailResult.block(
            guardrail_type="python",
            reason=(
                "Python syntax validation failed: "
                f"{exc}"
            ),
        )

    # ---------------------------------------------------------
    # Inspect AST
    # ---------------------------------------------------------

    for node in ast.walk(tree):

        # -----------------------------------------------------
        # Imports
        # -----------------------------------------------------

        if isinstance(node, ast.Import):

            modules = [
                alias.name
                for alias in node.names
            ]

            return GuardrailResult.block(
                guardrail_type="python",
                reason=(
                    "Import statements are not allowed. "
                    "Available objects are `pd`, `np`, "
                    "and `query(sql)`. "
                    f"Attempted import: {', '.join(modules)}."
                ),
            )

        if isinstance(node, ast.ImportFrom):

            module = node.module or "<unknown>"

            return GuardrailResult.block(
                guardrail_type="python",
                reason=(
                    "Import statements are not allowed. "
                    f"Attempted import from `{module}`."
                ),
            )

        # -----------------------------------------------------
        # Dangerous names
        # -----------------------------------------------------

        if isinstance(node, ast.Name):

            name = node.id

            if name in FORBIDDEN_MODULES:

                return GuardrailResult.block(
                    guardrail_type="python",
                    reason=(
                        f"Access to module `{name}` "
                        "is not allowed."
                    ),
                )

            if name in FORBIDDEN_CALLS:

                return GuardrailResult.block(
                    guardrail_type="python",
                    reason=(
                        f"Use of `{name}()` is not allowed."
                    ),
                )

            if name.startswith("__"):

                return GuardrailResult.block(
                    guardrail_type="python",
                    reason=(
                        "Dunder/private Python attributes "
                        "are not allowed."
                    ),
                )

        # -----------------------------------------------------
        # Attribute access
        # -----------------------------------------------------

        if isinstance(node, ast.Attribute):

            chain = _get_attribute_chain(node)

            if not chain:
                continue

            root = _module_root(chain[0])

            # Block direct access to dangerous modules.
            if root in FORBIDDEN_MODULES:

                return GuardrailResult.block(
                    guardrail_type="python",
                    reason=(
                        f"Access to module `{root}` "
                        "is not allowed."
                    ),
                )

            # Block dunder attributes.
            if any(
                part.startswith("__")
                for part in chain
            ):

                return GuardrailResult.block(
                    guardrail_type="python",
                    reason=(
                        "Dunder/private Python attributes "
                        "are not allowed."
                    ),
                )

            # Block obvious external file operations on
            # analytical libraries.
            if chain[-1] in FORBIDDEN_LIBRARY_CALLS:

                return GuardrailResult.block(
                    guardrail_type="python",
                    reason=(
                        f"External file/database operation "
                        f"`{'.'.join(chain)}` is not allowed. "
                        "Use `query(sql)` for database access."
                    ),
                )

        # -----------------------------------------------------
        # Function calls
        # -----------------------------------------------------

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):

                function_name = node.func.id

                if function_name in FORBIDDEN_CALLS:

                    return GuardrailResult.block(
                        guardrail_type="python",
                        reason=(
                            f"Use of `{function_name}()` "
                            "is not allowed."
                        ),
                    )

    return GuardrailResult.allow(
        guardrail_type="python",
    )