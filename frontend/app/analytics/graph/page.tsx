"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { PageHeader, StatCard } from "../../components/ui";

interface GraphStats {
  total_nodes: number;
  total_edges: number;
  total_components: number;
  largest_component_size: number;
  top_pagerank: Array<{ entity_id: number; primary_label: string | null; score: number }>;
  top_degree:   Array<{ entity_id: number; primary_label: string | null; total_degree: number }>;
}

interface PathResult {
  found: boolean;
  length?: number;
  relations?: string[];
  steps?: Array<{ entity_id: number; primary_label: string | null }>;
}

export default function GraphAnalyticsPage() {
  const [stats, setStats] = useState<GraphStats | null>(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [errorStats, setErrorStats] = useState<string | null>(null);

  // Path finder state
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [pathResult, setPathResult] = useState<PathResult | null>(null);
  const [loadingPath, setLoadingPath] = useState(false);
  const [pathError, setPathError] = useState<string | null>(null);

  useEffect(() => {
    setLoadingStats(true);
    apiFetch("/graph/stats")
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data) => setStats(data))
      .catch((e) => setErrorStats(`Failed to load graph stats (${e})`))
      .finally(() => setLoadingStats(false));
  }, []);

  async function findPath() {
    if (!fromId || !toId) return;
    setLoadingPath(true);
    setPathResult(null);
    setPathError(null);
    try {
      const r = await apiFetch(`/graph/path?from_id=${fromId}&to_id=${toId}`);
      if (r.ok) {
        setPathResult(await r.json());
      } else {
        const body = await r.json().catch(() => ({}));
        setPathError(body.detail ?? `Error ${r.status}`);
      }
    } catch {
      setPathError("Network error");
    } finally {
      setLoadingPath(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <PageHeader
          title="Graph Analytics"
          subtitle="Centrality scores, connected components, and shortest paths across the knowledge graph."
        />

        {/* Stats cards */}
        {loadingStats ? (
          <div className="flex h-32 items-center justify-center">
            <svg className="h-6 w-6 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          </div>
        ) : errorStats ? (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
            {errorStats}
          </div>
        ) : stats ? (
          <>
            <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard
                label="Total Nodes"
                value={stats.total_nodes.toLocaleString()}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M12 18a6 6 0 100-12 6 6 0 000 12z" />
                  </svg>
                }
              />
              <StatCard
                label="Total Edges"
                value={stats.total_edges.toLocaleString()}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M5 12h14" />
                  </svg>
                }
              />
              <StatCard
                label="Components"
                value={stats.total_components.toLocaleString()}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6z" />
                  </svg>
                }
              />
              <StatCard
                label="Largest Component"
                value={stats.largest_component_size.toLocaleString()}
                icon={
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 002.25-2.25V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v2.25A2.25 2.25 0 006 10.5z" />
                  </svg>
                }
              />
            </div>

            {stats.total_nodes === 0 ? (
              <div className="mt-8 rounded-xl border border-gray-200 bg-white p-12 text-center dark:border-gray-800 dark:bg-gray-900">
                <svg className="mx-auto mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M13.5 16.875h3.375m0 0h3.375m-3.375 0V13.5m0 3.375v3.375M6 10.5h2.25a2.25 2.25 0 002.25-2.25V6a2.25 2.25 0 00-2.25-2.25H6A2.25 2.25 0 003.75 6v2.25A2.25 2.25 0 006 10.5zm0 9.75h2.25A2.25 2.25 0 0010.5 18v-2.25a2.25 2.25 0 00-2.25-2.25H6a2.25 2.25 0 00-2.25 2.25V18A2.25 2.25 0 006 20.25zm9.75-9.75H18a2.25 2.25 0 002.25-2.25V6A2.25 2.25 0 0018 3.75h-2.25A2.25 2.25 0 0013.5 6v2.25a2.25 2.25 0 002.25 2.25z" />
                </svg>
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">No relationships found</p>
                <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">
                  Add relationships to entities to see graph analytics.
                </p>
              </div>
            ) : (
              <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* Top by PageRank */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
                  <h2 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">
                    Top by PageRank
                  </h2>
                  {stats.top_pagerank.length === 0 ? (
                    <p className="text-xs text-gray-400">No data</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100 dark:border-gray-800">
                          <th className="pb-2 text-left text-xs font-medium text-gray-400">#</th>
                          <th className="pb-2 text-left text-xs font-medium text-gray-400">Entity</th>
                          <th className="pb-2 text-right text-xs font-medium text-gray-400">Score</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                        {stats.top_pagerank.map((row, idx) => (
                          <tr key={row.entity_id}>
                            <td className="py-2 text-xs text-gray-400">{idx + 1}</td>
                            <td className="py-2">
                              <Link
                                href={`/entities/${row.entity_id}`}
                                className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                              >
                                {row.primary_label ?? `#${row.entity_id}`}
                              </Link>
                            </td>
                            <td className="py-2 text-right text-xs tabular-nums text-gray-700 dark:text-gray-300">
                              {row.score.toFixed(4)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                {/* Top by Degree */}
                <div className="rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
                  <h2 className="mb-4 text-sm font-semibold text-gray-900 dark:text-white">
                    Top by Degree
                  </h2>
                  {stats.top_degree.length === 0 ? (
                    <p className="text-xs text-gray-400">No data</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100 dark:border-gray-800">
                          <th className="pb-2 text-left text-xs font-medium text-gray-400">#</th>
                          <th className="pb-2 text-left text-xs font-medium text-gray-400">Entity</th>
                          <th className="pb-2 text-right text-xs font-medium text-gray-400">Degree</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50 dark:divide-gray-800/50">
                        {stats.top_degree.map((row, idx) => (
                          <tr key={row.entity_id}>
                            <td className="py-2 text-xs text-gray-400">{idx + 1}</td>
                            <td className="py-2">
                              <Link
                                href={`/entities/${row.entity_id}`}
                                className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                              >
                                {row.primary_label ?? `#${row.entity_id}`}
                              </Link>
                            </td>
                            <td className="py-2 text-right text-xs tabular-nums text-gray-700 dark:text-gray-300">
                              {row.total_degree}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}
          </>
        ) : null}

        {/* Path Finder */}
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
          <h2 className="mb-1 text-sm font-semibold text-gray-900 dark:text-white">Path Finder</h2>
          <p className="mb-4 text-xs text-gray-500 dark:text-gray-400">
            Find the shortest directed path between two entities using BFS.
          </p>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                From Entity ID
              </label>
              <input
                type="number"
                min={1}
                value={fromId}
                onChange={(e) => setFromId(e.target.value)}
                className="w-36 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                placeholder="e.g. 1"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                To Entity ID
              </label>
              <input
                type="number"
                min={1}
                value={toId}
                onChange={(e) => setToId(e.target.value)}
                className="w-36 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
                placeholder="e.g. 5"
              />
            </div>
            <button
              onClick={findPath}
              disabled={loadingPath || !fromId || !toId}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loadingPath ? "Searching…" : "Find Path"}
            </button>
          </div>

          {pathError && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
              {pathError}
            </div>
          )}

          {pathResult && (
            <div className="mt-4">
              {!pathResult.found ? (
                <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-400">
                  <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                  </svg>
                  No directed path found from entity {fromId} to entity {toId}.
                </div>
              ) : (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-800 dark:bg-emerald-900/10">
                  <div className="mb-3 flex items-center gap-3 text-xs">
                    <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                      Path found
                    </span>
                    <span className="text-emerald-600 dark:text-emerald-500">
                      Length: {pathResult.length} hop{pathResult.length !== 1 ? "s" : ""}
                    </span>
                    {pathResult.relations && pathResult.relations.length > 0 && (
                      <span className="text-emerald-600 dark:text-emerald-500">
                        Via: {pathResult.relations.join(" → ")}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-1">
                    {pathResult.steps?.map((step, idx) => (
                      <span key={step.entity_id} className="flex items-center gap-1">
                        <Link
                          href={`/entities/${step.entity_id}`}
                          className="rounded-md bg-white px-2 py-1 text-xs font-medium text-indigo-700 shadow-sm ring-1 ring-indigo-200 hover:ring-indigo-400 dark:bg-gray-800 dark:text-indigo-300 dark:ring-indigo-800"
                        >
                          {step.primary_label ?? `#${step.entity_id}`}
                        </Link>
                        {idx < (pathResult.steps?.length ?? 0) - 1 && (
                          <span className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                            <span className="text-[10px] text-indigo-500 dark:text-indigo-400">
                              {pathResult.relations?.[idx]}
                            </span>
                            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
