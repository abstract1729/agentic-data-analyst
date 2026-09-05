import json
from pathlib import Path
from typing import Any


class JSONLStorage:
    """
    Persistent JSON Lines storage for agent execution records.

    Each agent request is stored as one JSON object per line.
    """

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)

        self.log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def append(
        self,
        record: dict[str, Any],
    ) -> None:
        """
        Append one record to the JSONL file.
        """

        with self.log_path.open(
            "a",
            encoding="utf-8",
        ) as file:

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

    def read_all(self) -> list[dict[str, Any]]:
        """
        Read all persisted records.

        Returns an empty list if the log file
        does not exist.
        """

        if not self.log_path.exists():
            return []

        records = []

        with self.log_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            for line in file:

                line = line.strip()

                if not line:
                    continue

                records.append(
                    json.loads(line)
                )

        return records