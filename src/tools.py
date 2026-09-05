from typing import Any

import duckdb
import numpy as np
import pandas as pd


class DataAnalystTools:
    """
    Tools available to the Data Analyst Agent.

    The class centralizes access to the underlying DuckDB database.
    """

    def __init__(self, database_path: str):
        self.database_path = database_path

    # =============================================================
    # Schema
    # =============================================================

    def inspect_schema(self) -> str:
        """
        Return tables, columns, data types, and row counts
        available in the DuckDB database.
        """

        conn = duckdb.connect(
            self.database_path,
            read_only=True,
        )

        try:
            tables = conn.execute(
                "SHOW TABLES"
            ).fetchdf()

            if tables.empty:
                return "No tables are available in the database."

            output = []

            for table_name in tables["name"]:

                schema = conn.execute(
                    f"DESCRIBE {table_name}"
                ).fetchdf()

                row_count = conn.execute(
                    f"SELECT COUNT(*) AS count FROM {table_name}"
                ).fetchone()[0]

                output.append(
                    f"TABLE: {table_name}\n"
                    f"ROWS: {row_count}\n"
                    f"COLUMNS:\n"
                    f"{schema.to_string(index=False)}"
                )

            return "\n\n".join(output)

        except Exception as exc:

            return (
                "SCHEMA_ERROR\n"
                f"Error Type: {type(exc).__name__}\n"
                f"Message: {exc}"
            )

        finally:
            conn.close()

    def get_schema_context(self) -> str:
        """
        Return a compact schema description intended for
        inclusion in the agent system prompt.
        """

        conn = duckdb.connect(
            self.database_path,
            read_only=True,
        )

        try:
            tables = conn.execute(
                "SHOW TABLES"
            ).fetchdf()

            if tables.empty:
                return "No tables are available."

            output = []

            for table_name in tables["name"]:

                schema = conn.execute(
                    f"DESCRIBE {table_name}"
                ).fetchdf()

                columns = []

                for _, row in schema.iterrows():

                    columns.append(
                        f"{row['column_name']} "
                        f"({row['column_type']})"
                    )

                output.append(
                    f"{table_name}: "
                    + ", ".join(columns)
                )

            return "\n".join(output)

        except Exception as exc:

            return (
                "SCHEMA_CONTEXT_ERROR\n"
                f"Error Type: {type(exc).__name__}\n"
                f"Message: {exc}"
            )

        finally:
            conn.close()

    # =============================================================
    # SQL Execution
    # =============================================================

    @staticmethod
    def _validate_read_only_query(query: str) -> str:
        """
        Validate that a query is read-only.

        For the baseline, only SELECT and WITH queries are allowed.
        """

        if not isinstance(query, str):
            raise TypeError(
                "SQL query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "SQL query cannot be empty."
            )

        query_upper = query.upper()

        if not (
            query_upper.startswith("SELECT")
            or query_upper.startswith("WITH")
        ):
            raise ValueError(
                "Only SELECT or WITH queries are allowed."
            )

        forbidden = [
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
        ]

        if any(
            keyword in query_upper
            for keyword in forbidden
        ):
            raise ValueError(
                "Only read-only SQL queries are allowed."
            )

        return query

    def _query_dataframe(
        self,
        query: str,
    ) -> pd.DataFrame:
        """
        Execute a validated read-only SQL query and return
        the result as a Pandas DataFrame.

        This is the controlled database interface exposed
        to the Python analysis environment.
        """

        query = self._validate_read_only_query(query)

        conn = duckdb.connect(
            self.database_path,
            read_only=True,
        )

        try:
            return conn.execute(query).fetchdf()

        finally:
            conn.close()

    def execute_sql(self, query: str) -> str:
        """
        Execute a read-only SQL query against DuckDB.

        Use this tool for database-oriented operations such as:

        - filtering
        - aggregation
        - grouping
        - joins
        - sorting
        - counts
        - sums
        - averages
        - temporal analysis
        """

        try:

            result = self._query_dataframe(query)

            if result.empty:
                return (
                    "SQL_SUCCESS\n"
                    "Query executed successfully "
                    "but returned no rows."
                )

            return (
                "SQL_SUCCESS\n"
                + result.to_string(index=False)
            )

        except Exception as exc:

            return (
                "SQL_EXECUTION_ERROR\n"
                f"Error Type: {type(exc).__name__}\n"
                f"Message: {exc}"
            )

    # =============================================================
    # Python Execution
    # =============================================================

    def execute_python(self, code: str) -> str:
        """
        Execute Python/Pandas/NumPy analysis in a restricted
        environment.

        The Python environment does NOT contain complete database
        tables.

        Instead, the agent can use:

            query("SELECT ...")

        to retrieve only the data required for its analysis.

        Available objects:

            pd       - Pandas
            np       - NumPy
            query    - controlled read-only DuckDB query function

        The final result must be stored in a variable named `result`.
        """

        if not isinstance(code, str):
            return (
                "PYTHON_EXECUTION_ERROR\n"
                "Error Type: TypeError\n"
                "Message: Python code must be a string."
            )

        def query(sql: str) -> pd.DataFrame:
            """
            Execute a read-only SQL query and return the
            result as a Pandas DataFrame.

            SQL errors are propagated to the Python execution
            environment so they can be handled as Python-side
            execution failures.
            """

            return self._query_dataframe(sql)

        safe_builtins: dict[str, Any] = {
            "abs": abs,
            "all": all,
            "any": any,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "set": set,
            "sorted": sorted,
            "sum": sum,
            "tuple": tuple,
            "zip": zip,
            "enumerate": enumerate,
        }

        execution_globals: dict[str, Any] = {
            "__builtins__": safe_builtins,
            "pd": pd,
            "np": np,
            "query": query,
        }

        try:

            exec(
                code,
                execution_globals,
                execution_globals,
            )

            result = execution_globals.get("result")

            if result is None:
                return (
                    "PYTHON_EXECUTION_ERROR\n"
                    "Error Type: MissingResult\n"
                    "Message: Python executed successfully, "
                    "but no variable named `result` was produced."
                )

            if isinstance(result, pd.DataFrame):

                if result.empty:
                    return (
                        "PYTHON_SUCCESS\n"
                        "Python analysis completed "
                        "but produced an empty DataFrame."
                    )

                return (
                    "PYTHON_SUCCESS\n"
                    + result.to_string(index=False)
                )

            return (
                "PYTHON_SUCCESS\n"
                + str(result)
            )

        except Exception as exc:

            return (
                "PYTHON_EXECUTION_ERROR\n"
                f"Error Type: {type(exc).__name__}\n"
                f"Message: {exc}"
            )