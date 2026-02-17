"use client";

import { useState } from "react";
import ProductTable from "./components/ProductTable";
import ProductVariantView from "./components/ProductVariantView";
import { useSidebar } from "./components/SidebarProvider";

export default function Home() {
  const [viewMode, setViewMode] = useState<"table" | "variants">("table");
  const { collapsed } = useSidebar();

  return (
    <main className="min-h-screen bg-zinc-50 dark:bg-black p-8">
      <div className="space-y-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-zinc-900 dark:text-white">
              Database Disambiguator
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Product catalog and harmonization tools
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* View toggle */}
            <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 p-1 bg-white dark:bg-gray-900">
              <button
                onClick={() => setViewMode("table")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${viewMode === "table"
                  ? "bg-blue-600 text-white"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
              >
                Table View
              </button>
              <button
                onClick={() => setViewMode("variants")}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${viewMode === "variants"
                  ? "bg-blue-600 text-white"
                  : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
              >
                Variant Groups
              </button>
            </div>
            <a href="/disambiguation" className="text-blue-600 hover:underline text-sm font-medium">
              Go to Disambiguation Tool →
            </a>
          </div>
        </div>

        {viewMode === "table" ? <ProductTable /> : <ProductVariantView />}
      </div>
    </main>
  );
}
