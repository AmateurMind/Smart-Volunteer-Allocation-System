import { useState, useEffect } from "react";
import { 
    Search, 
    Filter, 
    UserCheck, 
    MapPin, 
    Zap, 
    Star,
    CheckCircle2,
    X,
    ArrowRight
} from "lucide-react";
import { Card, SkeletonLoader, LoadingSpinner } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";
import * as api from "../services/api";
import toast from "react-hot-toast";

export default function Matching() {
    const [needs, setNeeds] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedNeed, setSelectedNeed] = useState(null);
    const [matches, setMatches] = useState([]);
    const [matchingLoading, setMatchingLoading] = useState(false);

    useEffect(() => {
        fetchNeeds();
    }, []);

    const fetchNeeds = async () => {
        try {
            // In a real app, this would be an API call
            // const res = await api.listNeeds({ status: "OPEN" });
            // setNeeds(res.needs);
            
            // Mocking for UI demonstration
            setTimeout(() => {
                setNeeds([
                    { id: "n1", title: "Emergency Food Distribution", category: "FOOD", urgency: "HIGH", location: "Andheri East", skills: ["Logistics", "Local Language"] },
                    { id: "n2", title: "Medical Camp Coordination", category: "HEALTH", urgency: "HIGH", location: "Govandi", skills: ["Medical", "Nursing"] },
                    { id: "n3", title: "Temporary Shelter Setup", category: "SHELTER", urgency: "MEDIUM", location: "Dharavi", skills: ["Carpentry", "Labor"] },
                    { id: "n4", title: "Post-Flood Cleanup", category: "OTHER", urgency: "LOW", location: "Kurla", skills: ["General Labor"] },
                ]);
                setLoading(false);
            }, 600);
        } catch (err) {
            toast.error("Failed to load open needs.");
        }
    };

    const findMatches = async (need) => {
        setSelectedNeed(need);
        setMatchingLoading(true);
        setMatches([]);

        try {
            // Simulate AI matching call
            // const res = await api.matchVolunteers(need.id);
            // setMatches(res.matches);

            setTimeout(() => {
                setMatches([
                    { id: "v1", name: "Dr. Aris Ahmed", score: 98, distance: "1.2km", skills: ["Medical", "First Aid"], rating: 4.9, avatar: "AA" },
                    { id: "v2", name: "Sarah Jenkins", score: 92, distance: "2.5km", skills: ["Nursing", "Logistics"], rating: 4.7, avatar: "SJ" },
                    { id: "v3", name: "Michael Chen", score: 85, distance: "0.8km", skills: ["Local Language", "Driving"], rating: 4.5, avatar: "MC" },
                ]);
                setMatchingLoading(false);
            }, 1200);
        } catch (err) {
            toast.error("Matching engine failed.");
            setMatchingLoading(false);
        }
    };

    const handleAssign = async (volunteer) => {
        const loadingToast = toast.loading(`Assigning ${volunteer.name}...`);
        try {
            // await api.assignVolunteer(selectedNeed.id, volunteer.id);
            setTimeout(() => {
                toast.success(`${volunteer.name} has been assigned and notified!`, { id: loadingToast });
                setNeeds(prev => prev.filter(n => n.id !== selectedNeed.id));
                setSelectedNeed(null);
            }, 1000);
        } catch (err) {
            toast.error("Assignment failed.", { id: loadingToast });
        }
    };

    return (
        <div className="matching-page">
            <div className="page-header">
                <h1 className="page-title">Smart Volunteer Matching</h1>
                <p className="page-subtitle">AI-ranked volunteer recommendations based on proximity and expertise</p>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem", alignItems: "start" }}>
                
                {/* Left Side: Open Needs List */}
                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                        <h3 style={{ fontSize: "1rem", fontWeight: 700 }}>Open Needs requiring matching</h3>
                        <div style={{ display: "flex", gap: "0.5rem" }}>
                            <button className="btn btn-ghost btn-sm"><Filter size={14} /> Filter</button>
                        </div>
                    </div>

                    {loading ? (
                        <SkeletonLoader count={4} variant="card" />
                    ) : (
                        needs.map(need => (
                            <Card 
                                key={need.id} 
                                hover 
                                onClick={() => findMatches(need)}
                                style={{ 
                                    borderLeft: `4px solid ${selectedNeed?.id === need.id ? 'var(--color-primary)' : 'transparent'}`,
                                    background: selectedNeed?.id === need.id ? 'var(--color-brand-cream-50)' : '#fff'
                                }}
                            >
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                                    <div>
                                        <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                                            <Badge variant={need.category.toLowerCase()}>{need.category}</Badge>
                                            <Badge variant={need.urgency.toLowerCase()}>{need.urgency}</Badge>
                                        </div>
                                        <h4 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--color-gray-900)" }}>{need.title}</h4>
                                        <div style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.8rem", color: "var(--color-gray-500)", marginTop: 4 }}>
                                            <MapPin size={12} /> {need.location}
                                        </div>
                                    </div>
                                    <button className="btn btn-primary btn-sm">
                                        <Zap size={14} /> Match
                                    </button>
                                </div>
                            </Card>
                        ))
                    )}
                </div>

                {/* Right Side: Matching Results */}
                <div style={{ position: "sticky", top: "1.5rem" }}>
                    {!selectedNeed ? (
                        <div style={{ 
                            height: 400, 
                            display: "flex", 
                            flexDirection: "column", 
                            alignItems: "center", 
                            justifyContent: "center",
                            background: "rgba(255,255,255,0.4)",
                            border: "2px dashed var(--color-gray-200)",
                            borderRadius: "var(--radius-card)",
                            textAlign: "center",
                            padding: "2rem"
                        }}>
                            <div style={{ color: "var(--color-gray-300)", marginBottom: "1rem" }}>
                                <UserCheck size={64} strokeWidth={1} />
                            </div>
                            <h3 style={{ color: "var(--color-gray-500)", fontWeight: 600 }}>Select a Need to match</h3>
                            <p style={{ color: "var(--color-gray-400)", fontSize: "0.85rem", marginTop: 8 }}>
                                Our AI engine will rank the best volunteers nearby.
                            </p>
                        </div>
                    ) : (
                        <Card>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
                                <h3 style={{ fontSize: "1.1rem", fontWeight: 700 }}>AI Recommendations</h3>
                                <button className="btn btn-ghost btn-icon" onClick={() => setSelectedNeed(null)}><X size={18} /></button>
                            </div>

                            <div style={{ background: "var(--color-primary-50)", padding: "1rem", borderRadius: "0.5rem", marginBottom: "1.5rem", border: "1px solid var(--color-primary-100)" }}>
                                <div style={{ fontSize: "0.7rem", color: "var(--color-primary-dark)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>Targeting</div>
                                <div style={{ fontWeight: 600, marginTop: 4 }}>{selectedNeed.title}</div>
                                <div style={{ display: "flex", gap: 4, marginTop: 8 }}>
                                    {selectedNeed.skills.map(s => <span key={s} style={{ fontSize: "0.7rem", color: "var(--color-primary-dark)", background: "rgba(164,114,81,0.1)", padding: "2px 8px", borderRadius: 4 }}>{s}</span>)}
                                </div>
                            </div>

                            {matchingLoading ? (
                                <div style={{ padding: "2rem", textAlign: "center" }}>
                                    <LoadingSpinner size={32} label="Ranking volunteers..." center />
                                </div>
                            ) : (
                                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                    {matches.map((v, i) => (
                                        <div key={v.id} style={{ 
                                            padding: "1rem", 
                                            borderRadius: "0.75rem", 
                                            background: i === 0 ? "linear-gradient(90deg, #fff 0%, var(--color-brand-mint-50) 100%)" : "#fff",
                                            border: i === 0 ? "2px solid var(--color-success)" : "1px solid var(--color-gray-100)",
                                            boxShadow: i === 0 ? "0 4px 12px rgba(76, 175, 125, 0.15)" : "none",
                                            position: "relative",
                                            overflow: "hidden"
                                        }}>
                                            {i === 0 && (
                                                <div style={{ 
                                                    position: "absolute", top: 0, right: 0, 
                                                    background: "var(--color-success)", color: "#fff", 
                                                    fontSize: "0.6rem", fontWeight: 800, padding: "2px 10px",
                                                    borderBottomLeftRadius: 8
                                                }}>
                                                    BEST MATCH
                                                </div>
                                            )}
                                            
                                            <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
                                                <div className="avatar avatar-md">{v.avatar}</div>
                                                <div style={{ flex: 1 }}>
                                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                                        <span style={{ fontWeight: 700, fontSize: "0.95rem" }}>{v.name}</span>
                                                        <span style={{ color: "var(--color-success)", fontWeight: 800, fontSize: "0.9rem" }}>{v.score}%</span>
                                                    </div>
                                                    <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", marginTop: 4 }}>
                                                        <span style={{ fontSize: "0.75rem", color: "var(--color-gray-500)", display: "flex", alignItems: "center", gap: 3 }}>
                                                            <MapPin size={10} /> {v.distance}
                                                        </span>
                                                        <span style={{ fontSize: "0.75rem", color: "var(--color-accent-dark)", display: "flex", alignItems: "center", gap: 3, fontWeight: 600 }}>
                                                            <Star size={10} fill="currentColor" /> {v.rating}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                            <div style={{ display: "flex", gap: 6, margin: "10px 0" }}>
                                                {v.skills.map(s => <span key={s} style={{ fontSize: "0.65rem", background: "var(--color-gray-100)", padding: "2px 8px", borderRadius: 4, color: "var(--color-gray-600)" }}>{s}</span>)}
                                            </div>

                                            <button className={`btn btn-sm ${i === 0 ? 'btn-primary' : 'btn-outline'}`} style={{ width: "100%" }} onClick={() => handleAssign(v)}>
                                                Assign Mission
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </Card>
                    )}
                </div>
            </div>

            <style>{`
                .matching-page {
                    animation: slideIn 0.4s ease-out;
                }
                @keyframes slideIn {
                    from { opacity: 0; transform: translateX(20px); }
                    to { opacity: 1; transform: translateX(0); }
                }
            `}</style>
        </div>
    );
}
