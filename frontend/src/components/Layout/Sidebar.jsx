import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
    LayoutDashboard,
    Upload,
    Brain,
    Users,
    GitBranch,
    BarChart2,
    Settings,
    ChevronLeft,
    ChevronRight,
    LogOut,
    Heart,
    Bell,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";

// ── Navigation items ──────────────────────────────────────────────────────────
const NAV_ITEMS = [
    {
        to: "/dashboard",
        label: "Dashboard",
        icon: LayoutDashboard,
        description: "Overview & stats",
    },
    {
        to: "/upload",
        label: "Upload Data",
        icon: Upload,
        description: "Ingest CSV / JSON / images",
    },
    {
        to: "/analyze",
        label: "Need Analysis",
        icon: Brain,
        description: "AI-powered categorisation",
    },
    {
        to: "/volunteers",
        label: "Volunteers",
        icon: Users,
        description: "Profiles & availability",
    },
    {
        to: "/match",
        label: "Task Matching",
        icon: GitBranch,
        description: "Smart assignment engine",
    },
    {
        to: "/reports",
        label: "Reports",
        icon: BarChart2,
        description: "Analytics & insights",
    },
    {
        to: "/settings",
        label: "Settings",
        icon: Settings,
        description: "Profile & preferences",
    },
];

// ── Role badge colours ────────────────────────────────────────────────────────
const ROLE_STYLES = {
    ADMIN: { bg: "#f5ede5", color: "#7a5438", label: "Admin" },
    COORDINATOR: { bg: "#fbf3e6", color: "#8b5c12", label: "Coordinator" },
    VOLUNTEER: { bg: "#f4fbe9", color: "#2e6b48", label: "Volunteer" },
};

// ── Avatar initials helper ────────────────────────────────────────────────────
function getInitials(name = "") {
    return name
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((w) => w[0].toUpperCase())
        .join("");
}

// ─────────────────────────────────────────────────────────────────────────────
// Sidebar component
// ─────────────────────────────────────────────────────────────────────────────

