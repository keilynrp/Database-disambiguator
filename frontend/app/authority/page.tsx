"use client";

import { useState } from "react";

interface AuthorityGroup {
    main: string;
    variations: string[];
    count: number;
    has_rules: boolean;
    resolved_to: string | null;
}

interface AuthorityResponse {
    groups: AuthorityGroup[];
    total_groups: number;
    total_rules: number;
    pending_groups: number;
}

interface ApplyResult {
    rules_applied: number;
    records_updated: number;
}

interface GroupState {
    canonical: string;
    excluded: Set<string>;
    saved: boolean;
}

const fieldLabels: Record<string, string> = {
    brand_capitalized: "Brand",
    product_name: "Product Name",
    model: "Model",
    product_type: "Product Type",
};

export default function AuthorityPage() {
    const [field, setField] = useState("brand_capitalized");
    const [data, setData] = useState<AuthorityResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [applying, setApplying] = useState(false);
    const [applyResult, setApplyResult] = useState<ApplyResult | null>(null);
    const [groupStates, setGroupStates] = useState<Record<number, GroupState>>({});
    const [savingGroup, setSavingGroup] = useState<number | null>(null);

    async function analyze() {
        setLoading(true);
        setData(null);
        setGroupStates({});
        setApplyResult(null);
        try {
            const res = await fetch(`http://localhost:8000/authority/${field}`);
            if (!res.ok) throw new Error("Failed to fetch");
            const json: AuthorityResponse = await res.json();
            setData(json);

            // Initialize group states
            const states: Record<number, GroupState> = {};
            json.groups.forEach((g, idx) => {
                states[idx] = {
                    canonical: g.resolved_to || g.main,
                    excluded: new Set<string>(),
                    saved: g.has_rules,
                };
            });
            setGroupStates(states);
        } catch (error) {
            console.error(error);
            alert("Error fetching authority data");
        } finally {
            setLoading(false);
        }
    }

    function updateCanonical(idx: number, value: string) {
        setGroupStates((prev) => ({
            ...prev,
            [idx]: { ...prev[idx], canonical: value, saved: false },
        }));
    }

    function toggleExclude(idx: number, variation: string) {
        setGroupStates((prev) => {
            const excluded = new Set(prev[idx].excluded);
            if (excluded.has(variation)) {
                excluded.delete(variation);
            } else {
                excluded.add(variation);
            }
            return { ...prev, [idx]: { ...prev[idx], excluded, saved: false } };
        });
    }

    async function saveGroupRules(idx: number) {
        if (!data) return;
        const group = data.groups[idx];
        const state = groupStates[idx];
        const activeVariations = group.variations.filter((v) => !state.excluded.has(v));

        setSavingGroup(idx);
        try {
            const res = await fetch("http://localhost:8000/rules/bulk", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    field_name: field,
                    canonical_value: state.canonical,
                    variations: activeVariations,
                }),
            });
            if (!res.ok) throw new Error("Failed to save rules");
            setGroupStates((prev) => ({
                ...prev,
                [idx]: { ...prev[idx], saved: true },
            }));
        } catch (error) {
            console.error(error);
            alert("Error saving rules");
        } finally {
            setSavingGroup(null);
        }
    }

    async function applyAllRules() {
        setApplying(true);
        setApplyResult(null);
        try {
            const res = await fetch(`http://localhost:8000/rules/apply?field_name=${field}`, {
                method: "POST",
            });
            if (!res.ok) throw new Error("Failed to apply rules");
            const json: ApplyResult = await res.json();
            setApplyResult(json);
        } catch (error) {
            console.error(error);
            alert("Error applying rules");
        } finally {
            setApplying(false);
        }
    }

    const savedCount = Object.values(groupStates).filter((s) => s.saved).length;

    return (
        <div className="space-y-6">
            {/* Controls */}
            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                <div className="flex flex-wrap items-end gap-4">
                    <div className="min-w-[200px] flex-1">
                        <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Field to Normalize
                        </label>
                        <select
                            value={field}
                            onChange={(e) => setField(e.target.value)}
                            className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                        >
                            {Object.entries(fieldLabels).map(([val, label]) => (
                                <option key={val} value={val}>{label}</option>
                            ))}
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
                                Analyzing...
                            </>
                        ) : (
                            <>
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                Analyze
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Stats summary */}
            {data && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Variation Groups</p>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{data.total_groups}</p>
                    </div>
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Existing Rules</p>
                        <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{data.total_rules}</p>
                    </div>
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Pending Review</p>
                        <p className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">{data.pending_groups}</p>
                    </div>
                </div>
            )}

            {/* Groups list */}
            {data && (
                <div className="space-y-4">
                    {data.groups.map((group, idx) => {
                        const state = groupStates[idx];
                        if (!state) return null;

                        return (
                            <div
                                key={idx}
                                className={`rounded-2xl border bg-white p-5 transition-shadow hover:shadow-md dark:bg-gray-900 ${
                                    state.saved
                                        ? "border-green-200 dark:border-green-800"
                                        : "border-gray-200 dark:border-gray-800"
                                }`}
                            >
                                {/* Group header */}
                                <div className="mb-4 flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                            state.saved
                                                ? "bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400"
                                                : "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400"
                                        }`}>
                                            {state.saved ? "Resolved" : "Pending"}
                                        </span>
                                        <span className="text-xs text-gray-400 dark:text-gray-500">
                                            {group.count} variations
                                        </span>
                                    </div>
                                    <button
                                        onClick={() => saveGroupRules(idx)}
                                        disabled={savingGroup === idx}
                                        className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        {savingGroup === idx ? (
                                            <>
                                                <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                                </svg>
                                                Saving...
                                            </>
                                        ) : (
                                            <>
                                                <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                </svg>
                                                Save Rules
                                            </>
                                        )}
                                    </button>
                                </div>

                                {/* Canonical value input */}
                                <div className="mb-3">
                                    <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                                        Canonical Value
                                    </label>
                                    <input
                                        type="text"
                                        value={state.canonical}
                                        onChange={(e) => updateCanonical(idx, e.target.value)}
                                        className="h-9 w-full max-w-md rounded-lg border border-gray-200 bg-white px-3 text-sm font-semibold text-gray-900 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                                    />
                                </div>

                                {/* Variations */}
                                <div>
                                    <label className="mb-1.5 block text-xs font-medium text-gray-500 dark:text-gray-400">
                                        Variations (click to exclude)
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {group.variations.map((v, i) => {
                                            const isExcluded = state.excluded.has(v);
                                            const isCanonical = v === state.canonical;
                                            return (
                                                <button
                                                    key={i}
                                                    onClick={() => {
                                                        if (!isCanonical) toggleExclude(idx, v);
                                                    }}
                                                    className={`inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-sm transition-colors ${
                                                        isCanonical
                                                            ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-500/10 dark:text-blue-400"
                                                            : isExcluded
                                                              ? "border-gray-200 bg-gray-50 text-gray-300 line-through dark:border-gray-800 dark:bg-gray-800/50 dark:text-gray-600"
                                                              : "border-gray-200 bg-gray-50 text-gray-700 hover:border-red-300 hover:bg-red-50 hover:text-red-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:border-red-700 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                                                    }`}
                                                    title={isCanonical ? "Canonical value" : isExcluded ? "Click to include" : "Click to exclude"}
                                                >
                                                    {v}
                                                    {isCanonical && (
                                                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                        </svg>
                                                    )}
                                                    {isExcluded && (
                                                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                                        </svg>
                                                    )}
                                                </button>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        );
                    })}

                    {data.groups.length === 0 && (
                        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-16 dark:border-gray-700">
                            <svg className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No variation groups found</p>
                            <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">The data for this field appears to be consistent</p>
                        </div>
                    )}
                </div>
            )}

            {/* Empty state */}
            {!data && !loading && (
                <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-16 dark:border-gray-700">
                    <svg className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                    </svg>
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Authority Control Dictionary</p>
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Select a field and click Analyze to find data inconsistencies</p>
                </div>
            )}

            {/* Apply rules bar */}
            {data && data.total_groups > 0 && (
                <div className="sticky bottom-0 rounded-2xl border border-gray-200 bg-white p-4 shadow-lg dark:border-gray-800 dark:bg-gray-900">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm font-medium text-gray-900 dark:text-white">
                                {savedCount} of {data.total_groups} groups resolved
                            </p>
                            {applyResult && (
                                <p className="text-xs text-green-600 dark:text-green-400">
                                    Applied {applyResult.rules_applied} rules, updated {applyResult.records_updated} records
                                </p>
                            )}
                        </div>
                        <button
                            onClick={applyAllRules}
                            disabled={applying || savedCount === 0}
                            className="inline-flex h-10 items-center gap-2 rounded-lg bg-green-600 px-5 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            {applying ? (
                                <>
                                    <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                    </svg>
                                    Applying...
                                </>
                            ) : (
                                <>
                                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                    </svg>
                                    Apply All Rules to Database
                                </>
                            )}
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
