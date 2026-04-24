import { useState, useRef, useEffect } from "react";
import { useLocation } from "react-router-dom";
import { Bell, Search, ChevronDown, LogOut, User, Settings, Menu } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";

// ── Route → page title map ────────────────────────────────────────────────────
const PAGE_TITLES = {
    "/dashboard":  { title: "Dashboard",       subtitle: "Overview of community needs and volunteer activity" },
    "/upload":     { title: "Upload Data",     subtitle: "Ingest CSV, JSON, text, or image survey data" },
    "/analyze":    { title: "Need Analysis",   subtitle: "AI-powered community need categorisation" },
    "/volunteers": { title: "Volunteers",      subtitle: "Manage volunteer profiles and availability" },
    "/match":      { title: "Smart Matching",  subtitle: "Match volunteers to community needs" },
    "/reports":    { title: "Reports",         subtitle: "Analytics and performance insights" },
    "/settings":   { title: "Settings",        subtitle: "Account and system preferences" },
};

function getInitials(name = "") {
    return name
        .split(" ")
        .filter(Boolean)
        .slice(0, 2)
        .map((n) => n[0].toUpperCase())
        .join("");
}

export default function Header({ onToggleSidebar }) {
    const location = useLocation();
    const { displayName, email, photoURL, role, logout } = useAuth();

    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [searchFocused, setSearchFocused] = useState(false);
    const [searchQuery, setSearchQuery]   = useState("");

    const dropdownRef = useRef(null);

    const pageInfo = PAGE_TITLES[location.pathname] ?? {
        title:    "SVAS",
        subtitle: "Smart Volunteer Allocation System",
    };

    // Close dropdown on outside click
    useEffect(() => {
        function handleClickOutside(e) {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
                setDropdownOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const roleBadgeClass = {
        ADMIN:       "badge badge-danger",
        COORDINATOR: "badge badge-warning",
        VOLUNTEER:   "badge badge-success",
    }[role] ?? "badge badge-neutral";

    return (
        <header
            style={{
                background: "#fff",
                borderBottom: "1px solid var(--color-brand-cream)",
                height: "64px",
                display: "flex",
                alignItems: "center",
                padding: "0 1.5rem",
                gap: "1rem",
                position: "sticky",
                top: 0,
                zIndex: 30,
                boxShadow: "0 1px 4px rgba(164,114,81,0.07)",
            }}
        >
            {/* ── Sidebar toggle (mobile) ────────────────────────────────────── */}
            <button
                className="btn btn-ghost btn-icon"
                onClick={onToggleSidebar}
                aria-label="Toggle sidebar"
                style={{ flexShrink: 0 }}
            >
                <Menu size={20} />
            </button>

            {/* ── Page title ────────────────────────────────────────────────── */}
            <div style={{ flex: 1, minWidth: 0 }}>
                <h1
                    style={{
                        fontSize: "1.1rem",
                        fontWeight: 700,
                        color: "var(--color-gray-900)",
                        lineHeight: 1.2,
                        margin: 0,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                    }}
                >
                    {pageInfo.title}
                </h1>
                <p
                    style={{
                        fontSize: "0.75rem",
                        color: "var(--color-gray-400)",
                        margin: 0,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                    }}
                >
                    {pageInfo.subtitle}
                </p>
            </div>

            {/* ── Search bar ────────────────────────────────────────────────── */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    background: searchFocused
                        ? "#fff"
                        : "var(--color-brand-cream-50)",
                    border: `1.5px solid ${searchFocused ? "var(--color-accent)" : "var(--color-brand-cream)"}`,
                    borderRadius: "0.625rem",
                    padding: "0.375rem 0.875rem",
                    width: "220px",
                    transition: "all 0.15s ease",
                    boxShadow: searchFocused
                        ? "0 0 0 3px rgba(221,158,89,0.18)"
                        : "none",
                    flexShrink: 0,
                }}
                className="header-search"
            >
                <Search
                    size={15}
                    style={{
                        color: searchFocused
                            ? "var(--color-accent-dark)"
                            : "var(--color-gray-400)",
                        flexShrink: 0,
                        transition: "color 0.15s ease",
                    }}
                />
                <input
                    type="text"
                    placeholder="Search needs, volunteers…"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onFocus={() => setSearchFocused(true)}
                    onBlur={() => setSearchFocused(false)}
                    style={{
                        border: "none",
                        background: "transparent",
                        outline: "none",
                        fontSize: "0.8125rem",
                        color: "var(--color-gray-700)",
                        width: "100%",
                    }}
                />
            </div>

            {/* ── Notification bell ─────────────────────────────────────────── */}
            <button
                className="btn btn-ghost btn-icon"
                aria-label="Notifications"
                style={{ position: "relative", flexShrink: 0 }}
            >
                <Bell size={19} />
                {/* Red badge */}
                <span
                    style={{
                        position: "absolute",
                        top: "4px",
                        right: "4px",
                        width: "8px",
                        height: "8px",
                        background: "var(--color-danger)",
                        borderRadius: "50%",
                        border: "2px solid #fff",
                    }}
                />
            </button>

            {/* ── User dropdown ──────────────────────────────────────────────── */}
            <div ref={dropdownRef} style={{ position: "relative", flexShrink: 0 }}>
                <button
                    onClick={() => setDropdownOpen((o) => !o)}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        background: dropdownOpen
                            ? "var(--color-brand-cream-50)"
                            : "transparent",
                        border: "none",
                        borderRadius: "0.625rem",
                        padding: "0.375rem 0.625rem",
                        cursor: "pointer",
                        transition: "background 0.15s ease",
                    }}
                    aria-label="User menu"
                    aria-expanded={dropdownOpen}
                >
                    {/* Avatar */}
                    {photoURL ? (
                        <img
                            src={photoURL}
                            alt={displayName}
                            style={{
                                width: "32px",
                                height: "32px",
                                borderRadius: "50%",
                                objectFit: "cover",
                                flexShrink: 0,
                            }}
                        />
                    ) : (
                        <div
                            className="avatar avatar-sm"
                            style={{ width: "32px", height: "32px", fontSize: "0.7rem" }}
                        >
                            {getInitials(displayName)}
                        </div>
                    )}

                    {/* Name + role */}
                    <div style={{ textAlign: "left", lineHeight: 1.2 }}>
                        <div
                            style={{
                                fontSize: "0.8125rem",
                                fontWeight: 600,
                                color: "var(--color-gray-800)",
                                maxWidth: "100px",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                            }}
                        >
                            {displayName}
                        </div>
                        <div>
                            <span className={roleBadgeClass} style={{ fontSize: "0.6rem", padding: "0.1rem 0.45rem" }}>
                                {role}
                            </span>
                        </div>
                    </div>

                    <ChevronDown
                        size={14}
                        style={{
                            color: "var(--color-gray-400)",
                            transform: dropdownOpen ? "rotate(180deg)" : "none",
                            transition: "transform 0.2s ease",
                        }}
                    />
                </button>

                {/* Dropdown menu */}
                {dropdownOpen && (
                    <div
                        style={{
                            position: "absolute",
                            top: "calc(100% + 8px)",
                            right: 0,
                            minWidth: "200px",
                            background: "#fff",
                            borderRadius: "0.75rem",
                            boxShadow: "var(--shadow-modal)",
                            border: "1px solid var(--color-brand-cream)",
                            overflow: "hidden",
                            zIndex: 50,
                            animation: "slideUp 0.15s ease",
                        }}
                    >
                        {/* Profile header */}
                        <div
                            style={{
                                padding: "0.875rem 1rem",
                                background: "linear-gradient(135deg, var(--color-brand-cream-50), var(--color-brand-gold-50))",
                                borderBottom: "1px solid var(--color-brand-cream)",
                            }}
                        >
                            <div
                                style={{
                                    fontSize: "0.8125rem",
                                    fontWeight: 600,
                                    color: "var(--color-gray-800)",
                                }}
                            >
                                {displayName}
                            </div>
                            <div
                                style={{
                                    fontSize: "0.75rem",
                                    color: "var(--color-gray-500)",
                                    marginTop: "1px",
                                }}
                            >
                                {email}
                            </div>
                        </div>

                        {/* Menu items */}
                        <div style={{ padding: "0.375rem" }}>
                            <DropdownItem
                                icon={<User size={15} />}
                                label="My Profile"
                                href="/settings"
                                onClick={() => setDropdownOpen(false)}
                            />
                            <DropdownItem
                                icon={<Settings size={15} />}
                                label="Settings"
                                href="/settings"
                                onClick={() => setDropdownOpen(false)}
                            />
                        </div>

                        <div
                            style={{
                                borderTop: "1px solid var(--color-brand-cream)",
                                padding: "0.375rem",
                            }}
                        >
                            <button
                                onClick={() => {
                                    setDropdownOpen(false);
                                    logout();
                                }}
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.625rem",
                                    width: "100%",
                                    padding: "0.5rem 0.75rem",
                                    border: "none",
                                    background: "transparent",
                                    borderRadius: "0.5rem",
                                    cursor: "pointer",
                                    fontSize: "0.875rem",
                                    color: "var(--color-danger)",
                                    fontWeight: 500,
                                    transition: "background 0.12s ease",
                                    textAlign: "left",
                                }}
                                onMouseEnter={(e) =>
                                    (e.currentTarget.style.background = "var(--color-danger-50)")
                                }
                                onMouseLeave={(e) =>
                                    (e.currentTarget.style.background = "transparent")
                                }
                            >
                                <LogOut size={15} />
                                Sign Out
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </header>
    );
}

// ── Sub-component ─────────────────────────────────────────────────────────────

function DropdownItem({ icon, label, href, onClick }) {
    return (
        <a
            href={href}
            onClick={onClick}
            style={{
                display: "flex",
                alignItems: "center",
                gap: "0.625rem",
                padding: "0.5rem 0.75rem",
                borderRadius: "0.5rem",
                fontSize: "0.875rem",
                color: "var(--color-gray-700)",
                fontWeight: 450,
                textDecoration: "none",
                transition: "background 0.12s ease",
            }}
            onMouseEnter={(e) =>
                (e.currentTarget.style.background = "var(--color-brand-cream-50)")
            }
            onMouseLeave={(e) =>
                (e.currentTarget.style.background = "transparent")
            }
        >
            <span style={{ color: "var(--color-gray-500)" }}>{icon}</span>
            {label}
        </a>
    );
}
