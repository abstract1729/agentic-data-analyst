SQL_TOOL_DESCRIPTION = (
    """Execute a read-only SQL query against the DuckDB database.

    SQL is the primary tool for analysis involving data stored in
    the database.

    Use SQL for operations that can naturally be expressed through
    relational and analytical queries, including:
        - filtering and selection
        - joins
        - grouping and aggregation
        - sorting
        - date and temporal analysis
        - ratios and percentages
        - differences between periods
        - year-over-year or period-over-period calculations
        - rankings and top/bottom analysis
        - conditional calculations
        - running totals
        - window-function calculations
        - derived database metrics

    Prefer completing database-oriented analysis in SQL when the
    required calculations can be expressed clearly and correctly
    in SQL. The SQL query should be supplied as the `query` argument.

    After receiving a successful SQL result, inspect whether it
    already answers the user's question before selecting another
    tool.

    If additional calculations can naturally be completed with SQL,
    continue using SQL rather than transferring the analysis to
    Python unnecessarily.

    Execute only read-only SQL queries."""
)


PYTHON_TOOL_DESCRIPTION = (
    """Execute Python/Pandas/NumPy analysis in a restricted environment.

    Python is a secondary analysis tool intended for computations
    that genuinely benefit from Python, Pandas, or NumPy.

    Use Python for tasks such as:
        - statistical calculations
        - dataframe transformations that are cumbersome in SQL
        - numerical algorithms
        - distributional analysis
        - correlation or statistical summaries
        - custom calculations that are substantially clearer in Python
        - multi-step numerical processing not naturally expressed in SQL

    Before using Python, determine whether the required analysis can
    already be completed naturally in SQL.

    Do not transfer an analysis from SQL to Python merely to perform
    operations such as filtering, grouping, aggregation, sorting,
    percentages, period-over-period differences, rankings, or other
    calculations that SQL handles naturally.

    The Python environment provides these objects directly:

        pd
            Pandas.

        np
            NumPy.

        query(sql)
            Executes a read-only SQL query against the database and
            returns the result as a Pandas DataFrame.

    Example:

        df = query("SELECT column_a, column_b FROM table_name")

    For a multiline query:

        df = query('''
            SELECT
                column_a,
                SUM(column_b) AS total
            FROM table_name
            GROUP BY column_a
        ''')

    The SQL passed to `query(...)` must be explicitly written as a
    Python string inside the current Python code.

    The Python environment does not automatically receive:
        - SQL text from a previous execute_sql call
        - the DataFrame returned by a previous tool call
        - variables created during another Python tool execution

    Therefore, do not assume variables such as `sql`, `df`, or other
    previous tool outputs already exist unless you explicitly define
    them in the current Python code.

    Each Python tool call should be treated as a self-contained
    execution.

    Pandas and NumPy are already initialized as `pd` and `np`.
    Import statements are not supported.

    Do not use:
        import ...
        from ... import ...

    Retrieve only the database data required for the computation.

    The final value that should be returned by the Python tool must
    be assigned to a variable named:

        result

    For example:

        df = query("SELECT value FROM measurements")
        result = df["value"].mean()

    or:

        df = query("SELECT category, value FROM measurements")
        summary = df.groupby("category")["value"].mean()
        result = summary

    Write valid normal Python source code using actual line breaks.
    Do not encode the Python program itself using literal `\\n`
    sequences.

    Keep the computation focused on the user's requested analysis
    and avoid repeating work already completed by another tool when
    that result is sufficient."""
)