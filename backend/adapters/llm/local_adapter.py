"""
OpenAI-Compatible Adapter — Phase 5 RAG Engine
Works for ANY OpenAI-compatible API: DeepSeek, xAI (Grok), Google (Gemini via proxy),
and Local servers like Ollama, vLLM, or LMStudio.

The adapter detects whether it's using a remote cloud URL or a local endpoint.
Local usage also generates embeddings via sentence-transformers (free, offline).
"""
from typing import List, Optional
from .base import BaseLLMAdapter


class LocalAdapter(BaseLLMAdapter):
    """
    Versatile OpenAI-compatible adapter.
    - Local: Ollama (http://localhost:11434/v1), LMStudio, vLLM
    - Cloud: DeepSeek (https://api.deepseek.com), xAI (https://api.x.ai/v1),
             Google (https://generativelanguage.googleapis.com/v1beta/openai)
    Embeddings are always computed via sentence-transformers locally.
    """
    _embedding_model = None  # Lazy loaded singleton

    def __init__(self, base_url: str = "http://localhost:11434/v1", api_key: str = "not-needed", model_name: str = "llama3"):
        import openai
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._model_name = model_name
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "local"

    def get_embedding(self, text: str) -> List[float]:
        """Uses sentence-transformers locally — no API calls, no cost."""
        if LocalAdapter._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            LocalAdapter._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        text = text.replace("\n", " ").strip()
        vector = LocalAdapter._embedding_model.encode(text).tolist()
        return vector

    def chat(self, system_prompt: str, user_query: str, context_chunks: List[str]) -> str:
        context_block = "\n\n---\n\n".join(context_chunks)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXT FROM CATALOG:\n{context_block}\n\nQUESTION: {user_query}"}
        ]
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=messages,
            temperature=0.3,
            max_tokens=1200
        )
        return response.choices[0].message.content
