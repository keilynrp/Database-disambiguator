"use client";

import React, { createContext, useContext, useState, ReactNode, useEffect } from "react";
import { translations, Language } from "../i18n/translations";

interface LanguageContextType {
    language: Language;
    setLanguage: (lang: Language) => void;
    t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
    const [language, setLanguage] = useState<Language>("en");
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        const saved = localStorage.getItem("app_lang");
        if (saved && (saved === "en" || saved === "es")) {
            setLanguage(saved as Language);
        } else {
            // Default to spanish since user asked mostly in Spanish
            setLanguage("es");
        }
        setMounted(true);
    }, []);

    const changeLanguage = (lang: Language) => {
        setLanguage(lang);
        localStorage.setItem("app_lang", lang);
    };

    const t = (key: string): string => {
        const dict = translations[language];
        // @ts-ignore
        return dict[key] || key;
    };

    if (!mounted) {
        return null; // Or a loader
    }

    return (
        <LanguageContext.Provider value={{ language, setLanguage: changeLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
}

export function useLanguage() {
    const context = useContext(LanguageContext);
    if (context === undefined) {
        throw new Error("useLanguage must be used within a LanguageProvider");
    }
    return context;
}
