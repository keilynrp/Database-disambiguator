"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

interface Relationship {
    id: number;
    source_id: number;
    target_id: number;
    relation_type: string;
    weight: number;
    notes: string | null;
    created_at: string;
}

const RELATION_TYPES = ["cites", "authored-by", "belongs-to", "related-to"];

const TYPE_COLORS: Record<string, string> = {
    "cites":       "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400",
    "authored-by": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400",
    "belongs-to":  "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400",
    "related-to":  "bg-violet-100 text-violet-700 dark:bg-violet-500/10 dark:text-violet-400",
};

export default function RelationshipManager({
    entityId,
    onRefreshGraph,
}: {
    entityId: number;
    onRefreshGraph: () => void;
}) {
    const [relationships, setRelationships] = useState<Relationship[]>([]);
    const [loading, setLoading] = useState(true);

    // Add form state
    const [targetId, setTargetId] = useState("");
    const [relType, setRelType] = useState("related-to");
    const [weight, setWeight] = useState("1.0");
    const [notes, setNotes] = useState("");
    const [adding, setAdding] = useState(false);
    const [addError, setAddError] = useState<string | null>(null);

    const [deletingId, setDeletingId] = useState<number | null>(null);

    useEffect(() => {
        fetchRelationships();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [entityId]);

    async function fetchRelationships() {
        setLoading(true);
        try {
            const res = await apiFetch(`/entities/${entityId}/relationships`);
            if (res.ok) setRelationships(await res.json());
        } finally {
            setLoading(false);
        }
    }

    async function handleAdd(e: React.FormEvent) {
        e.preventDefault();
        setAddError(null);
        const tid = parseInt(targetId);
        if (!tid || isNaN(tid)) { setAddError("Target entity ID must be a number"); return; }
        setAdding(true);
        try {
            const res = await apiFetch(`/entities/${entityId}/relationships`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    target_id: tid,
                    relation_type: relType,
                    weight: parseFloat(weight) || 1.0,
                    notes: notes.trim() || null,
                }),
            });
            if (!res.ok) {
                const err = await res.json();
                setAddError(err.detail ?? "Failed to add relationship");
                return;
            }
            setTargetId("");
            setNotes("");
            setWeight("1.0");
            await fetchRelationships();
            onRefreshGraph();
        } finally {
            setAdding(false);
        }
    }

    async function handleDelete(relId: number) {
        setDeletingId(relId);
        try {
            await apiFetch(`/relationships/${relId}`, { method: "DELETE" });
            setRelationships((prev) => prev.filter((r) => r.id !== relId));
            onRefreshGraph();
        } finally {
            setDeletingId(null);
        }
    }

    return (
        <div className="space-y-5">
            {/* Add form */}
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50">
                <p className="mb-3 text-xs font-bold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                    Add Relationship
                </p>
                <form onSubmit={handleAdd} className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <div>
                        <label className="mb-1 block text-[10px] font-medium text-gray-500">Target Entity ID</label>
                        <input
                            type="number"
                            min="1"
                            value={targetId}
                            onChange={(e) => setTargetId(e.target.value)}
                            placeholder="e.g. 42"
                            className="h-8 w-full rounded-lg border border-gray-200 bg-white px-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                            required
                        />
                    </div>
                    <div>
                        <label className="mb-1 block text-[10px] font-medium text-gray-500">Relation Type</label>
                        <select
                            value={relType}
                            onChange={(e) => setRelType(e.target.value)}
                            className="h-8 w-full rounded-lg border border-gray-200 bg-white px-2 text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                        >
                            {RELATION_TYPES.map((t) => (
                                <option key={t} value={t}>{t}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="mb-1 block text-[10px] font-medium text-gray-500">Weight (0–10)</label>
                        <input
                            type="number"
                            min="0"
                            max="10"
                            step="0.1"
                            value={weight}
                            onChange={(e) => setWeight(e.target.value)}
                            className="h-8 w-full rounded-lg border border-gray-200 bg-white px-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                        />
                    </div>
                    <div className="flex items-end">
                        <button
                            type="submit"
                            disabled={adding}
                            className="h-8 w-full rounded-lg bg-indigo-600 px-3 text-xs font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                        >
                            {adding ? "Adding\u2026" : "+ Add"}
                        </button>
                    </div>
                    <div className="col-span-2 sm:col-span-4">
                        <input
                            type="text"
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="Optional notes\u2026"
                            maxLength={500}
                            className="h-8 w-full rounded-lg border border-gray-200 bg-white px-2.5 text-sm outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-400 dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                        />
                    </div>
                </form>
                {addError && (
                    <p className="mt-2 text-xs text-red-600 dark:text-red-400">{addError}</p>
                )}
            </div>

            {/* Relationship list */}
            {loading ? (
                <div className="flex h-20 items-center justify-center">
                    <svg className="h-5 w-5 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                </div>
            ) : relationships.length === 0 ? (
                <p className="text-center text-sm text-gray-400 dark:text-gray-500">No relationships yet.</p>
            ) : (
                <div className="space-y-2">
                    {relationships.map((rel) => {
                        const isSource = rel.source_id === entityId;
                        const otherId = isSource ? rel.target_id : rel.source_id;
                        const direction = isSource ? "\u2192" : "\u2190";
                        const typeColor = TYPE_COLORS[rel.relation_type] ?? "bg-gray-100 text-gray-700";
                        return (
                            <div
                                key={rel.id}
                                className="flex items-center gap-3 rounded-lg border border-gray-100 bg-white px-3 py-2.5 shadow-sm dark:border-gray-800 dark:bg-gray-900"
                            >
                                <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-bold ${typeColor}`}>
                                    {rel.relation_type}
                                </span>
                                <span className="text-xs text-gray-400">{direction}</span>
                                <Link
                                    href={`/entities/${otherId}`}
                                    className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                                >
                                    Entity #{otherId}
                                </Link>
                                {rel.weight !== 1.0 && (
                                    <span className="text-[10px] text-gray-400">w={rel.weight}</span>
                                )}
                                {rel.notes && (
                                    <span className="truncate text-xs text-gray-400 italic">{rel.notes}</span>
                                )}
                                <button
                                    onClick={() => handleDelete(rel.id)}
                                    disabled={deletingId === rel.id}
                                    className="ml-auto shrink-0 rounded p-1 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-500 disabled:opacity-50 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                                    title="Delete relationship"
                                >
                                    <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
