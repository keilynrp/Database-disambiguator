"use client";

import { useState, useRef } from "react";

interface AnalyzeResult {
    filename: string;
    format: string;
    count: number;
    structure: string[];
}

export default function DataSourceSchemaAnalyzer() {
    const [dragOver, setDragOver] = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult] = useState<AnalyzeResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    async function handleAnalyze(file: File) {
        setAnalyzing(true);
        setResult(null);
        setError(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch("http://localhost:8000/analyze", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                let errMessage = "Analysis failed";
                try {
                    const err = await res.json();
                    errMessage = err.detail || errMessage;
                } catch (e) { }
                throw new Error(errMessage);
            }

            const data: AnalyzeResult = await res.json();
            setResult(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Analysis failed");
        } finally {
            setAnalyzing(false);
        }
    }

    function handleDrop(e: React.DragEvent) {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleAnalyze(file);
    }

    function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (file) handleAnalyze(file);
        e.target.value = "";
    }

    return (
        <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
            <div className="mb-5 flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-100 dark:bg-purple-500/10">
                    <svg className="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                </div>
                <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white">Analyze Data Source Schema</h3>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        Preview structure for CSV, JSON, XML, RDF, Parquet, Logs, and Bibliographic formats (TXT, RIS, BibTeX).
                    </p>
                </div>
            </div>

            <div
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-6 transition-colors ${dragOver
                    ? "border-purple-500 bg-purple-50 dark:border-purple-400 dark:bg-purple-500/5"
                    : "border-gray-300 hover:border-gray-400 dark:border-gray-700 dark:hover:border-gray-600"
                    }`}
            >
                <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileSelect}
                    className="hidden"
                    accept=".csv,.xlsx,.xls,.json,.jsonld,.xml,.rdf,.ttl,.log,.txt,.ris,.bib,.parquet,.pkl"
                />

                {analyzing ? (
                    <>
                        <svg className="mb-3 h-8 w-8 animate-spin text-purple-600" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">Extracting multidimensional schema...</p>
                    </>
                ) : (
                    <>
                        <svg className="mb-3 h-8 w-8 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                        </svg>
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            Drop an arbitrary file here or <span className="text-purple-600 dark:text-purple-400">browse</span>
                        </p>
                    </>
                )}
            </div>

            {error && (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-500/5">
                    <p className="text-sm font-medium text-red-800 dark:text-red-300">{error}</p>
                </div>
            )}

            {result && (
                <div className="mt-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-700/10 dark:bg-purple-500/10 dark:text-purple-400 dark:ring-purple-500/20">
                            {result.format.toUpperCase()}
                        </span>
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {result.filename}
                        </span>
                        <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">
                            Found {result.count} structural elements
                        </span>
                    </div>

                    <div className="max-h-60 overflow-y-auto rounded-xl border border-gray-200 bg-gray-50 p-2 dark:border-gray-800 dark:bg-gray-900/50">
                        {result.structure.length > 0 ? (
                            <ul className="space-y-1">
                                {result.structure.map((item, i) => (
                                    <li key={i} className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-white dark:hover:bg-gray-800">
                                        <div className="h-1.5 w-1.5 rounded-full bg-purple-400 dark:bg-purple-500"></div>
                                        <span className="text-sm text-gray-700 dark:text-gray-300 font-mono break-all">{item}</span>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="p-3 text-center text-sm text-gray-500">No structured schema detected.</p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
