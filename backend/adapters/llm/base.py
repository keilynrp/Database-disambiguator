"""
Phase 5: Abstract base class for all LLM adapters.
All providers (OpenAI, Anthropic, DeepSeek, xAI, Google, Local) must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import List, Optional


class BaseLLMAdapter(ABC):
    """
    A unified, provider-agnostic interface for Large Language Model inference.
    Concrete implementations are injected at runtime based on the active AIIntegration record.
    """

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """
        Convert a string of text into a dense vector (embedding).
        Used to populate the ChromaDB Vector Database.
        """
        pass

    @abstractmethod
    def chat(self, system_prompt: str, user_query: str, context_chunks: List[str]) -> str:
        """
        Given a system prompt, a user question, and retrieved context documents,
        produce a grounded answer (RAG generation step).
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier e.g. 'openai'."""
        pass
