"""
OpenAI Adapter — Phase 5 RAG Engine
Supports: gpt-4o, gpt-4o-mini, text-embedding-3-small/large
"""
import openai
from typing import List
from .base import BaseLLMAdapter


class OpenAIAdapter(BaseLLMAdapter):

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self._client = openai.OpenAI(api_key=api_key)
        self._model_name = model_name
        self._embedding_model = "text-embedding-3-small"

    @property
    def provider_name(self) -> str:
        return "openai"

    def get_embedding(self, text: str) -> List[float]:
        text = text.replace("\n", " ").strip()
        response = self._client.embeddings.create(input=[text], model=self._embedding_model)
        return response.data[0].embedding

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
