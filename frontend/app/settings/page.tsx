"use client";

import { useLanguage } from "../contexts/LanguageContext";
import { useTheme } from "../contexts/ThemeContext";

export default function SettingsPage() {
    const { language, setLanguage, t } = useLanguage();
    const { theme, setTheme } = useTheme();

    return (
        <div className="max-w-4xl p-8">
            <h1 className="mb-2 text-2xl font-bold text-gray-900 dark:text-white">
                {t('settings.title')}
            </h1>
            <p className="mb-8 text-sm text-gray-500 dark:text-gray-400">
                {t('settings.subtitle')}
            </p>

            <div className="space-y-6">
                {/* Language */}
                <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
                    <div className="flex items-start justify-between">
                        <div>
                            <h3 className="text-base font-medium text-gray-900 dark:text-white">
                                {t('settings.language')}
                            </h3>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                {t('settings.language.desc')}
                            </p>
                        </div>

                        <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-1 dark:border-gray-700 dark:bg-gray-800">
                            <button
                                onClick={() => setLanguage('en')}
                                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${language === 'en'
                                    ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                                    }`}
                            >
                                <span className="text-lg">🇺🇸</span>
                                English
                            </button>
                            <button
                                onClick={() => setLanguage('es')}
                                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${language === 'es'
                                    ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                                    }`}
                            >
                                <span className="text-lg">🇪🇸</span>
                                Español
                            </button>
                        </div>
                    </div>
                </div>

                {/* Theme */}
                <div className="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
                    <div className="flex items-start justify-between">
                        <div>
                            <h3 className="text-base font-medium text-gray-900 dark:text-white">
                                {t('settings.theme')}
                            </h3>
                            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                                {t('settings.theme.desc')}
                            </p>
                        </div>

                        <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 p-1 dark:border-gray-700 dark:bg-gray-800">
                            <button
                                onClick={() => setTheme('light')}
                                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${theme === 'light'
                                    ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                                    }`}
                            >
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                                </svg>
                                {t('settings.theme.light')}
                            </button>
                            <button
                                onClick={() => setTheme('dark')}
                                className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${theme === 'dark'
                                    ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
                                    : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
                                    }`}
                            >
                                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                                </svg>
                                {t('settings.theme.dark')}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
