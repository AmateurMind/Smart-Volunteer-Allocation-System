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
    SearchX,
    UserPlus,
    ShieldCheck,
    Briefcase,
    Sparkles
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
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10">
                <div>
                    <h1 className="font-serif text-4xl text-brand-brown-dark mb-2">Volunteer Registry</h1>
                    <p className="text-muted-foreground font-medium flex items-center gap-2 uppercase tracking-widest text-[10px]">
                        <Briefcase size={14} className="text-brand-gold" />
                        Manage and track your community's active workforce
                    </p>
                </div>
                <button className="bg-brand-brown text-white px-6 py-3 rounded-xl font-bold text-xs flex items-center gap-2 shadow-lg shadow-brand-brown/20 hover:bg-brand-brown-dark hover:-translate-y-0.5 transition-all">
                    <UserPlus size={16} />
                    Register New Volunteer
                </button>
            </div>

            {/* Filters Bar */}
            <div className="bg-white rounded-2xl p-4 mb-8 border border-brand-cream/30 shadow-sm flex flex-col md:flex-row gap-4">
                <div className="relative flex-1">
                    <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-brand-brown/30" />
                    <input 
                        type="text"
                        placeholder="Search by name or location..." 
                        className="w-full pl-12 pr-4 py-3 rounded-xl bg-brand-cream-50 border-none text-sm font-medium focus:ring-2 focus:ring-brand-gold/20 transition-all outline-none"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
                <div className="flex gap-4">
                    <select 
                        className="px-4 py-3 rounded-xl bg-brand-cream-50 border-none text-sm font-bold text-brand-brown/60 focus:ring-2 focus:ring-brand-gold/20 outline-none min-w-[160px]"
                        value={filterSkill}
                        onChange={(e) => setFilterSkill(e.target.value)}
                    >
                        <option>All Skills</option>
                        <option>Medical</option>
                        <option>Logistics</option>
                        <option>Education</option>
                        <option>General Labor</option>
                    </select>
                    <button className="p-3 rounded-xl bg-brand-cream-50 text-brand-brown/40 hover:text-brand-brown hover:bg-brand-cream-100 transition-colors border-none">
                        <Filter size={18} />
                    </button>
                </div>
            </div>

            {/* Volunteers Grid */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    <SkeletonLoader count={6} variant="card" />
                </div>
            ) : filteredVolunteers.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-20 h-20 rounded-full bg-brand-cream-50 flex items-center justify-center text-brand-brown/10 mb-6">
                        <SearchX size={40} />
                    </div>
                    <h3 className="text-xl font-bold text-brand-brown/40">No volunteers found</h3>
                    <p className="text-sm text-brand-brown/30 mt-2">Try adjusting your search or filters.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                    {filteredVolunteers.map(v => (
                        <div key={v.id} className="group bg-white rounded-3xl p-6 border border-brand-cream/30 hover:border-brand-gold/30 hover:shadow-xl hover:shadow-brand-brown/5 transition-all duration-300 relative overflow-hidden">
                            <div className="flex justify-between items-start mb-6">
                                <div className="flex gap-4 items-center">
                                    <div className="w-14 h-14 rounded-2xl bg-brand-cream-50 text-brand-brown font-bold flex items-center justify-center text-lg shadow-sm group-hover:bg-brand-gold group-hover:text-brand-brown transition-colors">
                                        {v.avatar}
                                    </div>
                                    <div>
                                        <h4 className="font-bold text-brand-brown-dark text-lg truncate max-w-[150px]">{v.name}</h4>
                                        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-medium">
                                            <MapPin size={12} className="text-brand-gold" />
                                            {v.location}
                                        </div>
                                    </div>
                                </div>
                                <Badge variant={v.status.toLowerCase() === 'available' ? 'success' : v.status.toLowerCase() === 'busy' ? 'danger' : 'warning'} className="text-[10px] font-bold uppercase px-2 py-0.5">
                                    {v.status}
                                </Badge>
                            </div>

                            <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="bg-brand-cream-50/50 p-3 rounded-2xl border border-brand-cream/20">
                                    <p className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-widest mb-1 text-center">Rating</p>
                                    <div className="flex items-center justify-center gap-1.5 text-brand-gold font-bold">
                                        <Star size={14} fill="currentColor" />
                                        <span>{v.rating}</span>
                                    </div>
                                </div>
                                <div className="bg-brand-cream-50/50 p-3 rounded-2xl border border-brand-cream/20">
                                    <p className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-widest mb-1 text-center">Missions</p>
                                    <div className="flex items-center justify-center gap-1.5 text-brand-brown font-bold">
                                        <Award size={14} className="text-brand-gold" />
                                        <span>{v.tasks}</span>
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-wrap gap-1.5 mb-8 h-12 overflow-hidden content-start">
                                {v.skills.map(s => (
                                    <span key={s} className="px-3 py-1 rounded-full bg-brand-cream-50 text-[10px] font-bold text-brand-brown/60 uppercase tracking-tight border border-brand-cream/20">
                                        {s}
                                    </span>
                                ))}
                            </div>

                            <div className="flex gap-2 pt-4 border-t border-brand-cream/20">
                                <button className="flex-1 py-2.5 rounded-xl border border-brand-cream text-brand-brown text-[11px] font-bold hover:bg-brand-cream-50 transition-colors flex items-center justify-center gap-2">
                                    <Mail size={14} className="text-brand-gold" />
                                    Email
                                </button>
                                <button className="flex-1 py-2.5 rounded-xl border border-brand-cream text-brand-brown text-[11px] font-bold hover:bg-brand-cream-50 transition-colors flex items-center justify-center gap-2">
                                    <Phone size={14} className="text-brand-gold" />
                                    Call
                                </button>
                                <button className="w-10 h-10 rounded-xl bg-brand-cream-50 flex items-center justify-center text-brand-brown/40 hover:text-brand-gold transition-colors">
                                    <ChevronRight size={18} />
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
