"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

type Theme = "light" | "dark";

interface ThemeContextType {
    theme: Theme;
    setTheme: (theme: Theme) => void;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

function applyTheme(theme: Theme) {
    if (theme === "dark") {
        document.documentElement.classList.add("dark");
    } else {
        document.documentElement.classList.remove("dark");
    }
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [theme, setThemeState] = useState<Theme>("light");
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        const saved = localStorage.getItem("app_theme") as Theme | null;
        let initial: Theme;
        if (saved === "light" || saved === "dark") {
            initial = saved;
        } else {
            initial = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        }
        setThemeState(initial);
        applyTheme(initial);
        setMounted(true);
    }, []);

    const setTheme = useCallback((newTheme: Theme) => {
        setThemeState(newTheme);
        localStorage.setItem("app_theme", newTheme);
        applyTheme(newTheme);
    }, []);

    const toggleTheme = useCallback(() => {
        setTheme(theme === "dark" ? "light" : "dark");
    }, [theme, setTheme]);

    if (!mounted) {
        return null;
    }

    return (
        <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return context;
}
