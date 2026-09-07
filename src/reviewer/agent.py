from typing import Any

from src.llm import QwenProvider
from config import REVIEWER_SYSTEM_PROMPT

from .schemas import ReviewResult


class ReviewerAgent:
    """
    Reviewer Agent responsible for evaluating the output
    produced by the Data Analyst Agent.

    The Reviewer does not execute SQL or Python. It evaluates
    the Analyst's reasoning, tool usage, evidence, and final
    answer against the user's question and database semantics.
    """

    def __init__(
        self,
        model_name: str,
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        self.model_name = model_name
        self.provider = "qwen"

        self.llm_provider = QwenProvider(
            model_name=model_name,
            base_url=base_url,
            temperature=temperature,
        )

        self.llm = self.llm_provider.get_model()

        self.reviewer_llm = (
            self.llm.with_structured_output(
                ReviewResult
            )
        )

    # =============================================================
    # Review
    # =============================================================

    def review(
        self,
        question: str,
        schema_context: str,
        semantics_context: str,
        analysis_trace: str,
        final_answer: str,
    ) -> ReviewResult:
        """
        Review the Analyst's completed analysis.

        Args:
            question:
                Original user question.

            schema_context:
                Database schema available to the Analyst.

            semantics_context:
                Business and column semantics used to interpret
                the database.

            analysis_trace:
                Tool calls and tool results produced by the Analyst.

            final_answer:
                Analyst's proposed final answer.

        Returns:
            Structured ReviewResult.
        """

        review_prompt = f"""
{REVIEWER_SYSTEM_PROMPT}

============================================================
USER QUESTION
============================================================

{question}

============================================================
DATABASE SCHEMA
============================================================

{schema_context}

============================================================
DATABASE SEMANTICS
============================================================

{semantics_context}

============================================================
ANALYST ANALYSIS TRACE
============================================================

{analysis_trace}

============================================================
ANALYST FINAL ANSWER
============================================================

{final_answer}

============================================================
REVIEW TASK
============================================================

Evaluate the Analyst's work against the original question,
database schema, and database semantics.

Pay particular attention to:

- whether the Analyst interpreted the requested metric correctly;
- whether the correct columns and date dimensions were used;
- whether calculations are mathematically correct;
- whether numerical claims match the tool results;
- whether the answer addresses every part of the question;
- whether the final answer contains unsupported claims.

Return PASS only if the analysis and final answer are
semantically correct, numerically consistent, evidence-based,
and complete.

Otherwise return FAIL with specific issues and an actionable
correction for the Analyst.
""".strip()

        return self.reviewer_llm.invoke(
            review_prompt
        )