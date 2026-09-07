import os
import sys
import time
import socket
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agent import DataAnalystAgent
from src.llm import QwenProvider, GeminiProvider
from utils.logger import AgentLogger


# =============================================================
# Configuration
# =============================================================

load_dotenv(PROJECT_ROOT / ".env")

PROVIDER = "qwen"

QWEN_MODEL_NAME = "qwen2.5:14b-instruct"
GEMINI_MODEL_NAME = "gemini-3.6-flash"

DATABASE_PATH = PROJECT_ROOT / "data" / "tpch.duckdb"
LOG_PATH = PROJECT_ROOT / "logs" / "agent_runs.jsonl"

SSH_HOST = "ECESP9"
LOCAL_OLLAMA_HOST = "127.0.0.1"
LOCAL_OLLAMA_PORT = 11434
REMOTE_OLLAMA_PORT = 11434

# =============================================================
# Provider Selection
# =============================================================
def create_llm_provider():
    """
    Create the configured LLM provider.

    Qwen uses the local Ollama endpoint.
    Gemini uses the Gemini API through its environment-based
    authentication.
    """

    if PROVIDER == "qwen":

        return QwenProvider(
            model_name=QWEN_MODEL_NAME,
            base_url="http://localhost:11434",
            temperature=0.0,
        )

    if PROVIDER == "gemini":

        return GeminiProvider(
            model_name=GEMINI_MODEL_NAME,
            temperature=0.0,
        )

    raise ValueError(
        f"Unsupported LLM provider: {PROVIDER}"
    )

# =============================================================
# SSH Tunnel
# =============================================================

