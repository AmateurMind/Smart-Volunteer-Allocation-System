import { useState, useRef, useEffect } from "react";
import { useLocation, Link } from "react-router-dom";
import { Bell, Search, ChevronDown, LogOut, User, Settings, Menu, X } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";

// ── Route → page title map ────────────────────────────────────────────────────
const PAGE_TITLES = {
    "/dashboard":  { title: "Dashboard",       subtitle: "Overview of community needs and volunteer activity" },
    "/analysis":   { title: "Need Analysis",   subtitle: "AI-powered community need categorisation" },
    "/volunteers": { title: "Volunteers",      subtitle: "Manage volunteer profiles and availability" },
    "/matching":   { title: "Smart Matching",  subtitle: "Match volunteers to community needs" },
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

    return (
        <header className="sticky top-0 z-40 w-full h-16 bg-white/80 backdrop-blur-md border-b border-brand-cream/30 px-6 flex items-center gap-4 shadow-sm shadow-brand-brown/5">
            {/* ── Sidebar toggle (mobile/desktop) ───────────────────────────── */}
            <button
                className="p-2 rounded-lg hover:bg-brand-cream-50 text-brand-brown-dark transition-colors lg:hidden"
                onClick={onToggleSidebar}
            >
                <Menu size={22} />
            </button>

            {/* ── Page Title ────────────────────────────────────────────────── */}
            <div className="flex-1 min-w-0">
                <h1 className="text-lg font-bold text-brand-brown-dark truncate font-sans leading-tight">
                    {pageInfo.title}
                </h1>
                <p className="text-[11px] text-muted-foreground truncate uppercase tracking-widest font-bold font-sans">
                    {pageInfo.subtitle}
                </p>
            </div>

            {/* ── Search Bar ────────────────────────────────────────────────── */}
            <div className={`hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-200 w-64 ${
                searchFocused 
                    ? "bg-white border-brand-gold ring-4 ring-brand-gold/10 shadow-sm" 
                    : "bg-brand-cream-50 border-brand-cream/50"
            }`}>
                <Search size={16} className={searchFocused ? "text-brand-gold" : "text-muted-foreground"} />
                <input
                    type="text"
                    placeholder="Search anything..."
                    className="bg-transparent border-none outline-none text-sm text-brand-brown-dark placeholder:text-muted-foreground w-full"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onFocus={() => setSearchFocused(true)}
                    onBlur={() => setSearchFocused(false)}
                />
            </div>

            {/* ── Notifications ─────────────────────────────────────────────── */}
            <button className="relative p-2 rounded-lg hover:bg-brand-cream-50 text-brand-brown transition-colors">
                <Bell size={20} />
                <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
            </button>

            {/* ── User Dropdown ──────────────────────────────────────────────── */}
            <div className="relative" ref={dropdownRef}>
                <button
                    onClick={() => setDropdownOpen(!dropdownOpen)}
                    className={`flex items-center gap-3 p-1.5 pr-3 rounded-xl transition-all ${
                        dropdownOpen ? "bg-brand-cream-50" : "hover:bg-brand-cream-50"
                    }`}
                >
                    <div className="relative">
                        {photoURL ? (
                            <img src={photoURL} alt="" className="w-8 h-8 rounded-lg object-cover ring-2 ring-brand-cream/50" />
                        ) : (
                            <div className="w-8 h-8 rounded-lg bg-brand-gold text-brand-brown flex items-center justify-center font-bold text-xs ring-2 ring-brand-cream/50">
                                {getInitials(displayName)}
                            </div>
                        )}
                    </div>
                    <div className="hidden lg:block text-left">
                        <p className="text-sm font-bold text-brand-brown-dark leading-none">{displayName || "User"}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5 uppercase tracking-tighter">{role || "Role"}</p>
                    </div>
                    <ChevronDown size={14} className={`text-muted-foreground transition-transform duration-200 ${dropdownOpen ? "rotate-180" : ""}`} />
                </button>

                {/* Dropdown Menu */}
                {dropdownOpen && (
                    <div className="absolute right-0 mt-3 w-56 bg-white rounded-xl shadow-2xl border border-brand-cream/30 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        <div className="p-4 bg-brand-cream-50 border-b border-brand-cream/30 text-center">
                            <p className="text-sm font-bold text-brand-brown-dark">{displayName}</p>
                            <p className="text-xs text-muted-foreground truncate">{email}</p>
                        </div>
                        <div className="p-2">
                            <Link to="/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-brand-brown-dark hover:bg-brand-cream-50 transition-colors">
                                <User size={16} className="text-brand-gold" />
                                <span>My Profile</span>
                            </Link>
                            <Link to="/settings" className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-brand-brown-dark hover:bg-brand-cream-50 transition-colors">
                                <Settings size={16} className="text-brand-gold" />
                                <span>Settings</span>
                            </Link>
                        </div>
                        <div className="p-2 border-t border-brand-cream/10 bg-gray-50/50">
                            <button 
                                onClick={logout}
                                className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-red-500 hover:bg-red-50 transition-colors font-medium"
                            >
                                <LogOut size={16} />
                                <span>Sign Out</span>
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </header>
    );
}
