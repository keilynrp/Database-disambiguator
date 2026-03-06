"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";

interface MonteCarloData {
    current_citations: number;
    simulation_years: number;
    total_simulations: number;
    predicted_5yr_median: number;
    trajectories: Array<{
        year: string;
        optimistic: number;
        median: number;
        pessimistic: number;
    }>;
}

export default function MonteCarloChart({ productId }: { productId: number }) {
    const [data, setData] = useState<MonteCarloData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        async function fetchMonteCarlo() {
            setLoading(true);
            setError(null);
            try {
                const res = await apiFetch(`/enrich/montecarlo/${productId}`);
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.detail || "Failed to load Monte Carlo simulation");
                }
                const parsed = await res.json();
                if (isMounted) setData(parsed);
            } catch (err: any) {
                if (isMounted) setError(err.message);
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        if (productId) {
            fetchMonteCarlo();
        }

        return () => { isMounted = false; };
    }, [productId]);

    if (loading) {
        return (
            <div className="flex h-64 w-full flex-col items-center justify-center rounded-xl bg-gray-50/50 dark:bg-gray-800/20">
                <svg className="h-6 w-6 animate-spin text-purple-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <span className="mt-3 text-sm font-medium text-gray-500">Running Monte Carlo Simulations...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex h-64 w-full flex-col items-center justify-center rounded-xl bg-red-50/50 p-6 text-center dark:bg-red-500/10">
                <svg className="h-8 w-8 text-red-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span className="text-sm font-semibold text-red-700 dark:text-red-400">Simulation Failed</span>
                <span className="text-xs text-red-600/70 dark:text-red-400/70 mt-1">{error}</span>
            </div>
        );
    }

    if (!data) return null;

    return (
        <div className="flex h-full w-full flex-col">
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <h4 className="flex items-center gap-2 text-sm font-bold text-gray-900 dark:text-white">
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-purple-100 text-[10px] text-purple-700 dark:bg-purple-500/20 dark:text-purple-400">
                            🔮
                        </span>
                        Impact Projection
                    </h4>
                    <p className="text-xs text-gray-500 mt-0.5">
                        Phase 4: Simulated over {data.simulation_years} years ({data.total_simulations} iterations)
                    </p>
                </div>
                <div className="text-right">
                    <div className="text-lg font-black text-purple-600 dark:text-purple-400">{data.predicted_5yr_median}</div>
                    <div className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Predicted Med. Impact</div>
                </div>
            </div>

            <div className="h-48 w-full flex-1">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data.trajectories} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorMedian" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" className="dark:stroke-gray-800" />
                        <XAxis dataKey="year" tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#6b7280' }} dy={10} />
                        <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: '#6b7280' }} />
                        <Tooltip
                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                            itemStyle={{ fontWeight: 600 }}
                        />

                        {/* Bound Area (10th to 90th percentile spread) */}
                        <Area type="monotone" dataKey="optimistic" stroke="none" fill="#f3f4f6" fillOpacity={0.5} className="dark:fill-gray-800/50" />
                        <Area type="monotone" dataKey="pessimistic" stroke="none" fill="#ffffff" fillOpacity={1} className="dark:fill-gray-900" />

                        {/* Main Median Line */}
                        <Area
                            type="monotone"
                            dataKey="median"
                            stroke="#8b5cf6"
                            strokeWidth={3}
                            fillOpacity={1}
                            fill="url(#colorMedian)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}
