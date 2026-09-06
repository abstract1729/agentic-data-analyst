from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class LLMProvider(ABC):
    """
    Provider-agnostic interface for creating a LangChain chat model.
    """

    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """
        Return the configured LangChain chat model.
        """
        raise NotImplementedError