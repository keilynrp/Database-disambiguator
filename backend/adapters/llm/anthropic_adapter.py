"""
Anthropic (Claude) Adapter — Phase 5 RAG Engine
Supports: claude-3-5-sonnet-latest, claude-3-haiku-20240307
Embeddings: Falls back to sentence-transformers (Anthropic has no native embedding API).
"""
import anthropic
from typing import List
from .base import BaseLLMAdapter
from .local_adapter import LocalAdapter  # Reuse sentence-transformers for embeddings


class AnthropicAdapter(BaseLLMAdapter):

    def __init__(self, api_key: str, model_name: str = "claude-3-5-haiku-latest"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model_name = model_name
        # Claude has no embedding API — use local sentence-transformers as fallback
        self._embed_fallback = LocalAdapter(model_name="all-MiniLM-L6-v2")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def get_embedding(self, text: str) -> List[float]:
        # Route to local sentence-transformers (free, no API cost)
        return self._embed_fallback.get_embedding(text)

    def chat(self, system_prompt: str, user_query: str, context_chunks: List[str]) -> str:
        context_block = "\n\n---\n\n".join(context_chunks)
        user_content = f"CONTEXT FROM CATALOG:\n{context_block}\n\nQUESTION: {user_query}"

        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=1200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )
        return response.content[0].text
