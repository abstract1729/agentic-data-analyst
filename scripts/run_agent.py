import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import DataAnalystAgent


load_dotenv(PROJECT_ROOT / ".env")


MODEL_NAME = "gemini-3.6-flash"
DATABASE_PATH = PROJECT_ROOT / "data" / "tpch.duckdb"


def main():
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Add it to the .env file."
        )

    agent = DataAnalystAgent(database_path=str(DATABASE_PATH),model_name=MODEL_NAME)

    print("Data Analyst Agent")
    print("=" * 50)

    while True:
        question = input("\nQuestion: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue

        try:
            result = agent.invoke(question)

        except Exception as exc:
            print("\nAgent execution failed:")
            print(exc)
            continue

        # ---------------------------------------------------------
        # Agent trace
        # ---------------------------------------------------------

        print("\n" + "=" * 50)
        print("AGENT TRACE")
        print("=" * 50)

        for message in result["messages"]:
            print(f"\n[{message.type.upper()}]")

            if message.type == "human":
                print(message.content)

            elif message.type == "ai":
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        print(f"Tool call: {tool_call['name']}")
                        print(f"Arguments: {tool_call['args']}")

                elif message.content:
                    print(message.content)

            elif message.type == "tool":
                print(f"Tool: {message.name}")
                print(message.content)

        # ---------------------------------------------------------
        # Metrics
        # ---------------------------------------------------------

        metrics = agent.get_metrics()

        print("\n" + "=" * 50)
        print("METRICS")
        print("=" * 50)

        print(f"LLM calls:    {metrics['llm_calls']}")
        print(f"Tool calls:   {metrics['tool_calls']}")
        print(f"Iterations:   {metrics['iterations']}")

        print("=" * 50)


if __name__ == "__main__":
    main()