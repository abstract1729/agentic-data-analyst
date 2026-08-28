from typing import Any

import duckdb
import pandas as pd


class DataAnalystTools:
    """
    Tools available to the Data Analyst Agent.

    The class keeps the dataset/database interface centralized so that
    the agent does not need to know how the underlying data is stored.
    """

    def __init__(self, database_path: str):
        self.database_path = database_path

    def inspect_schema(self) -> str:
        """
        Return the tables, columns, data types, and row counts
        available in the DuckDB database.
        """

        conn = duckdb.connect(self.database_path, read_only=True)

        try:
            tables = conn.execute("SHOW TABLES").fetchdf()

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
                    f"COLUMNS:\n{schema.to_string(index=False)}"
                )

            return "\n\n".join(output)

        finally:
            conn.close()

    def get_schema_context(self) -> str:
        """
        Return a compact schema description intended to be injected
        into the agent's system prompt.
        """

        conn = duckdb.connect(self.database_path, read_only=True)

        try:
            tables = conn.execute("SHOW TABLES").fetchdf()

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
                        f"{row['column_name']} ({row['column_type']})"
                    )

                output.append(
                    f"{table_name}: " + ", ".join(columns)
                )

            return "\n".join(output)

        finally:
            conn.close()

    def execute_sql(self, query: str) -> str:
        """
        Execute a read-only SQL query against DuckDB.
        """

        query = query.strip()

        # Basic safety boundary for the baseline.
        forbidden = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "REPLACE",
        ]

        query_upper = query.upper()

        if any(keyword in query_upper for keyword in forbidden):
            return "ERROR: Only read-only SQL queries are allowed."

        conn = duckdb.connect(self.database_path, read_only=True)

        try:
            result = conn.execute(query).fetchdf()

            if result.empty:
                return "Query executed successfully but returned no rows."

            return result.to_string(index=False)

        except Exception as exc:
            return f"SQL execution error: {exc}"

        finally:
            conn.close()

    def execute_python(self, code: str) -> str:
        """
        Execute Python/Pandas analysis.

        This baseline implementation intentionally keeps the execution
        environment constrained to a small namespace.
        """

        conn = duckdb.connect(self.database_path, read_only=True)

        try:
            tables = conn.execute("SHOW TABLES").fetchdf()

            namespace: dict[str, Any] = {
                "pd": pd,
                "duckdb": duckdb,
            }

            for table_name in tables["name"]:
                namespace[table_name] = conn.execute(
                    f"SELECT * FROM {table_name}"
                ).fetchdf()

            exec(code, {"__builtins__": {}}, namespace)

            result = namespace.get("result")

            if result is None:
                return (
                    "Python executed successfully, "
                    "but no variable named `result` was produced."
                )

            if isinstance(result, pd.DataFrame):
                return result.to_string(index=False)

            return str(result)

        except Exception as exc:
            return f"Python execution error: {exc}"

        finally:
            conn.close()