from typing import Annotated, TypedDict
import time
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from src.tools import DataAnalystTools
from src.llm import LLMProvider
from src.reviewer import ReviewerAgent, ReviewResult
from config import (build_data_analyst_prompt,SQL_TOOL_DESCRIPTION,PYTHON_TOOL_DESCRIPTION)
from config import (FULL_DATABASE_SEMANTICS, ANALYST_SEMANTICS)

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    review_result: ReviewResult | None
    analyst_retry_count: int

class SQLToolInput(BaseModel):
    query: str | None = Field(default=None,description="SQL query to execute.")
    sql: str | None = Field(default=None,description="Alternative name for the SQL query.")

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

    def __init__(self,llm_provider: LLMProvider,database_path: str,model_name: str):
        self.database_path = database_path
        self.model_name = model_name

        # Provider metadata
        self.provider = (
            llm_provider.__class__.__name__
            .replace("Provider", "")
            .lower()
        )

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

        self.llm_provider = llm_provider
        self.llm = self.llm_provider.get_model()

        self.llm_with_tools = self.llm.bind_tools(self.tools)

        # ---------------------------------------------------------
        # Reviewer
        # ---------------------------------------------------------

        self.reviewer = ReviewerAgent(
            llm_provider=llm_provider
        )

        # Maximum number of Analyst retries after the original
        # Analyst attempt.
        self.max_analyst_retries = 2

        # ---------------------------------------------------------
        # System prompt
        # ---------------------------------------------------------

        self.system_prompt = build_data_analyst_prompt(
            self.schema_context,
            ANALYST_SEMANTICS,
        )

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
        self._last_tool_error_type = None

        self.request_id = None
        self.timestamp = None
        self.question = None
        self.analysis_package = None

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

        self.analyst_retry_count = 0
        self.review_result = None

        # ---------------------------------------------------------
        # Graph
        # ---------------------------------------------------------

        self.graph = self._build_graph()

    # =============================================================
    # Utility Functions
    # =============================================================

    def _reset_metrics(self):
        self.request_id = str(uuid.uuid4())
        self.timestamp = (datetime.now(timezone.utc).isoformat())

        self.llm_call_count = 0
        self.tool_call_count = 0
        self.iteration_count = 0

        self.llm_latencies = []
        self.tool_latencies = {}

        self.tools_used = []

        self.total_latency = 0.0
        self._inspected_tool_messages = 0
        self.analyst_retry_count = 0
        self.review_result = None

        self.status = None
        self.error = None
        self._last_tool_error_type = None

        # Reset error / recovery metrics.
        self.tool_error_count = 0
        self.errors = []
        self.recovery_attempts = 0
        self.recovered = False
        self._pending_recovery = False
        self.analysis_package = None

    # =============================================================
    # Timed Tools
    # =============================================================

    def _timed_sql_tool(self):
        def execute_sql_timed(query: str | None = None,sql: str | None = None,) -> str:
            actual_query = query or sql
            if not actual_query:
                return (
                    "SQL_EXECUTION_ERROR\n"
                    "Error Type: MissingQuery\n"
                    "Message: No SQL query was provided."
                )

            start_time = time.perf_counter()

            try:
                return self.tools_backend.execute_sql(actual_query)

            finally:
                latency = (time.perf_counter()- start_time)
                self.tool_latencies.setdefault("execute_sql",[]).append(latency)

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
        sql_tool = StructuredTool.from_function(func=self._timed_sql_tool(),name="execute_sql",description=SQL_TOOL_DESCRIPTION)
        python_tool = StructuredTool.from_function(func=self._timed_python_tool(),name="execute_python",description=PYTHON_TOOL_DESCRIPTION)

        return [sql_tool,python_tool]

    # =============================================================
    # LLM Node
    # =============================================================

    def _call_model(self, state: AgentState):

        self.llm_call_count += 1
        self.iteration_count += 1

        is_recovery = self._pending_recovery
        error_type = self._last_tool_error_type

        if is_recovery:
            self.recovery_attempts += 1
            self._pending_recovery = False

        start_time = time.perf_counter()

        try:

            messages = state["messages"]

            if is_recovery:

                recovery_message = (
                    "RECOVERY INSTRUCTION: The previous tool "
                    "execution failed.\n\n"
                    f"Error type: {error_type}\n\n"
                    "Inspect the previous tool result carefully. "
                    "Identify the cause, correct the operation, "
                    "and retry with a changed tool call.\n\n"
                    "Do not repeat the same failed operation."
                )

                if error_type == "PythonImportNotAllowedError":

                    recovery_message += (
                        "\n\nIMPORTANT: Python imports are "
                        "prohibited. Do NOT use `import` or "
                        "`from ... import ...`. The Python "
                        "environment already provides `pd`, "
                        "`np`, and `query(sql)`."
                    )

                messages = [
                    *messages,
                    (
                        "system",
                        recovery_message,
                    ),
                ]

            response = self.llm_with_tools.invoke(
                messages
            )

            self.tool_call_count += len(
                response.tool_calls
            )

            for tool_call in response.tool_calls:

                self.tools_used.append(
                    tool_call["name"]
                )

            return {
                "messages": [response]
            }

        finally:

            latency = (
                time.perf_counter()
                - start_time
            )

            self.llm_latencies.append(latency)

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
                self._last_tool_error_type = error_type

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
                self._last_tool_error_type = error_type

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
    # Reviewer Node
    # =============================================================

    def _review_analysis(self, state: AgentState):
        """
        Review the completed Analyst analysis.

        The Reviewer receives:
            - user question
            - database schema
            - database semantics
            - Analyst tool calls/results
            - final Analyst answer
        """

        analysis_package = self.get_analysis_package(state)

        review_result = self.reviewer.review(
            question=analysis_package["question"],
            schema_context=analysis_package["schema"],
            semantics_context=FULL_DATABASE_SEMANTICS,
            analysis_trace=str(
                {
                    "tool_calls": analysis_package["tool_calls"],
                    "tool_results": analysis_package["tool_results"],
                }
            ),
            final_answer=analysis_package["final_answer"],
        )

        self.review_result = review_result

        print("\n[REVIEWER]")
        print(f"Status: {review_result.status}")
        print(f"Confidence: {review_result.confidence}")

        if review_result.issues:

            print("Issues:")

            for issue in review_result.issues:

                print(
                    f"  - [{issue.type}] "
                    f"{issue.description}"
                )

        else:

            print("Issues: None")

        if review_result.correction:

            print("Correction:")
            print(review_result.correction)


        return {
            "review_result": review_result
        }

    # =============================================================
    # Reviewer Routing
    # =============================================================

    def _prepare_analyst_retry(self, state: AgentState):

        retry_count = state["analyst_retry_count"] + 1

        print(
            f"\n[ANALYST RETRY] "
            f"Starting retry {retry_count}/"
            f"{self.max_analyst_retries}"
        )

        # Keep the object-level metric synchronized with the LangGraph state.
        self.analyst_retry_count = retry_count
        review_result = state.get("review_result")

        correction = ""

        if review_result is not None:
            correction = review_result.correction

        retry_message = (
            "REVIEWER FEEDBACK: The previous analysis was rejected.\n\n"
            f"Correction required:\n{correction}\n\n"
            "Re-evaluate the original user question and correct "
            "the analysis. Do not blindly repeat the previous "
            "approach."
        )

        return {
            "messages": [
                (
                    "system",
                    retry_message,
                )
            ],
            "analyst_retry_count": retry_count,
            "review_result": None,
        }


    def _route_after_review(self, state: AgentState):

        review_result = state.get("review_result")
        retry_count = state["analyst_retry_count"]

        print("\n[REVIEWER ROUTER]")

        if review_result is None:

            print("Reviewer result: None")
            print("Decision: END")

            return END

        print(f"Reviewer status: {review_result.status}")
        print(f"Analyst retry count: {retry_count}")
        print(
            f"Maximum Analyst retries: "
            f"{self.max_analyst_retries}"
        )

        # ---------------------------------------------------------
        # Reviewer accepted the Analyst result
        # ---------------------------------------------------------

        if review_result.status == "PASS":

            print("Decision: PASS → END")

            return END

        # ---------------------------------------------------------
        # Reviewer rejected the Analyst result
        # ---------------------------------------------------------

        if retry_count >= self.max_analyst_retries:

            print(
                "Decision: FAIL + retry limit reached → END"
            )

            return END

        print("Decision: FAIL → ANALYST RETRY")

        return "analyst_retry"
    
    
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

        graph.add_node(
            "reviewer",
            self._review_analysis
        )

        graph.add_node(
            "analyst_retry",
            self._prepare_analyst_retry
        )

        # ---------------------------------------------------------
        # START → Analyst
        # ---------------------------------------------------------

        graph.add_edge(
            START,
            "agent"
        )

        # ---------------------------------------------------------
        # Analyst → Tools / Reviewer
        # ---------------------------------------------------------

        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: "reviewer",
            },
        )

        # ---------------------------------------------------------
        # Tools → Error Inspection
        # ---------------------------------------------------------

        graph.add_edge(
            "tools",
            "inspect_tool_results"
        )

        # ---------------------------------------------------------
        # Error Inspection → Analyst
        # ---------------------------------------------------------

        graph.add_edge(
            "inspect_tool_results",
            "agent"
        )

        # ---------------------------------------------------------
        # Reviewer → END / Analyst Retry
        # ---------------------------------------------------------

        graph.add_conditional_edges(
            "reviewer",
            self._route_after_review,
            {
                END: END,
                "analyst_retry": "analyst_retry",
            },
        )

        # ---------------------------------------------------------
        # Analyst Retry → Analyst
        # ---------------------------------------------------------

        graph.add_edge(
            "analyst_retry",
            "agent"
        )

        return graph.compile()

    # =============================================================
    # Analysis Package
    # =============================================================

    def get_analysis_package(self, final_state: AgentState) -> dict:
        """
        Build a structured package containing everything required
        by the Reviewer Agent.

        The package contains:
            - original user question
            - database schema
            - Analyst tool calls
            - tool execution results
            - final Analyst response
        """

        messages = final_state["messages"]

        tool_calls = []
        tool_results = []
        final_answer = ""

        for message in messages:

            # -----------------------------------------------------
            # Analyst tool calls
            # -----------------------------------------------------

            if message.type == "ai" and message.tool_calls:

                for tool_call in message.tool_calls:

                    tool_calls.append(
                        {
                            "tool_name": tool_call["name"],
                            "arguments": tool_call["args"],
                            "tool_call_id": tool_call["id"],
                        }
                    )

            # -----------------------------------------------------
            # Tool execution results
            # -----------------------------------------------------

            elif isinstance(message, ToolMessage):

                tool_results.append(
                    {
                        "tool_name": message.name,
                        "tool_call_id": message.tool_call_id,
                        "result": message.content,
                    }
                )

            # -----------------------------------------------------
            # Final Analyst response
            # -----------------------------------------------------

            elif message.type == "ai" and message.content:

                final_answer = message.content

        return {
            "question": self.question,
            "schema": self.schema_context,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "final_answer": final_answer,
        }

    # =============================================================
    # Public Invocation
    # =============================================================
 
    @staticmethod
    def _print_stream_event(event_type: str,message: BaseMessage):

        print(
            f"\n[{event_type}]"
        )

        if message.type == "ai":

            if message.tool_calls:

                for tool_call in message.tool_calls:

                    print(
                        f"Tool call: "
                        f"{tool_call['name']}"
                    )

                    print(
                        f"Arguments: "
                        f"{tool_call['args']}"
                    )

            elif message.content:

                print(
                    f"Response: "
                    f"{message.content}"
                )

        elif message.type == "tool":

            print(
                f"Tool: "
                f"{message.name}"
            )

            print(
                f"Result: "
                f"{message.content}"
            )

    def invoke_streaming(self, question: str):

        self.question = question
        self._reset_metrics()

        initial_state: AgentState = {
            "messages": [
                ("system", self.system_prompt),
                ("human", question),
            ],
            "review_result": None,
            "analyst_retry_count": 0,
        }

        final_state = None
        last_message_key = None

        for state in self.graph.stream(
            initial_state,
            config={"recursion_limit": 39},
            stream_mode="values",
        ):
            final_state = state

            if not state["messages"]:
                continue

            message = state["messages"][-1]

            # `stream_mode="values"` can emit the same message again
            # when another part of the state changes, such as when
            # the Reviewer produces `review_result`.
            #
            # Use the message ID when available. Otherwise, fall back
            # to the message contents.
            message_key = getattr(message, "id", None)

            if message_key is None:
                message_key = (
                    message.type,
                    getattr(message, "name", None),
                    str(message.content),
                )

            if message_key == last_message_key:
                continue

            last_message_key = message_key

            if message.type == "ai":
                self._print_stream_event("LLM", message)

            elif message.type == "tool":
                self._print_stream_event("TOOL", message)

        if final_state is None:
            raise RuntimeError("Agent graph produced no final state.")

        self.analysis_package = self.get_analysis_package(final_state)
        self.status = "success"

        return final_state

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
                    ],
                    "review_result": None,
                    "analyst_retry_count": 0,
                },
                config={
                    "recursion_limit": 39
                },
            )

            self.analysis_package = self.get_analysis_package(result)
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

            "analyst_retry_count": self.analyst_retry_count,

            "review": (
                self.review_result.model_dump()
                if self.review_result is not None
                else None
            ),
        }