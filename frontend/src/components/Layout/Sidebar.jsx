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
    Layers
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";

// ── Navigation items ──────────────────────────────────────────────────────────
const NAV_ITEMS = [
    {
        to: "/dashboard",
        label: "Dashboard",
        icon: LayoutDashboard,
    },
    {
        to: "/analysis",
        label: "Need Analysis",
        icon: Brain,
    },
    {
        to: "/volunteers",
        label: "Volunteers",
        icon: Users,
    },
    {
        to: "/matching",
        label: "Task Matching",
        icon: GitBranch,
    },
    {
        to: "/settings",
        label: "Settings",
        icon: Settings,
    },
];

// ── Role badge colours ────────────────────────────────────────────────────────
const ROLE_STYLES = {
    ADMIN: "bg-brand-gold text-white",
    COORDINATOR: "bg-brand-cream text-brand-brown-dark",
    VOLUNTEER: "bg-brand-mint text-brand-brown-dark",
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

export default function Sidebar({ collapsed, onToggle }) {
    const { displayName, email, role, logout, photoURL } = useAuth();
    const navigate = useNavigate();
    const [loggingOut, setLoggingOut] = useState(false);

    const initials = getInitials(displayName);

    const handleLogout = async () => {
        setLoggingOut(true);
        try {
            await logout();
            navigate("/login");
        } catch {
            // Error handled in AuthContext
        } finally {
            setLoggingOut(false);
        }
    };

    return (
        <aside
            className={`fixed left-0 top-0 h-screen bg-brand-brown text-white z-50 transition-all duration-300 ease-in-out shadow-2xl flex flex-col ${
                collapsed ? "w-20" : "w-64"
            }`}
        >
            {/* ── Logo / Brand ─────────────────────────────────────────────── */}
            <div className={`p-6 flex items-center gap-3 border-b border-white/10 ${collapsed ? "justify-center" : ""}`}>
                <div className="w-10 h-10 rounded-xl bg-brand-gold flex items-center justify-center flex-shrink-0 shadow-lg shadow-black/20">
                    <Heart size={24} className="text-brand-brown" strokeWidth={2.5} />
                </div>
                {!collapsed && (
                    <div className="overflow-hidden animate-in fade-in slide-in-from-left-4 duration-300">
                        <h2 className="font-serif text-2xl font-medium tracking-tight">SVAS</h2>
                        <p className="text-[10px] text-brand-cream/60 font-bold uppercase tracking-[0.2em] -mt-1">Allocation</p>
                    </div>
                )}
            </div>

            {/* ── Navigation ───────────────────────────────────────────────── */}
            <nav className="flex-1 py-6 px-3 flex flex-col gap-1 overflow-y-auto custom-scrollbar">
                {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                    <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                            `flex items-center gap-3 p-3 rounded-lg transition-all duration-200 group ${
                                isActive 
                                    ? "bg-brand-gold text-brand-brown shadow-md font-bold" 
                                    : "text-brand-cream/70 hover:bg-white/5 hover:text-white"
                            } ${collapsed ? "justify-center" : ""}`
                        }
                    >
                        <Icon size={20} className="flex-shrink-0" />
                        {!collapsed && (
                            <span className="text-sm font-sans tracking-wide truncate animate-in fade-in duration-300">
                                {label}
                            </span>
                        )}
                        {!collapsed && (
                            <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity">
                                <ChevronRight size={14} />
                            </div>
                        )}
                    </NavLink>
                ))}
            </nav>

            {/* ── User Profile ─────────────────────────────────────────────── */}
            <div className={`p-4 border-t border-white/10 bg-black/10 ${collapsed ? "items-center" : ""}`}>
                <div className={`flex items-center gap-3 ${collapsed ? "flex-col" : "mb-4"}`}>
                    <div className="relative">
                        {photoURL ? (
                            <img src={photoURL} alt="" className="w-10 h-10 rounded-full border-2 border-brand-gold shadow-sm" />
                        ) : (
                            <div className="w-10 h-10 rounded-full bg-brand-gold text-brand-brown flex items-center justify-center font-bold text-sm border-2 border-white/20">
                                {initials}
                            </div>
                        )}
                        <div className="absolute bottom-0 right-0 w-3 h-3 bg-brand-mint-dark border-2 border-brand-brown rounded-full" />
                    </div>
                    {!collapsed && (
                        <div className="flex-1 overflow-hidden">
                            <p className="text-sm font-bold truncate">{displayName || "Volunteer"}</p>
                            <p className="text-[10px] text-brand-cream/50 truncate uppercase tracking-wider">{role || "User"}</p>
                        </div>
                    )}
                </div>

                {!collapsed && (
                    <button
                        onClick={handleLogout}
                        disabled={loggingOut}
                        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-white/5 hover:bg-red-500/10 text-brand-cream/60 hover:text-red-400 border border-white/10 hover:border-red-400/30 transition-all text-xs font-bold uppercase tracking-widest"
                    >
                        <LogOut size={14} />
                        <span>{loggingOut ? "Signing out..." : "Sign Out"}</span>
                    </button>
                )}
                {collapsed && (
                    <button 
                        onClick={handleLogout}
                        className="p-2 rounded-lg text-brand-cream/60 hover:text-red-400 transition-colors"
                        title="Logout"
                    >
                        <LogOut size={18} />
                    </button>
                )}
            </div>

            {/* ── Collapse Toggle ─────────────────────────────────────────── */}
            <button
                onClick={onToggle}
                className="absolute -right-3 top-24 w-6 h-6 rounded-full bg-brand-gold text-brand-brown flex items-center justify-center shadow-lg hover:scale-110 transition-transform z-50 border border-brand-brown"
            >
                {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
        </aside>
    );
}
