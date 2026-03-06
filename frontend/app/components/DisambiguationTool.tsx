"use client";

import { useState, useEffect } from "react";
import { useDomain } from "../contexts/DomainContext";
import { apiFetch } from "@/lib/api";

interface VariationGroup {
    main: string;
    variations: string[];
    count: number;
}

interface DisambiguationResponse {
    groups: VariationGroup[];
    total_groups: number;
}

export default function DisambiguationTool() {
    const { activeDomain } = useDomain();
    const [field, setField] = useState("");

    // Auto-select first string field when domain loads
    useEffect(() => {
        if (activeDomain && !field) {
            const firstString = activeDomain.attributes.find(a => a.type === "string");
            if (firstString) setField(firstString.name);
        }
    }, [activeDomain, field]);

    const [groups, setGroups] = useState<VariationGroup[]>([]);
    const [loading, setLoading] = useState(false);
    const [totalGroups, setTotalGroups] = useState(0);
    const [resolvingIdx, setResolvingIdx] = useState<number | null>(null);
    const [resolutions, setResolutions] = useState<Record<number, { canonical_value: string; reasoning: string }>>({});
    const [processingRule, setProcessingRule] = useState<number | null>(null);

    async function analyze() {
        setLoading(true);
        try {
            const res = await apiFetch(`/disambiguate/${field}`);
            if (!res.ok) throw new Error("Failed to fetch analysis");
            const data: DisambiguationResponse = await res.json();
            setGroups(data.groups);
            setTotalGroups(data.total_groups);
        } catch (error) {
            console.error(error);
            alert("Error analyzing data");
        } finally {
            setLoading(false);
        }
    }

    async function resolveWithAI(idx: number, variations: string[]) {
        setResolvingIdx(idx);
        try {
            const res = await apiFetch(`/disambiguate/ai-resolve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ field_name: field, variations })
            });
            if (!res.ok) throw new Error("AI resolve failed");
            const data = await res.json();
            setResolutions(prev => ({ ...prev, [idx]: data }));
        } catch (error) {
            console.error(error);
            alert("Error from AI resolution endpoint");
        } finally {
            setResolvingIdx(null);
        }
    }

    async function acceptResolution(idx: number, canonical_value: string, variations: string[]) {
        setProcessingRule(idx);
        try {
            const res = await apiFetch(`/rules/bulk`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ field_name: field, canonical_value, variations })
            });
            if (!res.ok) throw new Error("Failed to save rules");

            // Execute rules to update database entities
            const applyRes = await apiFetch(`/rules/apply?field_name=${field}`, { method: "POST" });
            if (!applyRes.ok) throw new Error("Failed to apply rules to database");

            // Re-fetch groups after applying to see updated list
            analyze();
        } catch (error) {
            console.error(error);
            alert("Error applying rules");
        } finally {
            setProcessingRule(null);
        }
    }

    // Helper to get friendly label
    const fieldLabel = activeDomain?.attributes.find(a => a.name === field)?.label || field;

    return (
        <div className="space-y-6">
            {/* Controls card */}
            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                <div className="flex flex-wrap items-end gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Knowledge Attribute to Analyze
                        </label>
                        <select
                            value={field}
                            onChange={(e) => setField(e.target.value)}
                            className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                        >
                            {activeDomain ? (
                                activeDomain.attributes
                                    .filter(a => a.type === 'string')
                                    .map(attr => (
                                        <option key={attr.name} value={attr.name}>{attr.label}</option>
                                    ))
                            ) : (
                                <option value="">Loading attributes...</option>
                            )}
                        </select>
                    </div>
                    <button
                        onClick={analyze}
                        disabled={loading}
                        className="inline-flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {loading ? (
                            <>
                                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                                Parsing context...
                            </>
                        ) : (
                            <>
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                Find Inconsistencies
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Results summary */}
            {groups.length > 0 && (
                <div className="flex gap-4">
                    <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Resolved Groups</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">{totalGroups}</p>
                    </div>
                    <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Attribute</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">{fieldLabel}</p>
                    </div>
                    <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Lexical Variations</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                            {groups.reduce((acc, g) => acc + g.count, 0)}
                        </p>
                    </div>
                </div>
            )}

            {/* Variation groups */}
            <div className="space-y-4">
                {groups.map((group, idx) => (
                    <div key={idx} className="rounded-2xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md dark:border-gray-800 dark:bg-gray-900">
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                                {group.main}
                            </h3>
                            <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                                {group.count} variants matched
                            </span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {group.variations.map((v, i) => (
                                <span
                                    key={i}
                                    className="inline-flex items-center rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1 text-sm text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
                                >
                                    {v}
                                </span>
                            ))}
                        </div>

                        {/* Integration of LLM / AI Resolution block */}
                        {resolutions[idx] ? (
                            <div className="mt-4 rounded-xl relative border border-indigo-200 bg-indigo-50/50 p-4 dark:border-indigo-500/30 dark:bg-indigo-500/10">
                                <div className="absolute right-4 top-4 text-indigo-400 dark:text-indigo-500">
                                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                    </svg>
                                </div>
                                <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">Semantic AI Recommendation</p>
                                <div className="mt-2 flex items-end justify-between">
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Canonical term:</span>
                                            <span className="inline-flex items-center rounded bg-indigo-100 px-2 py-0.5 font-mono text-lg font-bold text-indigo-800 dark:bg-indigo-500/20 dark:text-indigo-300">
                                                {resolutions[idx].canonical_value}
                                            </span>
                                        </div>
                                        <p className="mt-2 max-w-xl text-xs text-slate-600 dark:text-slate-400">
                                            <strong className="text-slate-700 dark:text-slate-300">Reasoning: </strong>
                                            {resolutions[idx].reasoning}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => acceptResolution(idx, resolutions[idx].canonical_value, group.variations)}
                                        disabled={processingRule === idx}
                                        className="ml-4 shrink-0 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700 disabled:opacity-50"
                                    >
                                        {processingRule === idx ? "Applying..." : "Approve & Merge"}
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="mt-4 flex justify-end">
                                <button
                                    onClick={() => resolveWithAI(idx, group.variations)}
                                    disabled={resolvingIdx === idx}
                                    className="inline-flex items-center gap-2 rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:bg-indigo-50 disabled:opacity-50 dark:border-indigo-800 dark:bg-gray-900 dark:text-indigo-400 dark:hover:bg-indigo-900/30"
                                >
                                    {resolvingIdx === idx ? (
                                        <>
                                            <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                            Analyzing...
                                        </>
                                    ) : (
                                        <>
                                            <svg className="h-3.5 w-3.5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                            </svg>
                                            Auto-Resolve via AI
                                        </>
                                    )}
                                </button>
                            </div>
                        )}
                    </div>
                ))}
                {groups.length === 0 && !loading && (
                    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-16 dark:border-gray-700">
                        <svg className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Ready for Ontological Analysis</p>
                        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Pick an entity attribute to find naming inconsistencies in the repository</p>
                    </div>
                )}
            </div>
        </div>
    );
}
