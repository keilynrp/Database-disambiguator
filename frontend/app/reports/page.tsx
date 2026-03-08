"use client";

import { useState, useEffect, useCallback } from "react";
import { PageHeader, Badge } from "../components/ui";
import { apiFetch } from "../../lib/api";
import { useDomain } from "../contexts/DomainContext";
import { useToast } from "../components/ui";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Section {
  id: string;
  label: string;
}

const SECTION_ICONS: Record<string, string> = {
  entity_stats:         "📊",
  enrichment_coverage:  "🔬",
  top_brands:           "🏷️",
  topic_clusters:       "🧩",
  harmonization_log:    "⚙️",
};

const SECTION_DESCRIPTIONS: Record<string, string> = {
  entity_stats:         "Total entities, validation status breakdown, distribution chart",
  enrichment_coverage:  "Coverage %, average citations, top enriched entities",
  top_brands:           "Top 15 brands or classifications by entity count",
  topic_clusters:       "Most frequent concepts from enrichment data",
  harmonization_log:    "Last 10 harmonization steps with status",
};

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const { activeDomainId } = useDomain();
  const { toast } = useToast();

  const [sections, setSections] = useState<Section[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [title, setTitle] = useState("");
  const [generating, setGenerating] = useState(false);
  const [loadingSections, setLoadingSections] = useState(true);

  // Fetch available sections from backend
  const loadSections = useCallback(async () => {
    try {
      const res = await apiFetch("/reports/sections");
      if (res.ok) {
        const data: Section[] = await res.json();
        setSections(data);
        setSelected(new Set(data.map((s) => s.id)));
      }
    } finally {
      setLoadingSections(false);
    }
  }, []);

  useEffect(() => { loadSections(); }, [loadSections]);

  const toggleSection = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const selectAll = () => setSelected(new Set(sections.map((s) => s.id)));
  const clearAll  = () => setSelected(new Set());

  const handleGenerate = async () => {
    if (selected.size === 0) {
      toast("Select at least one section", "warning");
      return;
    }
    setGenerating(true);
    try {
      const res = await apiFetch("/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          domain_id: activeDomainId || "default",
          sections: Array.from(selected),
          title: title.trim() || null,
        }),
      });
      if (!res.ok) {
        const err = await res.text();
        toast(`Generation failed: ${err}`, "error");
        return;
      }
      // Download the HTML file
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      const cd   = res.headers.get("Content-Disposition") ?? "";
      const match = cd.match(/filename="([^"]+)"/);
      a.href     = url;
      a.download = match ? match[1] : "ukip_report.html";
      a.click();
      URL.revokeObjectURL(url);
      toast("Report downloaded", "success");
    } catch {
      toast("Failed to generate report", "error");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Analytics", href: "/analytics" },
          { label: "Report Builder" },
        ]}
        title="Report Builder"
        description="Generate self-contained HTML reports — printable and shareable"
        actions={
          <button
            onClick={handleGenerate}
            disabled={generating || selected.size === 0}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {generating ? (
              <>
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating…
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
                Generate & Download
              </>
            )}
          </button>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
        {/* Section picker */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
              Report Sections
              <span className="ml-2 text-xs font-normal text-gray-400">
                {selected.size} of {sections.length} selected
              </span>
            </h2>
            <div className="flex gap-2">
              <button onClick={selectAll} className="text-xs text-blue-600 hover:underline dark:text-blue-400">All</button>
              <span className="text-gray-300 dark:text-gray-700">·</span>
              <button onClick={clearAll} className="text-xs text-gray-500 hover:underline dark:text-gray-400">None</button>
            </div>
          </div>

          {loadingSections ? (
            <div className="flex justify-center py-16">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {sections.map((sec) => {
                const isOn = selected.has(sec.id);
                return (
                  <button
                    key={sec.id}
                    onClick={() => toggleSection(sec.id)}
                    className={`group flex items-start gap-4 rounded-2xl border p-5 text-left transition-all ${
                      isOn
                        ? "border-blue-300 bg-blue-50 dark:border-blue-500/40 dark:bg-blue-500/10"
                        : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-900 dark:hover:border-gray-600"
                    }`}
                  >
                    {/* Checkbox */}
                    <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 transition-colors ${
                      isOn
                        ? "border-blue-600 bg-blue-600"
                        : "border-gray-300 bg-white dark:border-gray-600 dark:bg-gray-800"
                    }`}>
                      {isOn && (
                        <svg className="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-base">{SECTION_ICONS[sec.id] ?? "📋"}</span>
                        <span className={`text-sm font-medium ${isOn ? "text-blue-700 dark:text-blue-300" : "text-gray-900 dark:text-white"}`}>
                          {sec.label}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {SECTION_DESCRIPTIONS[sec.id] ?? ""}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Configuration panel */}
        <div className="space-y-4">
          {/* Report title */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Configuration</h3>
            <div className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-600 dark:text-gray-400">
                  Report Title (optional)
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={`UKIP Report — ${activeDomainId || "default"}`}
                  className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-gray-600 dark:text-gray-400">
                  Active Domain
                </label>
                <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
                  <span className="text-sm text-gray-700 dark:text-gray-300">{activeDomainId || "default"}</span>
                  <Badge variant="info" size="sm">active</Badge>
                </div>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">Change domain in the header selector</p>
              </div>
            </div>
          </div>

          {/* Preview of what's included */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-900">
            <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Included Sections</h3>
            {selected.size === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500">No sections selected</p>
            ) : (
              <ol className="space-y-2">
                {sections
                  .filter((s) => selected.has(s.id))
                  .map((s, i) => (
                    <li key={s.id} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-600 dark:bg-blue-500/20 dark:text-blue-400">
                        {i + 1}
                      </span>
                      {SECTION_ICONS[s.id]} {s.label}
                    </li>
                  ))}
              </ol>
            )}
          </div>

          {/* Format info */}
          <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-500/20 dark:bg-amber-500/5">
            <div className="flex items-start gap-3">
              <svg className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
              </svg>
              <div>
                <p className="text-xs font-medium text-amber-800 dark:text-amber-300">HTML format</p>
                <p className="mt-0.5 text-xs text-amber-700 dark:text-amber-400">
                  Open in browser and use <kbd className="rounded bg-amber-100 px-1 font-mono dark:bg-amber-900/40">Ctrl+P</kbd> to print or export as PDF.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
