import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function Layout() {
    const [collapsed, setCollapsed] = useState(false);

    const sidebarWidth = collapsed ? 72 : 260;

    return (
        <div
            style={{
                display: "flex",
                minHeight: "100svh",
                background: "var(--color-surface)",
            }}
        >
            {/* ── Sidebar ───────────────────────────────────────────────────── */}
            <Sidebar
                collapsed={collapsed}
                onToggle={() => setCollapsed((c) => !c)}
            />

            {/* ── Main content area ─────────────────────────────────────────── */}
            <div
                style={{
                    flex: 1,
                    marginLeft: sidebarWidth,
                    display: "flex",
                    flexDirection: "column",
                    minWidth: 0,
                    transition: "margin-left 250ms cubic-bezier(0.4,0,0.2,1)",
                }}
            >
                {/* Sticky header */}
                <Header onToggleSidebar={() => setCollapsed((c) => !c)} />

                {/* Page content */}
                <main
                    style={{
                        flex: 1,
                        padding: "1.5rem",
                        overflowY: "auto",
                        overflowX: "hidden",
                    }}
                >
                    <Outlet />
                </main>

                {/* Footer */}
                <footer
                    style={{
                        padding: "0.75rem 1.5rem",
                        borderTop: "1px solid var(--color-brand-cream)",
                        background: "#fff",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: "1rem",
                        flexWrap: "wrap",
                    }}
                >
                    <span
                        style={{
                            fontSize: "0.75rem",
                            color: "var(--color-gray-400)",
                        }}
                    >
                        © {new Date().getFullYear()} SVAS — Smart Volunteer Allocation
                        System
                    </span>
                    <span
                        style={{
                            fontSize: "0.75rem",
                            color: "var(--color-gray-400)",
                        }}
                    >
                        Powered by Gemini AI · Firebase · Google Cloud
                    </span>
                </footer>
            </div>
        </div>
    );
}
