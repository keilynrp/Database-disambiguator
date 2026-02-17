"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface ProductType {
    name: string;
    count: number;
}

export default function ProductTypesPage() {
    const [types, setTypes] = useState<ProductType[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");

    useEffect(() => {
        async function fetchTypes() {
            try {
                const res = await fetch("http://localhost:8000/product-types");
                if (!res.ok) throw new Error("Failed to fetch product types");
                const data = await res.json();
                setTypes(data);
            } catch (error) {
                console.error("Error fetching product types:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchTypes();
    }, []);

    const filteredTypes = types.filter((type) =>
        type.name.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="space-y-6 p-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 dark:text-white">All Product Types</h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        {types.length} distinct product classifications found
                    </p>
                </div>
                <Link
                    href="/analytics"
                    className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    Back to Analytics
                </Link>
            </div>

            {/* Search */}
            <div className="relative max-w-md">
                <svg
                    className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                    type="text"
                    placeholder="Search product types..."
                    className="h-10 w-full rounded-lg border border-gray-200 bg-white pl-10 pr-4 text-sm outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            {loading ? (
                <div className="flex h-64 items-center justify-center">
                    <svg className="h-8 w-8 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                </div>
            ) : filteredTypes.length === 0 ? (
                <div className="rounded-xl border border-gray-200 bg-white p-12 text-center dark:border-gray-800 dark:bg-gray-900">
                    <p className="text-gray-500 dark:text-gray-400">No product types found matching "{search}"</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {filteredTypes.map((type) => (
                        <div
                            key={type.name}
                            className="group flex flex-col justify-between rounded-xl border border-gray-200 bg-white p-4 transition-all hover:border-blue-200 hover:shadow-md dark:border-gray-800 dark:bg-gray-900 dark:hover:border-blue-500/20"
                        >
                            <div className="flex items-start justify-between">
                                <span className="font-medium text-gray-900 dark:text-white truncate" title={type.name}>
                                    {type.name}
                                </span>
                                <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-blue-50 text-[10px] font-bold text-blue-600 dark:bg-blue-500/10 dark:text-blue-400">
                                    {/* Icon or char? Using first letter */}
                                    {type.name.charAt(0).toUpperCase()}
                                </span>
                            </div>
                            <div className="mt-4 flex items-center justify-between">
                                <span className="text-xs text-gray-500 dark:text-gray-400">Total Products</span>
                                <span className="text-sm font-semibold text-gray-900 dark:text-white">
                                    {type.count.toLocaleString()}
                                </span>
                            </div>
                            <div className="mt-2 h-1.5 w-full rounded-full bg-gray-100 dark:bg-gray-800">
                                <div
                                    className="h-1.5 rounded-full bg-blue-500"
                                    style={{
                                        width: `${Math.min((type.count / types[0].count) * 100, 100)}%`, // Normalize relative to max
                                    }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
