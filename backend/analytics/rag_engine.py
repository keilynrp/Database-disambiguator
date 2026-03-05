"""
Phase 5: RAG Engine — Orchestration Layer
Coordinates the full Retrieval-Augmented Generation pipeline:
  1. Load the active AI provider from the database (BYOK)
  2. Build a LLM adapter instance dynamically
  3. Index catalog records into ChromaDB
  4. Query the vector store and generate responses
"""
import logging
from typing import Optional, List, Dict, Any

from backend.analytics.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

# System prompt that grounds the LLM strictly in catalog data
SYSTEM_PROMPT = """You are a specialized research assistant for DB Disambiguador, a scientometric catalog tool.
Your knowledge comes EXCLUSIVELY from the provided context extracted from the catalog.
Answer questions directly based on the catalog entries, citations, and concepts shown in the context.
If the context doesn't contain enough information to answer confidently, say so transparently.
Be concise, structured, and factual. Respond in the same language used in the question.
"""


def _build_adapter(integration_record) -> Optional[object]:
    """
    Factory function — reads the active AIIntegration record and returns
    the correct concrete LLM adapter instance.
    """
    if not integration_record:
        return None

    provider = integration_record.provider_name
    api_key = integration_record.api_key or ""
    base_url = integration_record.base_url or ""
    model_name = integration_record.model_name or ""

    try:
        if provider == "openai":
            from backend.adapters.llm.openai_adapter import OpenAIAdapter
            return OpenAIAdapter(api_key=api_key, model_name=model_name or "gpt-4o-mini")

        elif provider == "anthropic":
            from backend.adapters.llm.anthropic_adapter import AnthropicAdapter
            return AnthropicAdapter(api_key=api_key, model_name=model_name or "claude-3-5-haiku-latest")

        elif provider in ("deepseek", "xai", "google", "local"):
            from backend.adapters.llm.local_adapter import LocalAdapter

            BASE_URLS = {
                "deepseek": "https://api.deepseek.com",
                "xai": "https://api.x.ai/v1",
                "google": "https://generativelanguage.googleapis.com/v1beta/openai",
            }
            DEFAULT_MODELS = {
                "deepseek": "deepseek-chat",
                "xai": "grok-3-mini",
                "google": "gemini-2.0-flash",
                "local": "llama3",
            }
            resolved_base_url = base_url if provider == "local" else BASE_URLS.get(provider, base_url)
            resolved_model = model_name or DEFAULT_MODELS.get(provider, "")
            return LocalAdapter(base_url=resolved_base_url, api_key=api_key, model_name=resolved_model)

        else:
            logger.warning(f"RAGEngine: Unknown provider '{provider}'")
            return None

    except Exception as e:
        logger.error(f"RAGEngine: Failed to build adapter for '{provider}': {e}")
        return None


def index_product(product, integration_record) -> Dict[str, Any]:
    """
    Phase 5 / Indexing Step:
    Converts a product's enrichment data into an embedding and stores it in ChromaDB.
    """
    adapter = _build_adapter(integration_record)
    if not adapter:
        return {"status": "error", "message": "No active AI provider configured."}

    # Build the canonical text representation of the product for embedding
    parts = [
        f"Title: {product.product_name or ''}",
        f"Brand: {product.brand_capitalized or ''}",
        f"Type: {product.product_type or ''}",
        f"Concepts: {product.enrichment_concepts or ''}",
        f"Citation Count: {product.enrichment_citation_count or 0}",
        f"Source API: {product.enrichment_source or ''}",
    ]
    text = " | ".join(p for p in parts if p.split(": ")[1])

    if not text.strip() or len(text) < 20:
        return {"status": "skipped", "message": "Insufficient data for indexing."}

    try:
        embedding = adapter.get_embedding(text)
        doc_id = f"product-{product.id}"

        VectorStoreService.upsert_document(
            doc_id=doc_id,
            text=text,
            embedding=embedding,
            metadata={
                "product_id": product.id,
                "product_name": product.product_name or "",
                "citation_count": product.enrichment_citation_count or 0,
                "source": product.enrichment_source or "unknown",
                "provider_used": adapter.provider_name,
            }
        )
        return {"status": "indexed", "doc_id": doc_id, "provider": adapter.provider_name}
    except Exception as e:
        logger.error(f"RAGEngine index error for product {product.id}: {e}")
        return {"status": "error", "message": str(e)}


def query_catalog(user_question: str, integration_record, top_k: int = 5) -> Dict[str, Any]:
    """
    Phase 5 / Generation Step:
    1. Embed the user's question
    2. Retrieve the most relevant catalog documents
    3. Send to LLM for grounded, context-aware generation
    """
    adapter = _build_adapter(integration_record)
    if not adapter:
        return {"error": "No active AI provider configured. Please set an active provider in Integrations → AI Language Models."}

    try:
        # Step 1: Embed user query
        query_embedding = adapter.get_embedding(user_question)

        # Step 2: Retrieve relevant context
        retrieved_docs = VectorStoreService.query(query_embedding, top_k=top_k)

        if not retrieved_docs:
            return {
                "answer": "The catalog knowledge base is empty. Please index your catalog records first using the 'Index Catalog' button.",
                "sources": []
            }

        context_chunks = [doc["text"] for doc in retrieved_docs]

        # Step 3: Generate answer with grounded context
        answer = adapter.chat(
            system_prompt=SYSTEM_PROMPT,
            user_query=user_question,
            context_chunks=context_chunks
        )

        return {
            "answer": answer,
            "provider": adapter.provider_name,
            "model": getattr(adapter, "_model_name", "unknown"),
            "sources": retrieved_docs,
            "context_chunks_used": len(context_chunks)
        }

    except Exception as e:
        logger.error(f"RAGEngine query error: {e}")
        return {"error": str(e)}