export default function Sidebar({ collapsed, onToggle }) {
    const { displayName, email, role, logout, photoURL } = useAuth();
    const navigate = useNavigate();
    const [loggingOut, setLoggingOut] = useState(false);

    const roleStyle = ROLE_STYLES[role] || ROLE_STYLES.VOLUNTEER;
    const initials = getInitials(displayName);

    const handleLogout = async () => {
        setLoggingOut(true);
        try {
            await logout();
            navigate("/login");
        } catch {
            // toast already shown by AuthContext
        } finally {
            setLoggingOut(false);
        }
    };

    return (
        <aside
            className="sidebar"
            style={{ width: collapsed ? 72 : 260 }}
        >
            {/* ── Logo / Brand ─────────────────────────────────────────────── */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: collapsed ? "1.25rem 1rem" : "1.25rem 1.25rem",
                    borderBottom: "1px solid var(--color-brand-cream)",
                    overflow: "hidden",
                    minHeight: 64,
                }}
            >
                {/* Logo mark */}
                <div
                    style={{
                        width: 38,
                        height: 38,
                        borderRadius: "0.625rem",
                        background:
                            "linear-gradient(135deg, var(--color-primary-dark) 0%, var(--color-accent) 100%)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        boxShadow: "0 2px 8px rgba(164,114,81,0.3)",
                    }}
                >
                    <Heart size={20} color="#fff" strokeWidth={2.5} />
                </div>

                {/* Brand name */}
                {!collapsed && (
                    <div style={{ overflow: "hidden" }}>
                        <div
                            style={{
                                fontSize: "1.0625rem",
                                fontWeight: 700,
                                color: "var(--color-primary-dark)",
                                lineHeight: 1.2,
                                whiteSpace: "nowrap",
                            }}
                        >
                            SVAS
                        </div>
                        <div
                            style={{
                                fontSize: "0.7rem",
                                color: "var(--color-gray-400)",
                                whiteSpace: "nowrap",
                                letterSpacing: "0.03em",
                            }}
                        >
                            Volunteer Allocation
                        </div>
                    </div>
                )}
            </div>

            {/* ── Navigation ───────────────────────────────────────────────── */}
            <nav
                style={{
                    flex: 1,
                    overflowY: "auto",
                    overflowX: "hidden",
                    padding: "0.75rem 0.625rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.125rem",
                }}
            >
                {NAV_ITEMS.map(({ to, label, icon: Icon, description }) => (
                    <NavLink
                        key={to}
                        to={to}
                        title={collapsed ? label : undefined}
                        className={({ isActive }) =>
                            `nav-item ${isActive ? "active" : ""}`
                        }
                        style={{
                            justifyContent: collapsed ? "center" : "flex-start",
                            padding: collapsed ? "0.625rem" : "0.625rem 1rem",
                        }}
                    >
                        {({ isActive }) => (
                            <>
                                <Icon
                                    size={20}
                                    strokeWidth={isActive ? 2.5 : 2}
                                    style={{
                                        flexShrink: 0,
                                        color: isActive
                                            ? "var(--color-primary-dark)"
                                            : "var(--color-gray-400)",
                                        transition: "color 150ms",
                                    }}
                                />
                                {!collapsed && (
                                    <span
                                        style={{
                                            overflow: "hidden",
                                            textOverflow: "ellipsis",
                                            whiteSpace: "nowrap",
                                        }}
                                    >
                                        {label}
                                    </span>
                                )}
                            </>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* ── User profile section ─────────────────────────────────────── */}
            <div
                style={{
                    borderTop: "1px solid var(--color-brand-cream)",
                    padding: collapsed ? "0.75rem 0.625rem" : "0.875rem 1rem",
                }}
            >
                {/* Profile row */}
                <div
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.75rem",
                        marginBottom: "0.75rem",
                        overflow: "hidden",
                        justifyContent: collapsed ? "center" : "flex-start",
                    }}
                >
                    {/* Avatar */}
                    {photoURL ? (
                        <img
                            src={photoURL}
                            alt={displayName}
                            style={{
                                width: 36,
                                height: 36,
                                borderRadius: "50%",
                                objectFit: "cover",
                                flexShrink: 0,
                                border: "2px solid var(--color-brand-cream)",
                            }}
                        />
                    ) : (
                        <div
                            className="avatar avatar-sm"
                            style={{ width: 36, height: 36, fontSize: "0.8rem", flexShrink: 0 }}
                            title={displayName}
                        >
                            {initials || "U"}
                        </div>
                    )}

                    {/* Name + role */}
                    {!collapsed && (
                        <div style={{ overflow: "hidden", flex: 1, minWidth: 0 }}>
                            <div
                                style={{
                                    fontSize: "0.875rem",
                                    fontWeight: 600,
                                    color: "var(--color-gray-800)",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                }}
                            >
                                {displayName}
                            </div>
                            <div
                                style={{
                                    fontSize: "0.7rem",
                                    whiteSpace: "nowrap",
                                    overflow: "hidden",
                                    textOverflow: "ellipsis",
                                    color: "var(--color-gray-400)",
                                }}
                            >
                                {email}
                            </div>
                        </div>
                    )}
                </div>

                {/* Role badge */}
                {!collapsed && (
                    <div
                        style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "0.3rem",
                            padding: "0.2rem 0.6rem",
                            borderRadius: 999,
                            background: roleStyle.bg,
                            color: roleStyle.color,
                            fontSize: "0.72rem",
                            fontWeight: 600,
                            marginBottom: "0.75rem",
                            letterSpacing: "0.01em",
                        }}
                    >
                        <span
                            style={{
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                background: roleStyle.color,
                                display: "inline-block",
                            }}
                        />
                        {roleStyle.label}
                    </div>
                )}

                {/* Logout button */}
                <button
                    onClick={handleLogout}
                    disabled={loggingOut}
                    title="Sign out"
                    style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: collapsed ? "center" : "flex-start",
                        gap: "0.5rem",
                        width: "100%",
                        padding: collapsed ? "0.5rem" : "0.5rem 0.75rem",
                        borderRadius: "0.5rem",
                        border: "1px solid var(--color-danger-100)",
                        background: loggingOut ? "var(--color-danger-50)" : "transparent",
                        color: "var(--color-danger)",
                        fontSize: "0.875rem",
                        fontWeight: 500,
                        cursor: loggingOut ? "not-allowed" : "pointer",
                        opacity: loggingOut ? 0.7 : 1,
                        transition: "background 150ms, color 150ms",
                    }}
                    onMouseEnter={(e) => {
                        if (!loggingOut) {
                            e.currentTarget.style.background = "var(--color-danger-50)";
                        }
                    }}
                    onMouseLeave={(e) => {
                        if (!loggingOut) {
                            e.currentTarget.style.background = "transparent";
                        }
                    }}
                >
                    <LogOut size={16} strokeWidth={2} style={{ flexShrink: 0 }} />
                    {!collapsed && (
                        <span>{loggingOut ? "Signing out…" : "Sign Out"}</span>
                    )}
                </button>
            </div>

            {/* ── Collapse toggle ──────────────────────────────────────────── */}
            <button
                onClick={onToggle}
                title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
                style={{
                    position: "absolute",
                    top: "50%",
                    right: -12,
                    transform: "translateY(-50%)",
                    width: 24,
                    height: 24,
                    borderRadius: "50%",
                    background: "var(--color-surface-raised)",
                    border: "1px solid var(--color-brand-cream)",
                    boxShadow: "0 1px 4px rgba(164,114,81,0.15)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    color: "var(--color-primary)",
                    zIndex: 50,
                    transition: "box-shadow 150ms",
                }}
                onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = "0 2px 8px rgba(164,114,81,0.25)";
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = "0 1px 4px rgba(164,114,81,0.15)";
                }}
            >
                {collapsed ? (
                    <ChevronRight size={13} strokeWidth={2.5} />
                ) : (
                    <ChevronLeft size={13} strokeWidth={2.5} />
                )}
            </button>
        </aside>
    );
}
