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
    ArrowRight,
    Target,
    ShieldCheck,
    Navigation,
    Trophy
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
        <div className="animate-in fade-in slide-in-from-right-4 duration-500">
            {/* Header */}
            <div className="mb-10">
                <h1 className="font-serif text-4xl text-brand-brown-dark mb-2">Smart Matching</h1>
                <p className="text-muted-foreground font-medium flex items-center gap-2 uppercase tracking-widest text-[10px]">
                    <Target size={14} className="text-brand-gold" />
                    AI-ranked volunteer recommendations based on proximity and expertise
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-start">
                
                {/* Left Side: Open Needs List */}
                <div className="space-y-6">
                    <div className="flex justify-between items-center px-1">
                        <h3 className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest">Active Community Needs</h3>
                        <div className="flex gap-2">
                            <button className="p-2 rounded-lg bg-brand-cream-50 text-brand-brown/40 hover:text-brand-brown hover:bg-brand-cream-100 transition-colors">
                                <Filter size={16} />
                            </button>
                            <button className="p-2 rounded-lg bg-brand-cream-50 text-brand-brown/40 hover:text-brand-brown hover:bg-brand-cream-100 transition-colors">
                                <Search size={16} />
                            </button>
                        </div>
                    </div>

                    <div className="space-y-4">
                        {loading ? (
                            <SkeletonLoader count={4} variant="card" />
                        ) : (
                            needs.map(need => (
                                <div 
                                    key={need.id} 
                                    onClick={() => findMatches(need)}
                                    className={`group cursor-pointer p-6 rounded-2xl bg-white border transition-all duration-300 hover:shadow-xl hover:shadow-brand-brown/5 ${
                                        selectedNeed?.id === need.id 
                                            ? "border-brand-gold ring-4 ring-brand-gold/10" 
                                            : "border-brand-cream/30 hover:border-brand-gold/50"
                                    }`}
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="space-y-3">
                                            <div className="flex gap-2">
                                                <Badge variant={need.category.toLowerCase()} className="text-[10px] font-bold uppercase">{need.category}</Badge>
                                                <Badge variant={need.urgency.toLowerCase()} className="text-[10px] font-bold uppercase">{need.urgency}</Badge>
                                            </div>
                                            <h4 className="font-bold text-brand-brown-dark group-hover:text-brand-gold transition-colors">{need.title}</h4>
                                            <div className="flex items-center gap-4">
                                                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-medium">
                                                    <MapPin size={12} className="text-brand-gold" />
                                                    {need.location}
                                                </div>
                                                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-medium">
                                                    <Target size={12} className="text-brand-gold" />
                                                    {need.skills.length} Required Skills
                                                </div>
                                            </div>
                                        </div>
                                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                                            selectedNeed?.id === need.id ? "bg-brand-brown text-white" : "bg-brand-cream-50 text-brand-brown/30 group-hover:bg-brand-gold group-hover:text-brand-brown"
                                        }`}>
                                            <Zap size={18} fill={selectedNeed?.id === need.id ? "currentColor" : "none"} />
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                        {!loading && needs.length === 0 && (
                            <div className="text-center py-12 bg-brand-cream/5 rounded-3xl border-2 border-dashed border-brand-cream/30">
                                <CheckCircle2 size={40} className="mx-auto text-brand-mint-dark mb-4 opacity-20" />
                                <p className="text-sm font-bold text-brand-brown/40">All needs are currently matched!</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right Side: Matching Results */}
                <div className="lg:sticky lg:top-24">
                    {!selectedNeed ? (
                        <div className="bg-brand-cream/5 border-2 border-dashed border-brand-cream/30 rounded-3xl p-12 flex flex-col items-center text-center justify-center min-h-[500px]">
                            <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center text-brand-brown/10 shadow-inner mb-6">
                                <UserCheck size={40} />
                            </div>
                            <h3 className="text-xl font-bold text-brand-brown/40">Ready to Match</h3>
                            <p className="text-sm text-brand-brown/30 mt-2 max-w-[280px]">
                                Select a community need from the list to find the best-fit volunteers nearby.
                            </p>
                        </div>
                    ) : (
                        <div className="bg-white rounded-3xl border border-brand-cream/30 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
                            <div className="bg-brand-brown p-8 text-white relative">
                                <button 
                                    onClick={() => setSelectedNeed(null)}
                                    className="absolute top-6 right-6 p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                                >
                                    <X size={16} />
                                </button>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-2 text-[10px] font-bold text-brand-gold uppercase tracking-[0.2em]">
                                        <Sparkles size={14} fill="currentColor" />
                                        AI Match Engine
                                    </div>
                                    <h3 className="text-2xl font-serif">{selectedNeed.title}</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {selectedNeed.skills.map(s => (
                                            <span key={s} className="px-2 py-1 rounded bg-white/10 text-[10px] font-bold text-brand-cream uppercase tracking-wider">{s}</span>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="p-8">
                                {matchingLoading ? (
                                    <div className="py-20 flex flex-col items-center gap-4 text-center">
                                        <LoadingSpinner size={40} color="var(--color-brand-brown)" />
                                        <p className="font-bold text-brand-brown-dark">Scanning volunteer database...</p>
                                        <p className="text-xs text-muted-foreground">Calculating proximity and skill alignment</p>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <div className="flex justify-between items-center mb-2 px-1">
                                            <h4 className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest">Recommended Volunteers</h4>
                                            <span className="text-[10px] font-bold text-brand-mint-dark bg-brand-mint/20 px-2 py-1 rounded-full">3 Matches Found</span>
                                        </div>
                                        
                                        {matches.map((v, i) => (
                                            <div 
                                                key={v.id} 
                                                className={`group p-5 rounded-2xl border transition-all duration-300 hover:-translate-y-1 ${
                                                    i === 0 
                                                        ? "bg-brand-mint/5 border-brand-mint ring-1 ring-brand-mint/50" 
                                                        : "bg-white border-brand-cream/30 hover:border-brand-gold/30 hover:shadow-lg"
                                                }`}
                                            >
                                                <div className="flex gap-4 items-center">
                                                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm shadow-sm ${
                                                        i === 0 ? "bg-brand-mint text-brand-mint-dark" : "bg-brand-cream-50 text-brand-brown"
                                                    }`}>
                                                        {v.avatar}
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex justify-between items-center mb-1">
                                                            <h5 className="font-bold text-brand-brown-dark truncate">{v.name}</h5>
                                                            <div className="flex items-center gap-1 text-brand-gold font-bold text-xs">
                                                                <Star size={12} fill="currentColor" />
                                                                {v.rating}
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-3">
                                                            <div className="flex items-center gap-1 text-[10px] text-muted-foreground font-bold">
                                                                <Navigation size={10} className="text-brand-brown/30" />
                                                                {v.distance}
                                                            </div>
                                                            <div className="flex items-center gap-1 text-[10px] text-brand-mint-dark font-bold">
                                                                <ShieldCheck size={10} />
                                                                {v.score}% Match
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>

                                                <div className="flex flex-wrap gap-1.5 my-4">
                                                    {v.skills.map(s => (
                                                        <span key={s} className="px-2 py-0.5 rounded bg-brand-cream-50 text-[9px] font-bold text-brand-brown/60 uppercase tracking-tighter border border-brand-cream/20">
                                                            {s}
                                                        </span>
                                                    ))}
                                                </div>

                                                <button 
                                                    onClick={() => handleAssign(v)}
                                                    className={`w-full py-3 rounded-xl font-bold text-xs transition-all flex items-center justify-center gap-2 ${
                                                        i === 0 
                                                            ? "bg-brand-brown text-white shadow-lg shadow-brand-brown/20 hover:bg-brand-brown-dark" 
                                                            : "bg-white border border-brand-cream hover:bg-brand-cream-50 text-brand-brown"
                                                    }`}
                                                >
                                                    {i === 0 && <Trophy size={14} className="text-brand-gold" />}
                                                    <span>Assign Mission</span>
                                                    <ArrowRight size={14} className={i === 0 ? "" : "opacity-30 group-hover:opacity-100 group-hover:translate-x-1 transition-all"} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
