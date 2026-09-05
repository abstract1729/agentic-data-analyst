from pathlib import Path
from typing import Any

from utils.logger.schema import AgentRunRecord
from utils.logger.storage import JSONLStorage


class AgentLogger:
    """
    Logging interface for Data Analyst Agent executions.

    Responsibilities:

    1. Validate/structure execution metrics.
    2. Persist the structured record.
    3. Provide access to previously stored records.

    The logger is independent of the LLM provider,
    database, and individual tools.
    """

    def __init__(
        self,
        log_path: str | Path,
    ):
        self.storage = JSONLStorage(
            log_path
        )

    def log_run(
        self,
        record: dict[str, Any],
    ) -> None:
        """
        Validate and persist one agent execution record.
        """

        structured_record = AgentRunRecord(
            **record
        )

        self.storage.append(
            structured_record.to_dict()
        )

    def read_all(
        self,
    ) -> list[dict[str, Any]]:
        """
        Read all persisted agent execution records.
        """

        return self.storage.read_all()