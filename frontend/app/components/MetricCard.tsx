interface MetricCardProps {
    label: string;
    value: string | number;
    icon: React.ReactNode;
    trend?: {
        value: string;
        positive: boolean;
    };
    subtitle?: string;
}

export default function MetricCard({ label, value, icon, trend, subtitle }: MetricCardProps) {
    return (
        <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-900">
            <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-100 dark:bg-gray-800">
                    {icon}
                </div>
                {trend && (
                    <span className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-xs font-medium ${
                        trend.positive
                            ? "bg-green-50 text-green-600 dark:bg-green-500/10 dark:text-green-400"
                            : "bg-red-50 text-red-600 dark:bg-red-500/10 dark:text-red-400"
                    }`}>
                        <svg className={`h-3 w-3 ${trend.positive ? "" : "rotate-180"}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                        </svg>
                        {trend.value}
                    </span>
                )}
            </div>
            <div className="mt-4">
                <h3 className="text-2xl font-bold text-gray-900 dark:text-white">{value}</h3>
                <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{label}</p>
                {subtitle && (
                    <p className="mt-1 text-xs text-gray-400 dark:text-gray-500">{subtitle}</p>
                )}
            </div>
        </div>
    );
}