def is_port_open(host: str,port: int,timeout: float = 1.0,) -> bool:
    """
    Check whether a TCP connection can be established
    to the specified host and port.
    """

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout,
        ):
            return True

    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def start_ssh_tunnel():
    """
    Ensure that an SSH tunnel exists between:

        localhost:11434
              ↓
        ECESP9:localhost:11434

    Returns:

        (process, created)

    where:

        process = SSH subprocess if this function created it
                  otherwise None.

        created = True if this function created the tunnel,
                  False if an existing tunnel was reused.
    """

    # ---------------------------------------------------------
    # Check whether an existing tunnel is already available.
    # ---------------------------------------------------------

    if is_port_open(
        LOCAL_OLLAMA_HOST,
        LOCAL_OLLAMA_PORT,
    ):
        print(
            "Existing Ollama connection detected on "
            f"{LOCAL_OLLAMA_HOST}:{LOCAL_OLLAMA_PORT}"
        )

        return None, False

    # ---------------------------------------------------------
    # Start SSH tunnel.
    # ---------------------------------------------------------

    print("Ollama connection not found.")
    print("Starting SSH tunnel to ECESP9...")

    command = [
        "ssh",
        "-N",
        "-L",
        (
            f"{LOCAL_OLLAMA_PORT}:"
            f"localhost:{REMOTE_OLLAMA_PORT}"
        ),
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ServerAliveInterval=60",
        "-o",
        "ServerAliveCountMax=3",
        SSH_HOST,
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    # ---------------------------------------------------------
    # Wait for the local tunnel endpoint to become available.
    # ---------------------------------------------------------

    max_wait_seconds = 10

    for _ in range(max_wait_seconds * 10):

        if is_port_open(
            LOCAL_OLLAMA_HOST,
            LOCAL_OLLAMA_PORT,
        ):
            print(
                "SSH tunnel established successfully."
            )

            return process, True

        # Check whether SSH exited prematurely.
        if process.poll() is not None:

            stderr = process.stderr.read().strip()

            raise RuntimeError(
                "Failed to establish SSH tunnel to ECESP9.\n"
                f"SSH error: {stderr}"
            )

        time.sleep(0.1)

    # ---------------------------------------------------------
    # Tunnel did not become available in time.
    # ---------------------------------------------------------

    process.terminate()

    try:
        process.wait(timeout=2)

    except subprocess.TimeoutExpired:
        process.kill()

    raise RuntimeError(
        "SSH tunnel could not be established within "
        f"{max_wait_seconds} seconds."
    )


def stop_ssh_tunnel(
    process: subprocess.Popen | None,
):
    """
    Stop the SSH tunnel only if this application created it.

    Existing tunnels are intentionally left untouched.
    """

    if process is None:
        return

    if process.poll() is None:

        print("\nStopping SSH tunnel...")

        process.terminate()

        try:
            process.wait(timeout=3)

        except subprocess.TimeoutExpired:

            process.kill()
            process.wait()

        print("SSH tunnel stopped.")


def verify_ollama():
    """
    Verify that Ollama is reachable through the local tunnel.

    This uses the Ollama HTTP API directly rather than
    making an LLM call.
    """

    import urllib.request
    import urllib.error

    url = (
        f"http://{LOCAL_OLLAMA_HOST}:"
        f"{LOCAL_OLLAMA_PORT}/api/tags"
    )

    try:

        with urllib.request.urlopen(
            url,
            timeout=5,
        ) as response:

            if response.status != 200:
                raise RuntimeError(
                    f"Ollama returned HTTP {response.status}."
                )

    except urllib.error.URLError as exc:

        raise RuntimeError(
            "Ollama is not reachable through the SSH tunnel.\n"
            f"Endpoint: {url}\n"
            f"Error: {exc}"
        ) from exc

    print("Ollama connection verified.")


# =============================================================
# Main
# =============================================================

def main():
    tunnel_process = None

    try:

        # -----------------------------------------------------
        # Establish / reuse provider-specific connection
        # -----------------------------------------------------

        if PROVIDER == "qwen":
            tunnel_process, tunnel_created = start_ssh_tunnel()
            verify_ollama()

        elif PROVIDER == "gemini":
            print("Using Gemini API.")

        else:
            raise ValueError(f"Unsupported LLM provider: {PROVIDER}")

        # -----------------------------------------------------
        # Create agent
        # -----------------------------------------------------

        llm_provider = create_llm_provider()
        model_name = ( QWEN_MODEL_NAME if PROVIDER == "qwen" else GEMINI_MODEL_NAME )
        agent = DataAnalystAgent(llm_provider=llm_provider,database_path=str(DATABASE_PATH),model_name=model_name,)

        logger = AgentLogger(LOG_PATH)

        print("\nData Analyst Agent")
        print("=" * 50)
        print(f"Provider: {PROVIDER}")
        print(f"Model: {model_name}")

        if PROVIDER == "qwen":
            print(
                f"Ollama: "
                f"http://{LOCAL_OLLAMA_HOST}:{LOCAL_OLLAMA_PORT}"
            )

        elif PROVIDER == "gemini":
            print("Gemini API: configured")

        # -----------------------------------------------------
        # Interactive loop
        # -----------------------------------------------------

        while True:

            question = input("\nQuestion: ").strip()

            if question.lower() in {"exit", "quit"}:
                break

            if not question:
                continue

            try:

                result = agent.invoke_streaming(question)

            except Exception as exc:

                print("\nAgent execution failed:")
                print(exc)

                # Log failed request as well.
                metrics = agent.get_metrics()
                logger.log_run(metrics)

                continue

            # -------------------------------------------------
            # Agent trace
            # -------------------------------------------------

            print("\n" + "=" * 50)
            print("AGENT TRACE")
            print("=" * 50)

            for message in result["messages"]:

                print(
                    f"\n[{message.type.upper()}]"
                )

                if message.type == "human":

                    print(message.content)

                elif message.type == "ai":

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

                        print(message.content)

                elif message.type == "tool":

                    print(f"Tool: {message.name}")
                    print(message.content)

            # -------------------------------------------------
            # Persistent logging
            # -------------------------------------------------

            metrics = agent.get_metrics()

            logger.log_run(metrics)

            print("\nExecution metrics logged.")
            print("=" * 50)

    except KeyboardInterrupt:

        print("\n\nApplication interrupted by user.")

    except Exception as exc:

        print("\nApplication startup failed:")
        print(exc)

        raise

    finally:

        # -----------------------------------------------------
        # Clean up only the tunnel created by this process.
        # -----------------------------------------------------

        stop_ssh_tunnel(tunnel_process)


# =============================================================
# Entry Point
# =============================================================

if __name__ == "__main__":
    main()