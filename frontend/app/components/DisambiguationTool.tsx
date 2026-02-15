"use client";

import { useState } from "react";

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
    const [field, setField] = useState("brand_capitalized");
    const [groups, setGroups] = useState<VariationGroup[]>([]);
    const [loading, setLoading] = useState(false);
    const [totalGroups, setTotalGroups] = useState(0);

    async function analyze() {
        setLoading(true);
        try {
            const res = await fetch(`http://localhost:8000/disambiguate/${field}`);
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

    const fieldLabels: Record<string, string> = {
        brand_capitalized: "Brand",
        product_name: "Product Name",
        model: "Model",
    };

    return (
        <div className="space-y-6">
            {/* Controls card */}
            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                <div className="flex flex-wrap items-end gap-4">
                    <div className="flex-1 min-w-[200px]">
                        <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                            Field to Analyze
                        </label>
                        <select
                            value={field}
                            onChange={(e) => setField(e.target.value)}
                            className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm text-gray-700 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                        >
                            <option value="brand_capitalized">Brand</option>
                            <option value="product_name">Product Name</option>
                            <option value="model">Model</option>
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
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                </svg>
                                Analyze
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Results summary */}
            {groups.length > 0 && (
                <div className="flex gap-4">
                    <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Groups Found</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">{totalGroups}</p>
                    </div>
                    <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Field Analyzed</p>
                        <p className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">{fieldLabels[field]}</p>
                    </div>
                    <div className="flex-1 rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <p className="text-sm text-gray-500 dark:text-gray-400">Total Variations</p>
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
                                {group.count} variations
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
                    </div>
                ))}
                {groups.length === 0 && !loading && (
                    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 py-16 dark:border-gray-700">
                        <svg className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                        </svg>
                        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No analysis results yet</p>
                        <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Select a field and click Analyze to find data inconsistencies</p>
                    </div>
                )}
            </div>
        </div>
    );
}
