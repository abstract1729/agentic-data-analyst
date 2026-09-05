from typing import Annotated, TypedDict
import time
import uuid
from datetime import datetime, timezone

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools import DataAnalystTools


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class DataAnalystAgent:
    """
    Baseline tool-using Data Analyst Agent.

    Architecture:

        User Question
              ↓
        LLM + Schema Context
              ↓
        Tool Selection
              ↓
        Tool Execution
              ↓
        Tool Result
              ↓
        Error Inspection
              ↓
        LLM
              ↓
        ...
              ↓
        Final Answer

    The database schema is loaded once during initialization and
    provided to the LLM as context. Schema inspection is therefore
    not an agent tool in the baseline.
    """

    def __init__(self, database_path: str, model_name: str):

        self.database_path = database_path
        self.model_name = model_name
        self.provider = "gemini"

        # ---------------------------------------------------------
        # Data backend
        # ---------------------------------------------------------

        self.tools_backend = DataAnalystTools(
            database_path=database_path
        )

        # Load schema once.
        self.schema_context = (
            self.tools_backend.get_schema_context()
        )

        # ---------------------------------------------------------
        # Tools
        # ---------------------------------------------------------

        self.tools = self._build_tools()

        # ---------------------------------------------------------
        # LLM
        # ---------------------------------------------------------

        self.llm = ChatGoogleGenerativeAI(
            model=model_name
        )

        self.llm_with_tools = self.llm.bind_tools(
            self.tools
        )

        # ---------------------------------------------------------
        # System prompt
        # ---------------------------------------------------------

        self.system_prompt = f"""
You are an AI Data Analyst.

Your job is to answer analytical questions using the
provided dataset.

Rules:

1. Use the provided database schema to determine which
   tables and columns are relevant.

2. Use SQL for database-oriented analysis such as:
   filtering, aggregation, grouping, joins, sorting,
   and temporal analysis.

3. Use Python/Pandas when statistical or dataframe
   analysis is more appropriate.

4. Do not invent numerical values.

5. Base all analytical conclusions on actual tool results.

6. Perform additional analysis when the available evidence
   is insufficient.

7. Clearly state when the available data cannot answer
   the question.

8. If a tool returns an execution error:
   - inspect the error carefully,
   - identify the cause,
   - correct the SQL or Python code,
   - retry the operation with a corrected query/code.

9. Do not repeatedly retry the same failed operation without
   changing the query or code.

10. Provide a concise explanation of the analysis performed.

DATABASE SCHEMA:

{self.schema_context}
"""

        # ---------------------------------------------------------
        # Execution metrics
        # ---------------------------------------------------------

        self.llm_call_count = 0
        self.tool_call_count = 0
        self.iteration_count = 0

        # ---------------------------------------------------------
        # Latencies
        # ---------------------------------------------------------

        self.llm_latencies = []
        self.tool_latencies = {}
        self.total_latency = 0.0

        # ---------------------------------------------------------
        # General run information
        # ---------------------------------------------------------

        self.tools_used = []
        self.status = None
        self.error = None

        self.request_id = None
        self.timestamp = None
        self.question = None

        # ---------------------------------------------------------
        # Error / recovery metrics
        # ---------------------------------------------------------

        # Number of tool executions that returned an error.
        self.tool_error_count = 0

        # Detailed information about each tool error.
        self.errors = []

        # Number of LLM/tool cycles performed after a tool error.
        self.recovery_attempts = 0

        # True if the agent successfully executed a tool after
        # encountering a tool error.
        self.recovered = False

        # Internal flag indicating that the next LLM call is
        # responding to a tool error.
        self._pending_recovery = False
        self._inspected_tool_messages = 0

        # ---------------------------------------------------------
        # Graph
        # ---------------------------------------------------------

        self.graph = self._build_graph()

    # =============================================================
    # Utility Functions
    # =============================================================

    def _reset_metrics(self):

        self.request_id = str(uuid.uuid4())

        self.timestamp = (
            datetime.now(timezone.utc).isoformat()
        )

        self.llm_call_count = 0
        self.tool_call_count = 0
        self.iteration_count = 0

        self.llm_latencies = []
        self.tool_latencies = {}

        self.tools_used = []

        self.total_latency = 0.0
        self._inspected_tool_messages = 0

        self.status = None
        self.error = None

        # Reset error / recovery metrics.
        self.tool_error_count = 0
        self.errors = []
        self.recovery_attempts = 0
        self.recovered = False
        self._pending_recovery = False

    # =============================================================
    # Timed Tools
    # =============================================================

    def _timed_sql_tool(self):

        def execute_sql_timed(query: str) -> str:

            start_time = time.perf_counter()

            try:
                return self.tools_backend.execute_sql(query)

            finally:

                latency = (
                    time.perf_counter()
                    - start_time
                )

                self.tool_latencies.setdefault(
                    "execute_sql",
                    []
                ).append(latency)

        return execute_sql_timed

    def _timed_python_tool(self):

        def execute_python_timed(code: str) -> str:

            start_time = time.perf_counter()

            try:
                return self.tools_backend.execute_python(code)

            finally:

                latency = (
                    time.perf_counter()
                    - start_time
                )

                self.tool_latencies.setdefault(
                    "execute_python",
                    []
                ).append(latency)

        return execute_python_timed

    # =============================================================
    # Tool Definitions
    # =============================================================

    def _build_tools(self):

        sql_tool = StructuredTool.from_function(
            func=self._timed_sql_tool(),
            name="execute_sql",
            description=(
                "Execute a read-only SQL query against the "
                "DuckDB database. Use SQL for filtering, "
                "aggregation, grouping, joins, sorting, "
                "and temporal analysis."
            ),
        )

        python_tool = StructuredTool.from_function(
            func=self._timed_python_tool(),
            name="execute_python",
            description=(
                "Execute Python/Pandas/NumPy analysis in a "
                "restricted environment. The environment "
                "provides pd, np, and query(sql). Use query(sql) "
                "to retrieve only the data required for analysis "
                "as a Pandas DataFrame. Do not import libraries "
                "or access the database directly. Use Python "
                "for statistical calculations, dataframe "
                "transformations, and numerical analysis. "
                "The final output must be stored in a variable "
                "named `result`."
            ),
        )

        return [
            sql_tool,
            python_tool,
        ]

    # =============================================================
    # LLM Node
    # =============================================================

    def _call_model(self, state: AgentState):

        self.llm_call_count += 1
        self.iteration_count += 1

        # If the previous tool execution failed, this LLM call
        # represents a recovery attempt.
        if self._pending_recovery:

            self.recovery_attempts += 1
            self._pending_recovery = False

        start_time = time.perf_counter()

        try:

            response = self.llm_with_tools.invoke(
                state["messages"]
            )

            self.tool_call_count += len(
                response.tool_calls
            )

            for tool_call in response.tool_calls:

                tool_name = tool_call["name"]

                self.tools_used.append(
                    tool_name
                )

            return {
                "messages": [response]
            }

        finally:

            latency = (
                time.perf_counter()
                - start_time
            )

            self.llm_latencies.append(
                latency
            )

    # =============================================================
    # Tool Error Inspection
    # =============================================================

    def _inspect_tool_results(self, state: AgentState):

        """
        Inspect only newly generated tool results.

        Tool implementations return structured strings such as:

            SQL_SUCCESS
            SQL_EXECUTION_ERROR
            PYTHON_SUCCESS
            PYTHON_EXECUTION_ERROR

        When an execution error is detected, record it and mark
        the next LLM call as a recovery attempt.
        """

        # ---------------------------------------------------------
        # Get all ToolMessages currently present in the state
        # ---------------------------------------------------------

        tool_messages = [ message for message in state["messages"] if isinstance(message, ToolMessage) ]

        # Only inspect ToolMessages that have not been inspected
        # during a previous pass through this node.
        new_tool_messages = tool_messages[self._inspected_tool_messages:]

        # Update the counter so these messages are not inspected again.
        self._inspected_tool_messages = len(tool_messages)

        if not new_tool_messages:
            return {"messages": []}

        # ---------------------------------------------------------
        # Inspect newly generated tool results
        # ---------------------------------------------------------

        for message in new_tool_messages:
            content = message.content

            # ToolMessage content is normally a string, but normalize
            # it defensively in case the tool returns another type.
            if not isinstance(content, str):
                content = str(content)

            # -----------------------------------------------------
            # Detect SQL execution errors
            # -----------------------------------------------------

            if content.startswith("SQL_EXECUTION_ERROR"):
                self.tool_error_count += 1
                error_type = self._extract_error_type(content)
                self.errors.append(
                    {
                        "source": "tool",
                        "tool": message.name or "execute_sql",
                        "error_type": error_type,
                        "message": content,
                    }
                )

                # The next LLM call will be a recovery attempt.
                self._pending_recovery = True

            # -----------------------------------------------------
            # Detect Python execution errors
            # -----------------------------------------------------

            elif content.startswith("PYTHON_EXECUTION_ERROR"):
                self.tool_error_count += 1
                error_type = self._extract_error_type( content )
                self.errors.append(
                    {
                        "source": "tool",
                        "tool": message.name or "execute_python",
                        "error_type": error_type,
                        "message": content,
                    }
                )

                # The next LLM call will be a recovery attempt.
                self._pending_recovery = True

            # -----------------------------------------------------
            # Detect successful execution after recovery
            # -----------------------------------------------------

            elif ( content.startswith("SQL_SUCCESS") or content.startswith("PYTHON_SUCCESS") ):

                # If a previous tool failed and the next LLM call
                # successfully executed a tool, recovery succeeded.
                if ( self.recovery_attempts > 0 and not self._pending_recovery ):
                    self.recovered = True

        return { "messages": []}

    # =============================================================
    # Error Parsing
    # =============================================================

    @staticmethod
    def _extract_error_type(content: str) -> str:

        """
        Extract:

            Error Type: BinderException

        from a structured tool error.
        """

        prefix = "Error Type:"

        for line in content.splitlines():

            line = line.strip()

            if line.startswith(prefix):

                return line[len(prefix):].strip()

        return "Unknown"

    # =============================================================
    # Graph
    # =============================================================

    def _build_graph(self):

        graph = StateGraph(AgentState)

        # ---------------------------------------------------------
        # Nodes
        # ---------------------------------------------------------

        graph.add_node(
            "agent",
            self._call_model
        )

        tool_node = ToolNode(
            self.tools
        )

        graph.add_node(
            "tools",
            tool_node
        )

        graph.add_node(
            "inspect_tool_results",
            self._inspect_tool_results
        )

        # ---------------------------------------------------------
        # Start → LLM
        # ---------------------------------------------------------

        graph.add_edge(
            START,
            "agent"
        )

        # ---------------------------------------------------------
        # LLM → Tool / END
        # ---------------------------------------------------------

        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: END,
            },
        )

        # ---------------------------------------------------------
        # Tool → Error Inspection
        # ---------------------------------------------------------

        graph.add_edge(
            "tools",
            "inspect_tool_results"
        )

        # ---------------------------------------------------------
        # Error Inspection → LLM
        # ---------------------------------------------------------

        graph.add_edge(
            "inspect_tool_results",
            "agent"
        )

        return graph.compile()

    # =============================================================
    # Public Invocation
    # =============================================================

    def invoke(self, question: str):

        self._reset_metrics()

        self.question = question

        request_start = time.perf_counter()

        try:

            result = self.graph.invoke(
                {
                    "messages": [
                        (
                            "system",
                            self.system_prompt
                        ),
                        (
                            "human",
                            question
                        ),
                    ]
                },
                config={
                    "recursion_limit": 10
                },
            )

            self.status = "success"

            return result

        except Exception as exc:

            self.status = "error"
            self.error = str(exc)

            raise

        finally:

            self.total_latency = (
                time.perf_counter()
                - request_start
            )

    # =============================================================
    # Metrics
    # =============================================================

    def get_metrics(self):

        total_llm_latency = sum(
            self.llm_latencies
        )

        total_tool_latency = sum(
            latency
            for latencies in self.tool_latencies.values()
            for latency in latencies
        )

        return {

            # -----------------------------------------------------
            # Run information
            # -----------------------------------------------------

            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "question": self.question,

            "provider": self.provider,
            "model": self.model_name,

            # -----------------------------------------------------
            # Execution counts
            # -----------------------------------------------------

            "llm_api_calls": self.llm_call_count,
            "tool_calls": self.tool_call_count,
            "iterations": self.iteration_count,

            # -----------------------------------------------------
            # Latencies
            # -----------------------------------------------------

            "llm_latencies": self.llm_latencies,
            "tool_latencies": self.tool_latencies,

            "total_llm_latency": total_llm_latency,
            "total_tool_latency": total_tool_latency,
            "total_latency": self.total_latency,

            # -----------------------------------------------------
            # Tool information
            # -----------------------------------------------------

            "tools_used": self.tools_used,

            # -----------------------------------------------------
            # Run status
            # -----------------------------------------------------

            "status": self.status,
            "error": self.error,

            # -----------------------------------------------------
            # Error / recovery information
            # -----------------------------------------------------

            "tool_error_count": self.tool_error_count,
            "errors": self.errors,
            "recovery_attempts": self.recovery_attempts,
            "recovered": self.recovered,
        }