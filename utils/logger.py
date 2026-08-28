import json
from pathlib import Path
from typing import Any


class AgentLogger:
    """
    Persists agent execution records as JSON Lines (JSONL).

    Each call to log_run() appends exactly one execution
    record to the configured log file.
    """

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True,exist_ok=True,)

    def log_run(self, record: dict[str, Any]) -> None:
        """
        Append one agent execution record to the JSONL log.
        """

        with self.log_path.open("a",encoding="utf-8",) as f:
            f.write(json.dumps(record,default=str,)+ "\n")

