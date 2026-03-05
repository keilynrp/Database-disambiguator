"use client";

import { useState, useRef, useEffect } from "react";

interface Message {
    role: "user" | "assistant" | "system";
    content: string;
    sources?: any[];
    provider?: string;
    model?: string;
    isLoading?: boolean;
}

export default function RAGChatInterface() {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: "system",
            content: "🧠 **Semantic RAG Assistant** — Ask anything about your catalog. I'll retrieve the most relevant documents and generate a grounded answer.",
        }
    ]);
    const [input, setInput] = useState("");
    const [isQuerying, setIsQuerying] = useState(false);
    const [isIndexing, setIsIndexing] = useState(false);
    const [indexStats, setIndexStats] = useState<{ total_indexed: number } | null>(null);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    useEffect(() => {
        fetchStats();
    }, []);

    async function fetchStats() {
        try {
            const res = await fetch("http://localhost:8000/rag/stats");
            if (res.ok) setIndexStats(await res.json());
        } catch { }
    }

    async function handleIndex() {
        setIsIndexing(true);
        try {
            const res = await fetch("http://localhost:8000/rag/index", { method: "POST" });
            if (!res.ok) throw new Error("Indexing failed");
            const data = await res.json();
            setMessages(prev => [...prev, {
                role: "assistant",
                content: `✅ **Indexing complete!** ${data.indexed} records embedded and stored in the Vector Database. ${data.skipped || 0} records skipped (insufficient data). You can now ask questions about your catalog.`
            }]);
            fetchStats();
        } catch (e) {
            setMessages(prev => [...prev, { role: "assistant", content: "❌ Indexing failed. Make sure an AI provider is configured and active." }]);
        } finally {
            setIsIndexing(false);
        }
    }

    async function handleSend(e: React.FormEvent) {
        e.preventDefault();
        const query = input.trim();
        if (!query || isQuerying) return;

        setInput("");
        const userMessage: Message = { role: "user", content: query };
        const loadingMessage: Message = { role: "assistant", content: "", isLoading: true };
        setMessages(prev => [...prev, userMessage, loadingMessage]);
        setIsQuerying(true);

        try {
            const res = await fetch("http://localhost:8000/rag/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: query, top_k: 5 })
            });
            const data = await res.json();

            setMessages(prev => {
                const next = [...prev];
                next[next.length - 1] = {
                    role: "assistant",
                    content: data.error
                        ? `⚠️ ${data.error}`
                        : data.answer,
                    sources: data.sources,
                    provider: data.provider,
                    model: data.model,
                };
                return next;
            });
        } catch {
            setMessages(prev => {
                const next = [...prev];
                next[next.length - 1] = { role: "assistant", content: "❌ Failed to connect to the RAG engine. Make sure the backend is running." };
                return next;
            });
        } finally {
            setIsQuerying(false);
        }
    }

    return (
        <div className="flex h-[calc(100vh-200px)] flex-col rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900 overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3.5 dark:border-gray-800">
                <div className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-100 text-lg dark:bg-indigo-500/20">🌌</span>
                    <div>
                        <p className="text-sm font-bold text-gray-900 dark:text-white">Semantic Context Assistant</p>
                        <p className="text-xs text-gray-500">RAG Phase 5 — Grounded by your catalog</p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    {indexStats !== null && (
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${indexStats.total_indexed > 0 ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400'}`}>
                            {indexStats.total_indexed > 0 ? `${indexStats.total_indexed} records indexed` : "Not indexed yet"}
                        </span>
                    )}
                    <button
                        onClick={handleIndex}
                        disabled={isIndexing}
                        className="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-semibold text-indigo-700 transition-colors hover:bg-indigo-100 disabled:opacity-60 dark:border-indigo-500/20 dark:bg-indigo-500/10 dark:text-indigo-400"
                    >
                        {isIndexing ? (
                            <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                        ) : "⚡"}
                        {isIndexing ? "Indexing..." : "Index Catalog"}
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {messages.map((msg, i) => (
                    <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                        {msg.role !== "user" && (
                            <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm dark:bg-indigo-500/20">
                                {msg.role === "system" ? "🧠" : "✨"}
                            </div>
                        )}
                        <div className={`max-w-[75%] space-y-2 ${msg.role === "user" ? "items-end" : ""}`}>
                            <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${msg.role === "user"
                                ? "bg-indigo-600 text-white"
                                : msg.role === "system"
                                    ? "bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-dashed border-gray-200 dark:border-gray-700"
                                    : "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200"
                                }`}>
                                {msg.isLoading ? (
                                    <div className="flex items-center gap-2 py-0.5">
                                        <div className="flex gap-1">
                                            <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:0ms]" />
                                            <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:150ms]" />
                                            <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-indigo-400 [animation-delay:300ms]" />
                                        </div>
                                        <span className="text-xs text-gray-500">Retrieving context & generating answer...</span>
                                    </div>
                                ) : (
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                )}
                            </div>

                            {/* Source pills */}
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="flex flex-wrap gap-1.5">
                                    <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Sources:</span>
                                    {msg.sources.map((src, j) => (
                                        <span key={j} className="rounded-full border border-indigo-100 bg-white px-2 py-0.5 text-[10px] font-medium text-indigo-600 dark:border-indigo-500/20 dark:bg-gray-800 dark:text-indigo-400">
                                            {src.metadata?.product_name || src.id} ({Math.round(src.similarity_score * 100)}%)
                                        </span>
                                    ))}
                                    {msg.provider && (
                                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                                            via {msg.provider} / {msg.model}
                                        </span>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t border-gray-100 p-4 dark:border-gray-800">
                <form onSubmit={handleSend} className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        disabled={isQuerying}
                        placeholder="Ask something about your catalog... e.g. 'What are the most cited products related to deep learning?'"
                        className="h-11 flex-1 rounded-xl border border-gray-200 bg-gray-50 px-4 text-sm outline-none transition-colors focus:border-indigo-400 focus:bg-white focus:ring-1 focus:ring-indigo-400 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-white dark:focus:bg-gray-800"
                    />
                    <button
                        type="submit"
                        disabled={isQuerying || !input.trim()}
                        className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-600 text-white transition-colors hover:bg-indigo-700 disabled:opacity-40"
                    >
                        {isQuerying ? (
                            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                        ) : (
                            <svg className="h-4 w-4 rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        )}
                    </button>
                </form>
            </div>
        </div>
    );
}
