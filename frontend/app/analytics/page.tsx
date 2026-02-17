"use client";

import { useState, useEffect } from "react";
import MetricCard from "../components/MetricCard";

interface Stats {
    total_products: number;
    unique_brands: number;
    unique_models: number;
    unique_product_types: number;
    products_with_variants: number;
    unique_products_with_variants: number;
    validation_status: Record<string, number>;
    identifier_coverage: {
        with_sku: number;
        with_barcode: number;
        with_gtin: number;
        total: number;
    };
    top_brands: { name: string; count: number }[];
    type_distribution: { name: string; count: number }[];
    status_distribution: { name: string; count: number }[];
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
    const pct = max > 0 ? (value / max) * 100 : 0;
    return (
        <div className="h-2 w-full rounded-full bg-gray-100 dark:bg-gray-800">
            <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
        </div>
    );
}

export default function AnalyticsPage() {
    const [stats, setStats] = useState<Stats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchStats() {
            try {
                const res = await fetch("http://localhost:8000/stats");
                if (!res.ok) throw new Error("Failed to fetch stats");
                const data = await res.json();
                setStats(data);
            } catch (error) {
                console.error("Error fetching stats:", error);
            } finally {
                setLoading(false);
            }
        }
        fetchStats();
    }, []);

    if (loading) {
        return (
            <div className="flex h-64 items-center justify-center">
                <svg className="h-8 w-8 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
            </div>
        );
    }

    if (!stats) {
        return (
            <div className="flex h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-gray-300 dark:border-gray-700">
                <svg className="mb-3 h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Could not load analytics data</p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Make sure the backend is running on port 8000</p>
            </div>
        );
    }

    const validCount = stats.validation_status["valid"] || 0;
    const invalidCount = stats.validation_status["invalid"] || 0;
    const pendingCount = stats.validation_status["pending"] || 0;
    const validPct = stats.total_products > 0 ? ((validCount / stats.total_products) * 100).toFixed(1) : "0";
    const skuPct = stats.total_products > 0 ? ((stats.identifier_coverage.with_sku / stats.total_products) * 100).toFixed(1) : "0";

    return (
        <div className="space-y-6">
            {/* Metric cards grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-5">
                <MetricCard
                    label="Total Products"
                    value={stats.total_products.toLocaleString()}
                    icon={
                        <svg className="h-5 w-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                        </svg>
                    }
                    subtitle="Records in database"
                />
                <MetricCard
                    label="Unique Brands"
                    value={stats.unique_brands.toLocaleString()}
                    icon={
                        <svg className="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                    }
                    subtitle="Distinct brand names"
                />
                <MetricCard
                    label="Product Types"
                    value={stats.unique_product_types.toLocaleString()}
                    icon={
                        <svg className="h-5 w-5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    }
                    subtitle="Category classifications"
                />
                <MetricCard
                    label="Validated"
                    value={`${validPct}%`}
                    icon={
                        <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    }
                    trend={Number(validPct) >= 50 ? { value: `${validCount} records`, positive: true } : { value: `${pendingCount} pending`, positive: false }}
                    subtitle={`${validCount} valid of ${stats.total_products}`}
                />
                <MetricCard
                    label="Product Variants"
                    value={stats.unique_products_with_variants.toLocaleString()}
                    icon={
                        <svg className="h-5 w-5 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                    }
                    trend={{ value: `${stats.products_with_variants} variant entries`, positive: true }}
                    subtitle="Products with multiple variants"
                />
            </div>

            {/* Two-column layout */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-12">
                {/* Validation status card */}
                <div className="xl:col-span-5">
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Validation Status</h3>
                        <p className="mb-5 text-xs text-gray-500 dark:text-gray-400">Product data quality overview</p>

                        <div className="space-y-4">
                            {/* Valid */}
                            <div>
                                <div className="mb-1.5 flex items-center justify-between text-sm">
                                    <div className="flex items-center gap-2">
                                        <span className="h-2.5 w-2.5 rounded-full bg-green-500" />
                                        <span className="text-gray-700 dark:text-gray-300">Valid</span>
                                    </div>
                                    <span className="font-medium text-gray-900 dark:text-white">{validCount.toLocaleString()}</span>
                                </div>
                                <ProgressBar value={validCount} max={stats.total_products} color="bg-green-500" />
                            </div>
                            {/* Pending */}
                            <div>
                                <div className="mb-1.5 flex items-center justify-between text-sm">
                                    <div className="flex items-center gap-2">
                                        <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                                        <span className="text-gray-700 dark:text-gray-300">Pending</span>
                                    </div>
                                    <span className="font-medium text-gray-900 dark:text-white">{pendingCount.toLocaleString()}</span>
                                </div>
                                <ProgressBar value={pendingCount} max={stats.total_products} color="bg-amber-500" />
                            </div>
                            {/* Invalid */}
                            <div>
                                <div className="mb-1.5 flex items-center justify-between text-sm">
                                    <div className="flex items-center gap-2">
                                        <span className="h-2.5 w-2.5 rounded-full bg-red-500" />
                                        <span className="text-gray-700 dark:text-gray-300">Invalid</span>
                                    </div>
                                    <span className="font-medium text-gray-900 dark:text-white">{invalidCount.toLocaleString()}</span>
                                </div>
                                <ProgressBar value={invalidCount} max={stats.total_products} color="bg-red-500" />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Identifier coverage card */}
                <div className="xl:col-span-7">
                    <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Identifier Coverage</h3>
                        <p className="mb-5 text-xs text-gray-500 dark:text-gray-400">How well products are identified across systems</p>

                        <div className="space-y-4">
                            {[
                                { label: "SKU", value: stats.identifier_coverage.with_sku, color: "bg-blue-500" },
                                { label: "Barcode", value: stats.identifier_coverage.with_barcode, color: "bg-purple-500" },
                                { label: "GTIN", value: stats.identifier_coverage.with_gtin, color: "bg-cyan-500" },
                            ].map((item) => {
                                const pct = stats.total_products > 0 ? ((item.value / stats.total_products) * 100).toFixed(1) : "0";
                                return (
                                    <div key={item.label}>
                                        <div className="mb-1.5 flex items-center justify-between text-sm">
                                            <div className="flex items-center gap-2">
                                                <span className={`h-2.5 w-2.5 rounded-full ${item.color}`} />
                                                <span className="text-gray-700 dark:text-gray-300">{item.label}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-gray-400 dark:text-gray-500">{pct}%</span>
                                                <span className="font-medium text-gray-900 dark:text-white">{item.value.toLocaleString()}</span>
                                            </div>
                                        </div>
                                        <ProgressBar value={item.value} max={stats.total_products} color={item.color} />
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom row: Top Brands + Product Types */}
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
                {/* Top brands */}
                <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
                    <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Top Brands</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Most represented brands in database</p>
                    </div>
                    <div className="divide-y divide-gray-100 dark:divide-gray-800">
                        {stats.top_brands.map((brand, idx) => (
                            <div key={brand.name} className="flex items-center justify-between px-5 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                <div className="flex items-center gap-3">
                                    <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gray-100 text-xs font-semibold text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                                        {idx + 1}
                                    </span>
                                    <span className="text-sm font-medium text-gray-900 dark:text-white">{brand.name}</span>
                                </div>
                                <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                                    {brand.count.toLocaleString()}
                                </span>
                            </div>
                        ))}
                        {stats.top_brands.length === 0 && (
                            <div className="px-5 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                                No brand data available
                            </div>
                        )}
                    </div>
                </div>

                {/* Product type distribution */}
                <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
                    <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Product Types</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Distribution by product category</p>
                    </div>
                    <div className="divide-y divide-gray-100 dark:divide-gray-800">
                        {stats.type_distribution.map((type) => {
                            const pct = stats.total_products > 0 ? ((type.count / stats.total_products) * 100).toFixed(1) : "0";
                            return (
                                <div key={type.name} className="px-5 py-3 transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                    <div className="mb-1.5 flex items-center justify-between">
                                        <span className="text-sm font-medium text-gray-900 dark:text-white">{type.name}</span>
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs text-gray-400 dark:text-gray-500">{pct}%</span>
                                            <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                                                {type.count.toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                    <ProgressBar value={type.count} max={stats.total_products} color="bg-blue-500" />
                                </div>
                            );
                        })}
                        {stats.type_distribution.length === 0 && (
                            <div className="px-5 py-8 text-center text-sm text-gray-400 dark:text-gray-500">
                                No product type data available
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Status distribution */}
            {stats.status_distribution.length > 0 && (
                <div className="rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
                    <div className="border-b border-gray-200 px-5 py-4 dark:border-gray-800">
                        <h3 className="text-base font-semibold text-gray-900 dark:text-white">Product Status</h3>
                        <p className="text-xs text-gray-500 dark:text-gray-400">Active vs inactive product records</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-3 lg:grid-cols-4">
                        {stats.status_distribution.map((s) => (
                            <div key={s.name} className="rounded-xl border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-gray-800">
                                <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.count.toLocaleString()}</p>
                                <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{s.name}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
