import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout() {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <div className="flex min-h-screen bg-brand-cream-50 font-sans">
            {/* ── Sidebar ───────────────────────────────────────────────────── */}
            <Sidebar
                collapsed={collapsed}
                onToggle={() => setCollapsed((c) => !c)}
            />

            {/* ── Main content area ─────────────────────────────────────────── */}
            <div
                className={`flex-1 flex flex-col min-w-0 transition-all duration-300 ease-in-out ${
                    collapsed ? "ml-20" : "ml-64"
                }`}
            >
                {/* Sticky header */}
                <Header onToggleSidebar={() => setCollapsed((c) => !c)} />

                {/* Page content */}
                <main className="flex-1 p-8 overflow-y-auto">
                    <Outlet />
                </main>

                {/* Footer */}
                <footer className="px-8 py-4 bg-white border-t border-brand-cream/30 flex items-center justify-between gap-4 flex-wrap">
                    <span className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-[0.2em]">
                        © {new Date().getFullYear()} SVAS — Smart Volunteer Allocation System
                    </span>
                    <span className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-[0.2em]">
                        Powered by Gemini AI · Firebase · Google Cloud
                    </span>
                </footer>
            </div>
        </div>
    );
}
