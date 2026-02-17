"use client";

import { useSidebar } from "./SidebarProvider";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function LayoutContent({ children }: { children: React.ReactNode }) {
    const { collapsed } = useSidebar();

    return (
        <div className="flex min-h-screen">
            <Sidebar />
            <div
                className={`flex flex-1 flex-col transition-all duration-300 ${collapsed ? "ml-20" : "ml-64"
                    }`}
            >
                <Header />
                <main className="flex-1 p-6 transition-all duration-300">
                    <div className={`mx-auto transition-all duration-300 ${collapsed ? "max-w-none px-4" : "max-w-7xl"}`}>
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
}
