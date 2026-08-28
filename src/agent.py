from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
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

        # ---------------------------------------------------------
        # Data backend
        # ---------------------------------------------------------
        self.tools_backend = DataAnalystTools(database_path=database_path)

        # Load schema once.
        # This avoids an additional LLM → inspect_schema → LLM
        # cycle for every user question.
        self.schema_context = (self.tools_backend.get_schema_context())

        # ---------------------------------------------------------
        # Tools
        # ---------------------------------------------------------
        self.tools = self._build_tools()

        # ---------------------------------------------------------
        # LLM
        # ---------------------------------------------------------
        self.llm = ChatGoogleGenerativeAI(model=model_name)
        self.llm_with_tools = self.llm.bind_tools(self.tools)

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

8. Provide a concise explanation of the analysis performed.

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
        # Graph
        # ---------------------------------------------------------

        self.graph = self._build_graph()

    # =============================================================
    # Tool definitions
    # =============================================================

    def _build_tools(self):

        sql_tool = StructuredTool.from_function(
            func=self.tools_backend.execute_sql,
            name="execute_sql",
            description=(
                "Execute a read-only SQL query against the "
                "DuckDB database. Use SQL for filtering, "
                "aggregation, grouping, joins, sorting, "
                "and temporal analysis."
            ),
        )

        python_tool = StructuredTool.from_function(
            func=self.tools_backend.execute_python,
            name="execute_python",
            description=(
                "Execute Python/Pandas analysis against the "
                "available database tables. Use this for "
                "statistical or dataframe-oriented analysis. "
                "The final output must be stored in a variable "
                "named `result`."
            ),
        )

        return [sql_tool,python_tool]

    # =============================================================
    # LLM node
    # =============================================================

    def _call_model(self, state: AgentState):
        # One invocation of this node = one LLM API request.
        self.llm_call_count += 1

        # For the current baseline, each LLM invocation is
        # considered one agent iteration.
        self.iteration_count += 1
        response = self.llm_with_tools.invoke(state["messages"])

        # Count every tool call requested by this LLM response.
        self.tool_call_count += len(response.tool_calls)
        return {"messages": [response]}

    # =============================================================
    # Graph
    # =============================================================

    def _build_graph(self):
        graph = StateGraph(AgentState)

        # LLM node
        graph.add_node("agent",self._call_model)
        # Tool execution node
        tool_node = ToolNode(self.tools)

        graph.add_node("tools",tool_node)
        # Start → LLM
        graph.add_edge(START,"agent")

        # LLM decides:
        #
        #     tool call → tools
        #     no tool   → END
        #
        graph.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: END,
            },
        )

        # Tool result → LLM
        graph.add_edge("tools","agent")
        return graph.compile()

    # =============================================================
    # Public invocation
    # =============================================================

    def invoke(self, question: str):

        # Reset per-question metrics.
        self.llm_call_count = 0
        self.tool_call_count = 0
        self.iteration_count = 0

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
                # Prevent an accidental infinite agent loop
                # from consuming the API quota.
                "recursion_limit": 10
            },
        )

        return result

    # =============================================================
    # Metrics
    # =============================================================

    def get_metrics(self):

        return {
            "llm_calls": self.llm_call_count,
            "tool_calls": self.tool_call_count,
            "iterations": self.iteration_count,
        }