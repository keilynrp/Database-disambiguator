"use client";

import { usePathname } from "next/navigation";
import { useTheme } from "../contexts/ThemeContext";

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  "/": { title: "Product Catalog", subtitle: "Browse and search your product database" },
  "/disambiguation": { title: "Data Disambiguation", subtitle: "Find and resolve data inconsistencies" },
  "/analytics": { title: "Analytics", subtitle: "Key metrics and data quality insights" },
  "/authority": { title: "Authority Control", subtitle: "Normalize and harmonize field values with canonical rules" },
  "/harmonization": { title: "Data Harmonization", subtitle: "Automated pipeline for cleaning and consolidating product data" },
  "/import-export": { title: "Import / Export", subtitle: "Upload and download product data in Excel format" },
};

export default function Header() {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const page = pageTitles[pathname] || { title: "Dashboard", subtitle: "" };

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center border-b border-gray-200 bg-white/80 backdrop-blur-sm dark:border-gray-800 dark:bg-gray-900/80">
      <div className="flex w-full items-center justify-between px-6">
        <div>
          <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
            {page.title}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {page.subtitle}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="rounded-lg border border-gray-200 p-2 text-gray-500 transition-colors hover:bg-gray-100 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-800"
            title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          {/* User avatar */}
          <div className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-1.5 dark:border-gray-700">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-600 dark:bg-blue-600/20 dark:text-blue-400">
              A
            </div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Admin</span>
          </div>
        </div>
      </div>
    </header>
  );
}

