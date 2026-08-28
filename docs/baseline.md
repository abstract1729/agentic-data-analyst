# Baseline v0.1

Baseline v0.1 implements a tool-using data analysis agent using **Gemini Flash, LangGraph, and DuckDB**. The agent receives a natural-language analytical question, uses the database schema supplied as context, dynamically selects between SQL and Python analysis tools, observes tool results, and iterates until it can provide a final answer. The baseline also records the number of LLM API calls, tool calls, and agent iterations for each query.

The baseline was validated using the TPC-H SF1 dataset in DuckDB through a set of smoke tests covering schema inspection, SQL aggregation, grouping, and multi-step analytical queries. The agent produced correct answers in the tested SQL-based cases, while the Python tool exposed execution issues that will be addressed in Baseline v0.2.

## Smoke Test Results

| Test                                          | LLM API Calls | Tool Calls | Iterations | Result                                           |
| --------------------------------------------- | ------------: | ---------: | ---------: | ------------------------------------------------ |
| Tables available                              |             2 |          1 |          2 | Correct                                          |
| Total number of orders                        |             2 |          1 |          2 | Correct                                          |
| Highest customer count by market segment      |             3 |          2 |          3 | Correct                                          |
| Mean & standard deviation of order price      |             5 |          4 |          5 | Correct, but Python tool failed during execution |
| Highest average order value by market segment |             5 |          4 |          5 | Correct                                          |

### Observations

* Schema context eliminated the repeated `inspect_schema` tool call for analytical queries.
* The agent can perform multiple tool-calling iterations when it determines additional analysis is required.
* Some queries resulted in unnecessary additional SQL calls, establishing a baseline for future agent-efficiency experiments.
* Python tool execution requires refinement before it can be reliably used for analysis.
