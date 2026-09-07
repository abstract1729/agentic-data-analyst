from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """
    Gemini provider using the Google Gemini API.

    Authentication is handled through the GEMINI_API_KEY or
    GOOGLE_API_KEY environment variable.
    """

    def __init__(self,model_name: str = "gemini-2.5-flash",temperature: float = 0.0):
        self.model_name = model_name
        self.temperature = temperature
        self.llm = ChatGoogleGenerativeAI(model=self.model_name,temperature=self.temperature,)

    def get_model(self) -> BaseChatModel:
        """
        Return the configured ChatGoogleGenerativeAI model.
        """
        return self.llm