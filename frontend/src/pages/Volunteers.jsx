import { useState, useEffect } from "react";
import { 
    Search, 
    Filter, 
    MoreVertical, 
    Mail, 
    Phone, 
    MapPin, 
    Star,
    Award,
    Calendar,
    ChevronRight,
    SearchX
} from "lucide-react";
import { Card, SkeletonLoader } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import * as api from "../services/api";
import toast from "react-hot-toast";

export default function Volunteers() {
    const [volunteers, setVolunteers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [filterSkill, setFilterSkill] = useState("All Skills");

    useEffect(() => {
        fetchVolunteers();
    }, []);

    const fetchVolunteers = async () => {
        try {
            // Mocking for UI demonstration
            setTimeout(() => {
                setVolunteers([
                    { id: "v1", name: "Dr. Aris Ahmed", email: "aris@medical.org", phone: "+91 98765 43210", location: "Andheri", skills: ["Medical", "First Aid"], rating: 4.9, tasks: 24, status: "Available", avatar: "AA" },
                    { id: "v2", name: "Sarah Jenkins", email: "sarah.j@ngo.com", phone: "+91 91234 56789", location: "Bandra", skills: ["Nursing", "Logistics"], rating: 4.7, tasks: 18, status: "Busy", avatar: "SJ" },
                    { id: "v3", name: "Michael Chen", email: "m.chen@vol.in", phone: "+91 99887 76655", location: "Dharavi", skills: ["Language", "Driving"], rating: 4.5, tasks: 32, status: "Available", avatar: "MC" },
                    { id: "v4", name: "Priya Sharma", email: "priya@social.org", phone: "+91 88776 65544", location: "Powai", skills: ["Education", "Mentoring"], rating: 4.8, tasks: 12, status: "Away", avatar: "PS" },
                    { id: "v5", name: "Rahul Varma", email: "rahul.v@gmail.com", phone: "+91 77665 54433", location: "Kurla", skills: ["General Labor", "Logistics"], rating: 4.3, tasks: 8, status: "Available", avatar: "RV" },
                    { id: "v6", name: "Anita Desai", email: "anita.d@foundation.in", phone: "+91 66554 43322", location: "Colaba", skills: ["Coordination", "Admin"], rating: 4.6, tasks: 15, status: "Available", avatar: "AD" },
                ]);
                setLoading(false);
            }, 500);
        } catch (err) {
            toast.error("Failed to load volunteers.");
        }
    };

    const filteredVolunteers = volunteers.filter(v => {
        const matchesSearch = v.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                              v.location.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesSkill = filterSkill === "All Skills" || v.skills.includes(filterSkill);
        return matchesSearch && matchesSkill;
    });

    return (
        <div className="volunteers-page">
            <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
                <div>
                    <h1 className="page-title">Volunteer Management</h1>
                    <p className="page-subtitle">Manage and track your community's active workforce</p>
                </div>
                <button className="btn btn-primary btn-sm">
                    Register New Volunteer
                </button>
            </div>

            {/* ── Filters Bar ────────────────────────────────────────────────── */}
            <div className="card" style={{ padding: "0.75rem 1rem", marginBottom: "1.5rem", display: "flex", gap: "1rem", alignItems: "center" }}>
                <div style={{ position: "relative", flex: 1 }}>
                    <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--color-gray-400)" }} />
                    <input 
                        className="form-input" 
                        placeholder="Search volunteers by name or location..." 
                        style={{ paddingLeft: "2.5rem" }}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <select 
                    className="form-select" 
                    style={{ width: 200 }}
                    value={filterSkill}
                    onChange={(e) => setFilterSkill(e.target.value)}
                >
                    <option>All Skills</option>
                    <option>Medical</option>
                    <option>Logistics</option>
                    <option>Education</option>
                    <option>General Labor</option>
                </select>
                <button className="btn btn-outline btn-icon"><Filter size={18} /></button>
            </div>

            {/* ── Volunteers Grid ────────────────────────────────────────────── */}
            {loading ? (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.25rem" }}>
                    <SkeletonLoader count={6} variant="card" />
                </div>
            ) : filteredVolunteers.length === 0 ? (
                <div style={{ padding: "4rem", textAlign: "center", color: "var(--color-gray-400)" }}>
                    <SearchX size={48} style={{ marginBottom: "1rem" }} />
                    <h3>No volunteers found matching your criteria.</h3>
                </div>
            ) : (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))", gap: "1.25rem" }}>
                    {filteredVolunteers.map(v => (
                        <Card key={v.id} hover className="card-hover">
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                                    <div className="avatar avatar-lg">{v.avatar}</div>
                                    <div>
                                        <h4 style={{ fontSize: "1rem", fontWeight: 700 }}>{v.name}</h4>
                                        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.75rem", color: "var(--color-gray-500)" }}>
                                            <MapPin size={10} /> {v.location}
                                        </div>
                                    </div>
                                </div>
                                <Badge variant={v.status.toLowerCase() === 'available' ? 'success' : v.status.toLowerCase() === 'busy' ? 'danger' : 'warning'}>
                                    {v.status}
                                </Badge>
                            </div>

                            <div style={{ margin: "1.25rem 0", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                                <div style={{ background: "var(--color-gray-50)", padding: "0.5rem", borderRadius: "0.5rem", textAlign: "center" }}>
                                    <div style={{ fontSize: "0.65rem", color: "var(--color-gray-400)", textTransform: "uppercase" }}>Rating</div>
                                    <div style={{ fontWeight: 700, fontSize: "1rem", display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
                                        {v.rating} <Star size={14} fill="var(--color-accent)" color="var(--color-accent)" />
                                    </div>
                                </div>
                                <div style={{ background: "var(--color-gray-50)", padding: "0.5rem", borderRadius: "0.5rem", textAlign: "center" }}>
                                    <div style={{ fontSize: "0.65rem", color: "var(--color-gray-400)", textTransform: "uppercase" }}>Missions</div>
                                    <div style={{ fontWeight: 700, fontSize: "1rem", display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
                                        {v.tasks} <Award size={14} color="var(--color-primary)" />
                                    </div>
                                </div>
                            </div>

                            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: "1.25rem", height: 48, overflow: "hidden" }}>
                                {v.skills.map(s => <span key={s} style={{ fontSize: "0.7rem", background: "var(--color-brand-cream-50)", padding: "2px 10px", borderRadius: 99, border: "1px solid var(--color-brand-cream)", color: "var(--color-brand-brown)" }}>{s}</span>)}
                            </div>

                            <div style={{ display: "flex", gap: "0.5rem", paddingTop: "1rem", borderTop: "1px solid var(--color-gray-100)" }}>
                                <button className="btn btn-outline btn-sm" style={{ flex: 1 }} onClick={() => toast(`Contacting ${v.name}...`)}>
                                    <Mail size={14} /> Email
                                </button>
                                <button className="btn btn-ghost btn-icon btn-sm"><ChevronRight size={18} /></button>
                            </div>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
