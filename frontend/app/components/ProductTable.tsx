"use client";

import { useState, useEffect, useCallback } from "react";

interface Product {
    id: number;
    product_name: string;
    brand_capitalized: string;
    model: string;
    sku: string;
    classification: string;
    product_type: string;
    validation_status: string;
}

type EditableFields = Pick<Product, "product_name" | "brand_capitalized" | "model" | "sku" | "product_type" | "validation_status">;

function StatusBadge({ status }: { status: string }) {
    const styles: Record<string, string> = {
        valid: "bg-green-100 text-green-700 dark:bg-green-500/10 dark:text-green-400",
        invalid: "bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-400",
    };
    const fallback = "bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400";

    return (
        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status] || fallback}`}>
            {status}
        </span>
    );
}

export default function ProductTable() {
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState("");
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [page, setPage] = useState(0);
    const limit = 20;

    // Edit state
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editData, setEditData] = useState<EditableFields>({
        product_name: "", brand_capitalized: "", model: "", sku: "", product_type: "", validation_status: "",
    });
    const [saving, setSaving] = useState(false);

    // Delete state
    const [deletingId, setDeletingId] = useState<number | null>(null);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedSearch(search);
            setPage(0);
        }, 500);
        return () => clearTimeout(handler);
    }, [search]);

    const fetchProducts = useCallback(async () => {
        setLoading(true);
        try {
            const queryParams = new URLSearchParams({
                skip: (page * limit).toString(),
                limit: limit.toString(),
            });
            if (debouncedSearch) queryParams.append("search", debouncedSearch);

            const res = await fetch(`http://localhost:8000/products?${queryParams}`);
            if (!res.ok) throw new Error("Failed to fetch products");
            setProducts(await res.json());
        } catch (error) {
            console.error("Error fetching products:", error);
        } finally {
            setLoading(false);
        }
    }, [debouncedSearch, page]);

    useEffect(() => { fetchProducts(); }, [fetchProducts]);

    function startEdit(product: Product) {
        setEditingId(product.id);
        setEditData({
            product_name: product.product_name || "",
            brand_capitalized: product.brand_capitalized || "",
            model: product.model || "",
            sku: product.sku || "",
            product_type: product.product_type || "",
            validation_status: product.validation_status || "pending",
        });
    }

    function cancelEdit() {
        setEditingId(null);
    }

    async function saveEdit() {
        if (!editingId) return;
        setSaving(true);
        try {
            const res = await fetch(`http://localhost:8000/products/${editingId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(editData),
            });
            if (!res.ok) throw new Error("Failed to update");
            const updated = await res.json();
            setProducts((prev) => prev.map((p) => (p.id === editingId ? updated : p)));
            setEditingId(null);
        } catch (error) {
            console.error(error);
            alert("Error updating product");
        } finally {
            setSaving(false);
        }
    }

    async function deleteProduct(id: number) {
        setDeletingId(id);
        try {
            const res = await fetch(`http://localhost:8000/products/${id}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete");
            setProducts((prev) => prev.filter((p) => p.id !== id));
        } catch (error) {
            console.error(error);
            alert("Error deleting product");
        } finally {
            setDeletingId(null);
        }
    }

    const thClass = "px-5 py-3.5 text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400";
    const inputClass = "h-8 w-full rounded border border-gray-200 bg-white px-2 text-sm text-gray-900 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-white";

    return (
        <div className="space-y-6">
            {/* Search bar */}
            <div className="flex items-center justify-between">
                <div className="relative">
                    <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                        type="text"
                        placeholder="Search products, brands, models..."
                        className="h-10 w-80 rounded-lg border border-gray-200 bg-white pl-10 pr-4 text-sm text-gray-700 placeholder-gray-400 outline-none transition-colors focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:placeholder-gray-500 dark:focus:border-blue-500"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                    Page {page + 1}
                </span>
            </div>

            {/* Table card */}
            <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="border-b border-gray-200 dark:border-gray-800">
                                <th className={thClass}>ID</th>
                                <th className={thClass}>Product Name</th>
                                <th className={thClass}>Brand</th>
                                <th className={thClass}>Model</th>
                                <th className={thClass}>SKU</th>
                                <th className={thClass}>Type</th>
                                <th className={thClass}>Status</th>
                                <th className={`${thClass} text-right`}>Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                            {loading ? (
                                <tr>
                                    <td colSpan={8} className="px-5 py-12 text-center">
                                        <div className="flex flex-col items-center gap-2">
                                            <svg className="h-6 w-6 animate-spin text-blue-600" fill="none" viewBox="0 0 24 24">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                            <span className="text-sm text-gray-500 dark:text-gray-400">Loading products...</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : products.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="px-5 py-12 text-center">
                                        <div className="flex flex-col items-center gap-2">
                                            <svg className="h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                                            </svg>
                                            <span className="text-sm text-gray-500 dark:text-gray-400">No products found</span>
                                        </div>
                                    </td>
                                </tr>
                            ) : (
                                products.map((product) => {
                                    const isEditing = editingId === product.id;

                                    if (isEditing) {
                                        return (
                                            <tr key={product.id} className="bg-blue-50/50 dark:bg-blue-500/5">
                                                <td className="px-5 py-2.5 text-gray-500 dark:text-gray-400">{product.id}</td>
                                                <td className="px-5 py-2.5">
                                                    <input className={inputClass} value={editData.product_name} onChange={(e) => setEditData({ ...editData, product_name: e.target.value })} />
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <input className={inputClass} value={editData.brand_capitalized} onChange={(e) => setEditData({ ...editData, brand_capitalized: e.target.value })} />
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <input className={inputClass} value={editData.model} onChange={(e) => setEditData({ ...editData, model: e.target.value })} />
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <input className={inputClass} value={editData.sku} onChange={(e) => setEditData({ ...editData, sku: e.target.value })} />
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <input className={inputClass} value={editData.product_type} onChange={(e) => setEditData({ ...editData, product_type: e.target.value })} />
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <select
                                                        className={inputClass}
                                                        value={editData.validation_status}
                                                        onChange={(e) => setEditData({ ...editData, validation_status: e.target.value })}
                                                    >
                                                        <option value="pending">pending</option>
                                                        <option value="valid">valid</option>
                                                        <option value="invalid">invalid</option>
                                                    </select>
                                                </td>
                                                <td className="px-5 py-2.5">
                                                    <div className="flex items-center justify-end gap-1">
                                                        <button
                                                            onClick={saveEdit}
                                                            disabled={saving}
                                                            className="rounded-lg p-1.5 text-green-600 hover:bg-green-100 disabled:opacity-50 dark:text-green-400 dark:hover:bg-green-500/10"
                                                            title="Save"
                                                        >
                                                            {saving ? (
                                                                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                                                </svg>
                                                            ) : (
                                                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                                </svg>
                                                            )}
                                                        </button>
                                                        <button
                                                            onClick={cancelEdit}
                                                            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                                                            title="Cancel"
                                                        >
                                                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                            </svg>
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    }

                                    return (
                                        <tr key={product.id} className="group transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/50">
                                            <td className="px-5 py-3.5 text-gray-500 dark:text-gray-400">{product.id}</td>
                                            <td className="px-5 py-3.5 font-medium text-gray-900 dark:text-white">
                                                {product.product_name}
                                            </td>
                                            <td className="px-5 py-3.5 text-gray-600 dark:text-gray-300">{product.brand_capitalized || "—"}</td>
                                            <td className="px-5 py-3.5 text-gray-600 dark:text-gray-300">{product.model || "—"}</td>
                                            <td className="px-5 py-3.5">
                                                {product.sku ? (
                                                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                                                        {product.sku}
                                                    </code>
                                                ) : "—"}
                                            </td>
                                            <td className="px-5 py-3.5 text-gray-600 dark:text-gray-300">{product.product_type}</td>
                                            <td className="px-5 py-3.5">
                                                <StatusBadge status={product.validation_status} />
                                            </td>
                                            <td className="px-5 py-3.5">
                                                <div className="flex items-center justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                                                    <button
                                                        onClick={() => startEdit(product)}
                                                        className="rounded-lg p-1.5 text-gray-400 hover:bg-blue-100 hover:text-blue-600 dark:hover:bg-blue-500/10 dark:hover:text-blue-400"
                                                        title="Edit"
                                                    >
                                                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
                                                        </svg>
                                                    </button>
                                                    <button
                                                        onClick={() => {
                                                            if (confirm(`Delete product #${product.id} "${product.product_name}"?`)) {
                                                                deleteProduct(product.id);
                                                            }
                                                        }}
                                                        disabled={deletingId === product.id}
                                                        className="rounded-lg p-1.5 text-gray-400 hover:bg-red-100 hover:text-red-600 disabled:opacity-50 dark:hover:bg-red-500/10 dark:hover:text-red-400"
                                                        title="Delete"
                                                    >
                                                        {deletingId === product.id ? (
                                                            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                                            </svg>
                                                        ) : (
                                                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                                                            </svg>
                                                        )}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between border-t border-gray-200 px-5 py-3.5 dark:border-gray-800">
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
                        disabled={products.length < limit || loading}
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
