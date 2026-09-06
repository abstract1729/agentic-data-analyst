from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel

from .base import LLMProvider


class QwenProvider(LLMProvider):
    """
    Qwen provider using Ollama as the inference server.

    The Ollama server is expected to be reachable through the
    configured HTTP endpoint. SSH tunneling is handled outside
    this provider.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:14b-instruct",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature

        self.llm = ChatOllama(
            model=self.model_name,
            base_url=self.base_url,
            temperature=self.temperature,
        )

    def get_model(self) -> BaseChatModel:
        """
        Return the configured ChatOllama model.
        """
        return self.llm