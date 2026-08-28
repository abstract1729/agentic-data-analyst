# Agentic Data Analyst

An experimentally evaluated AI data analyst that autonomously performs structured-data analysis using SQL and Python tools. The project investigates which agentic mechanisms—dynamic tool selection, planning, execution feedback, recovery, state, and verification—actually improve analytical reliability and at what computational cost.

## Baseline
Implement a tool-using data analysis agent using **Gemini Flash, LangGraph, and DuckDB**. The agent receives a natural-language analytical question, uses the database schema supplied as context, dynamically selects between SQL and Python analysis tools, observes tool results, and iterates until it can provide a final answer. The baseline also records the number of LLM API calls, tool calls, agent iterations and per part latency for each query.

## Experiments

### Experiment 1 — Dynamic Tool Selection

Compares a fixed analytical workflow against an agent that dynamically selects SQL, Python, and data-quality tools. Evaluates task success, tool-selection accuracy, unnecessary tool calls, latency, and token usage.

### Experiment 2 — Planning

Compares reactive execution with explicit plan-first execution. Measures whether structured planning improves multi-step analytical accuracy and how much additional latency and token cost it introduces.

### Experiment 3 — Tool Selection Analysis

Evaluates how accurately the agent selects the appropriate analytical tool for different question types. Analyzes incorrect and redundant tool selections and their effect on task completion.

### Experiment 4 — Execution Feedback

Compares execution without meaningful feedback against an agent that observes intermediate tool results and adapts subsequent actions. Evaluates multi-step accuracy, incorrect assumptions, and recovery from unexpected results.

### Experiment 5 — Error Recovery

Introduces controlled execution failures such as invalid SQL, missing columns, type errors, and empty results. Compares no recovery, simple retry, and error-aware diagnosis and correction.

### Experiment 6 — Verification

Compares immediate answer generation with analysis followed by independent verification of numerical claims, SQL evidence, assumptions, and conclusions.

### Experiment 7 — Structured State

Compares stateless execution, execution history, and structured agent state containing plans, results, errors, assumptions, and verified findings. Evaluates effects on multi-step execution and recovery.

### Experiment 8 — Ambiguity Handling

Tests how the agent handles underspecified analytical questions. Compares guessing, explicit assumptions, and clarification requests based on correctness and interaction cost.

### Experiment 9 — Data Quality Robustness

Introduces missing values, duplicates, inconsistent categories, invalid dates, and other controlled data-quality issues. Evaluates whether explicit data-quality analysis improves downstream conclusions.

### Experiment 10 — Unanswerable Questions

Tests whether the agent recognizes when the available dataset does not contain sufficient evidence to answer a question. Measures correct abstention, hallucination, and false abstention.

### Experiment 11 — Final Ablation

Progressively adds agentic capabilities to identify which mechanisms provide measurable improvements. Compares accuracy, reliability, latency, token usage, tool calls, and overall cost.

## Evaluation

All experiments use fixed benchmark questions and deterministic ground-truth checks wherever possible. Results are analyzed across task correctness, reliability, agent behavior, and computational efficiency.

## Results

*Results will be added as experiments are completed.*

## Tech Stack

Python · Pandas · NumPy · DuckDB · LangChain · LangGraph · Gemini · scikit-learn · Matplotlib
