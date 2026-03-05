"use client";

import RAGChatInterface from "../components/RAGChatInterface";

export default function RAGPage() {
    return (
        <div className="space-y-5 p-8">
            <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">🌌 Semantic RAG Assistant</h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                    Phase 5 — Query your enriched catalog with natural language. Powered by your configured AI provider and a local ChromaDB vector database.
                </p>
            </div>
            <RAGChatInterface />
        </div>
    );
}
