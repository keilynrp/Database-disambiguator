"use client";

import { useState, useEffect } from "react";

interface Variant {
    id: number;
    product_name: string;
    brand_capitalized: string;
    model: string;
    sku: string;
    variant: string;
    classification: string;
    product_type: string;
    validation_status: string;
}

interface ProductGroup {
    product_name: string;
    variant_count: number;
    variants: Variant[];
}

export default function ProductVariantView() {
    const [productGroups, setProductGroups] = useState<ProductGroup[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [page, setPage] = useState(0);
    const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
    const [limit, setLimit] = useState(20);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedSearch(search);
            setPage(0);
        }, 500);
        return () => clearTimeout(handler);
    }, [search]);

    useEffect(() => {
        async function fetchProducts() {
            setLoading(true);
            try {
                const queryParams = new URLSearchParams({
                    skip: (page * limit).toString(),
                    limit: limit.toString(),
                });
                if (debouncedSearch) {
                    queryParams.append("search", debouncedSearch);
                }

                const res = await fetch(`http://localhost:8000/products/grouped?${queryParams}`);
                if (!res.ok) throw new Error("Failed to fetch products");
                const data = await res.json();
                setProductGroups(data);
            } catch (error) {
                console.error("Error fetching products:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchProducts();
    }, [debouncedSearch, page, limit]);

    const toggleGroup = (productName: string) => {
        setExpandedGroups(prev => {
            const newSet = new Set(prev);
            if (newSet.has(productName)) {
                newSet.delete(productName);
            } else {
                newSet.add(productName);
            }
            return newSet;
        });
    };

    return (
        <div className="w-full max-w-7xl mx-auto p-4">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold dark:text-white">Product Catalog - Variant View</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Products grouped by name showing all variants</p>
                </div>
                <input
                    type="text"
                    placeholder="Search products..."
                    className="p-2 border rounded w-64 dark:bg-zinc-800 dark:text-white dark:border-zinc-700"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
            </div>

            <div className="overflow-x-auto shadow-md sm:rounded-lg">
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                    {loading ? (
                        <div className="py-12 text-center">
                            <svg className="h-8 w-8 animate-spin mx-auto text-blue-600" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                        </div>
                    ) : productGroups.length === 0 ? (
                        <div className="py-12 text-center text-gray-500 dark:text-gray-400">
                            No products found
                        </div>
                    ) : (
                        productGroups.map((group) => {
                            const isExpanded = expandedGroups.has(group.product_name);
                            return (
                                <div key={group.product_name} className="bg-white dark:bg-zinc-800">
                                    {/* Group header */}
                                    <div
                                        className="px-6 py-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-zinc-700 transition-colors"
                                        onClick={() => toggleGroup(group.product_name)}
                                    >
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3 flex-1">
                                                <svg
                                                    className={`h-5 w-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                                                    fill="none"
                                                    stroke="currentColor"
                                                    viewBox="0 0 24 24"
                                                >
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                                </svg>
                                                <span className="font-medium text-gray-900 dark:text-white">
                                                    {group.product_name}
                                                </span>
                                            </div>
                                            <span className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                                                {group.variant_count} {group.variant_count === 1 ? 'variant' : 'variants'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Variants table */}
                                    {isExpanded && (
                                        <div className="border-t border-gray-200 dark:border-gray-700 table-container">
                                            <table className="w-full min-w-[1000px] text-sm text-left">
                                                <thead className="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-zinc-900 dark:text-gray-400">
                                                    <tr>
                                                        <th className="px-6 py-3">ID</th>
                                                        <th className="px-6 py-3">Variant</th>
                                                        <th className="px-6 py-3">Brand</th>
                                                        <th className="px-6 py-3">Model</th>
                                                        <th className="px-6 py-3">SKU</th>
                                                        <th className="px-6 py-3">Classification</th>
                                                        <th className="px-6 py-3">Type</th>
                                                        <th className="px-6 py-3">Status</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                                                    {group.variants.map((variant) => (
                                                        <tr key={variant.id} className="bg-white dark:bg-zinc-800 hover:bg-gray-50 dark:hover:bg-zinc-700">
                                                            <td className="px-6 py-3 text-gray-500 dark:text-gray-400">{variant.id}</td>
                                                            <td className="px-6 py-3 font-medium text-gray-900 dark:text-white">
                                                                {variant.variant || '-'}
                                                            </td>
                                                            <td className="px-6 py-3 text-gray-700 dark:text-gray-300">{variant.brand_capitalized || '-'}</td>
                                                            <td className="px-6 py-3 text-gray-700 dark:text-gray-300">{variant.model || '-'}</td>
                                                            <td className="px-6 py-3 text-gray-700 dark:text-gray-300">{variant.sku || '-'}</td>
                                                            <td className="px-6 py-3 text-gray-700 dark:text-gray-300">{variant.classification || '-'}</td>
                                                            <td className="px-6 py-3 text-gray-700 dark:text-gray-300">{variant.product_type || '-'}</td>
                                                            <td className="px-6 py-3">
                                                                <span className={`px-2 py-1 rounded text-xs ${variant.validation_status === 'valid' ? 'bg-green-100 text-green-800 dark:bg-green-500/10 dark:text-green-400' :
                                                                    variant.validation_status === 'invalid' ? 'bg-red-100 text-red-800 dark:bg-red-500/10 dark:text-red-400' :
                                                                        'bg-yellow-100 text-yellow-800 dark:bg-yellow-500/10 dark:text-yellow-400'
                                                                    }`}>
                                                                    {variant.validation_status}
                                                                </span>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </div>

            <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500 dark:text-gray-400">Rows per page:</span>
                    <select
                        value={limit}
                        onChange={(e) => {
                            setLimit(Number(e.target.value));
                            setPage(0);
                        }}
                        className="rounded-lg border border-gray-200 bg-white px-2 py-1 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
                    >
                        <option value={10}>10</option>
                        <option value={20}>20</option>
                        <option value={50}>50</option>
                        <option value={100}>100</option>
                    </select>
                </div>

                <div className="flex items-center gap-4">
                    <button
                        onClick={() => setPage(p => Math.max(0, p - 1))}
                        disabled={page === 0 || loading}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3.5 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                    >
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                        Previous
                    </button>
                    <div className="flex items-center gap-2">
                        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-medium text-white">
                            {page + 1}
                        </span>
                    </div>
                    <button
                        onClick={() => setPage(p => p + 1)}
                        disabled={productGroups.length < limit || loading}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3.5 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
                    >
                        Next
                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    );
}
