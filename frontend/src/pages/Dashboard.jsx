import { useState, useEffect } from "react";
import { 
    AlertCircle, 
    Users, 
    CheckCircle2, 
    Clock, 
    TrendingUp, 
    MapPin,
    ArrowRight,
    Search,
    Filter,
    Calendar,
    ChevronRight
} from "lucide-react";
import { StatCard, Card, SkeletonLoader } from "../components/ui/StatCard";
import { Badge } from "../components/ui/Badge";

// We'll use Tailwind classes for layout and styling
export default function Dashboard() {
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState(null);

    useEffect(() => {
        const timer = setTimeout(() => {
            setStats({
                openNeeds: 124,
                activeVolunteers: 45,
                completedTasks: 892,
                avgResponseTime: "1.4h",
                trends: {
                    needs: { value: 12, direction: "up", label: "vs last month" },
                    volunteers: { value: 5, direction: "up", label: "vs last month" }
                }
            });
            setLoading(false);
        }, 800);
        return () => clearTimeout(timer);
    }, []);

    return (
        <div className="flex flex-col gap-8 animate-in fade-in duration-500">
            {/* ── Page Header ────────────────────────────────────────────────── */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 className="text-4xl font-serif text-brand-brown-dark leading-tight">
                        Operational Overview
                    </h1>
                    <p className="text-muted-foreground font-sans mt-1">
                        Real-time community needs and volunteer distribution
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button className="inline-flex items-center gap-2 px-4 py-2 rounded-md border border-brand-cream-dark bg-white text-sm font-medium text-brand-brown hover:bg-brand-cream-50 transition-colors shadow-sm">
                        <Calendar size={16} /> 
                        <span>Last 30 Days</span>
                    </button>
                    <button className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-brand-brown text-white text-sm font-medium hover:bg-brand-brown-dark transition-all shadow-md shadow-brand-brown/20">
                        <PlusIcon size={16} />
                        <span>New Report</span>
                    </button>
                </div>
            </div>

            {/* ── KPI Row ────────────────────────────────────────────────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                <StatCard 
                    label="Open Needs" 
                    value={stats?.openNeeds} 
                    icon={<AlertCircle size={20} />} 
                    iconColor="#d9534f"
                    iconBg="#fef2f2"
                    trend={stats?.trends.needs}
                    loading={loading}
                    className="border-none shadow-sm ring-1 ring-brand-cream/50"
                />
                <StatCard 
                    label="Active Volunteers" 
                    value={stats?.activeVolunteers} 
                    icon={<Users size={20} />} 
                    iconColor="var(--color-brand-brown)"
                    iconBg="var(--color-brand-brown-50)"
                    trend={stats?.trends.volunteers}
                    loading={loading}
                    className="border-none shadow-sm ring-1 ring-brand-cream/50"
                />
                <StatCard 
                    label="Completed Tasks" 
                    value={stats?.completedTasks} 
                    icon={<CheckCircle2 size={20} />} 
                    iconColor="#4caf7d"
                    iconBg="#f0fdf4"
                    loading={loading}
                    className="border-none shadow-sm ring-1 ring-brand-cream/50"
                />
                <StatCard 
                    label="Avg. Response" 
                    value={stats?.avgResponseTime} 
                    icon={<Clock size={20} />} 
                    iconColor="var(--color-brand-gold-dark)"
                    iconBg="var(--color-brand-gold-50)"
                    loading={loading}
                    className="border-none shadow-sm ring-1 ring-brand-cream/50"
                />
            </div>

            {/* ── Main Dashboard Grid ─────────────────────────────────────────── */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                
                {/* Left Column: Heatmap & Recent Needs (8 cols) */}
                <div className="lg:col-span-8 flex flex-col gap-8">
                    
                    {/* Heatmap Card */}
                    <div className="bg-white rounded-xl shadow-sm ring-1 ring-brand-cream/50 overflow-hidden">
                        <div className="p-6 border-b border-brand-cream/30 flex items-center justify-between">
                            <div>
                                <h3 className="text-xl font-serif text-brand-brown-dark">Needs Distribution Heatmap</h3>
                                <p className="text-xs text-muted-foreground mt-0.5">Geographical hotspots for urgent community requests</p>
                            </div>
                            <div className="flex items-center gap-2 px-2 py-1 bg-brand-mint/30 rounded-full">
                                <div className="w-1.5 h-1.5 rounded-full bg-brand-mint-dark animate-pulse" />
                                <span className="text-[10px] font-bold text-brand-mint-dark uppercase tracking-wider">Live</span>
                            </div>
                        </div>
                        <div className="h-[400px] relative bg-brand-brown-50/50">
                            {/* Simulated map background */}
                            <div className="absolute inset-0 opacity-20 pointer-events-none" 
                                style={{ backgroundImage: 'radial-gradient(circle at 2px 2px, var(--color-brand-brown) 1px, transparent 0)', backgroundSize: '32px 32px' }} 
                            />
                            
                            {/* Hotspots */}
                            {[
                                { t: "25%", l: "30%", s: "w-24 h-24", c: "bg-red-500" },
                                { t: "60%", l: "55%", s: "w-32 h-32", c: "bg-brand-gold" },
                                { t: "40%", l: "70%", s: "w-20 h-20", c: "bg-red-600" },
                                { t: "75%", l: "20%", s: "w-28 h-28", c: "bg-brand-mint-dark" },
                            ].map((h, i) => (
                                <div key={i} className={`absolute ${h.s} rounded-full blur-[40px] opacity-40 animate-pulse`} 
                                    style={{ top: h.t, left: h.l, backgroundColor: i % 2 === 0 ? '#d9534f' : '#dd9e59' }} 
                                />
                            ))}

                            <div className="absolute bottom-6 right-6 p-4 bg-white/80 backdrop-blur-md rounded-lg shadow-lg border border-brand-cream/50 max-w-[200px]">
                                <h4 className="text-xs font-bold text-brand-brown-dark mb-2">HOTSPOT LEGEND</h4>
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-[#d9534f]" />
                                        <span className="text-[10px] text-muted-foreground font-medium">Critical (Medical/Shelter)</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-[#dd9e59]" />
                                        <span className="text-[10px] text-muted-foreground font-medium">High (Food/Water)</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Recent Needs Table */}
                    <div className="bg-white rounded-xl shadow-sm ring-1 ring-brand-cream/50 overflow-hidden">
                        <div className="p-6 border-b border-brand-cream/30 flex items-center justify-between">
                            <h3 className="text-xl font-serif text-brand-brown-dark">Recent Urgent Needs</h3>
                            <button className="text-sm font-medium text-brand-brown hover:text-brand-gold flex items-center gap-1 transition-colors">
                                View all reports <ChevronRight size={16} />
                            </button>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse">
                                <thead className="bg-brand-cream-50/50">
                                    <tr>
                                        <th className="px-6 py-4 text-[10px] font-bold text-brand-brown-dark/50 uppercase tracking-widest">Time</th>
                                        <th className="px-6 py-4 text-[10px] font-bold text-brand-brown-dark/50 uppercase tracking-widest">Need Details</th>
                                        <th className="px-6 py-4 text-[10px] font-bold text-brand-brown-dark/50 uppercase tracking-widest">Category</th>
                                        <th className="px-6 py-4 text-[10px] font-bold text-brand-brown-dark/50 uppercase tracking-widest">Urgency</th>
                                        <th className="px-6 py-4 text-[10px] font-bold text-brand-brown-dark/50 uppercase tracking-widest">Location</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-brand-cream/10">
                                    {[
                                        { id: 1, time: "12m ago", title: "Flood assistance - 20 families", cat: "SHELTER", urg: "HIGH", loc: "Dharavi, Sector 3" },
                                        { id: 2, time: "45m ago", title: "Medical supplies for clinic", cat: "HEALTH", urg: "MEDIUM", loc: "Govandi West" },
                                        { id: 3, time: "2h ago", title: "Food packets needed", cat: "FOOD", urg: "HIGH", loc: "Mankhurd" },
                                        { id: 4, time: "4h ago", title: "Textbooks for community school", cat: "EDUCATION", urg: "LOW", loc: "Kurla East" },
                                    ].map(n => (
                                        <tr key={n.id} className="hover:bg-brand-cream-50/30 transition-colors cursor-pointer">
                                            <td className="px-6 py-4 text-xs text-muted-foreground">{n.time}</td>
                                            <td className="px-6 py-4 font-semibold text-brand-brown-dark text-sm">{n.title}</td>
                                            <td className="px-6 py-4">
                                                <Badge variant={n.cat.toLowerCase()} className="bg-opacity-10">{n.cat}</Badge>
                                            </td>
                                            <td className="px-6 py-4">
                                                <Badge variant={n.urg.toLowerCase()}>{n.urg}</Badge>
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                                                    <MapPin size={12} className="text-brand-gold" />
                                                    {n.loc}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* Right Column: Analytics & Quick Actions (4 cols) */}
                <div className="lg:col-span-4 flex flex-col gap-8">
                    
                    {/* Distribution Card */}
                    <div className="bg-white rounded-xl shadow-sm ring-1 ring-brand-cream/50 p-6">
                        <h3 className="text-lg font-serif text-brand-brown-dark mb-6">Volunteer Distribution</h3>
                        <div className="flex flex-col items-center">
                            <div className="relative w-48 h-48 mb-6">
                                <svg viewBox="0 0 36 36" className="w-full h-full transform -rotate-90">
                                    <circle cx="18" cy="18" r="15.915" fill="transparent" stroke="var(--color-brand-cream-50)" strokeWidth="3" />
                                    <circle cx="18" cy="18" r="15.915" fill="transparent" stroke="var(--color-brand-brown)" strokeWidth="3" strokeDasharray="40 60" />
                                    <circle cx="18" cy="18" r="15.915" fill="transparent" stroke="var(--color-brand-gold)" strokeWidth="3" strokeDasharray="30 70" strokeDashoffset="-40" />
                                    <circle cx="18" cy="18" r="15.915" fill="transparent" stroke="var(--color-brand-mint-dark)" strokeWidth="3" strokeDasharray="30 70" strokeDashoffset="-70" />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-3xl font-bold text-brand-brown-dark">45</span>
                                    <span className="text-[10px] text-muted-foreground font-bold tracking-widest">VOLUNTEERS</span>
                                </div>
                            </div>
                            <div className="w-full space-y-3">
                                <div className="flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-brand-brown" />
                                        <span className="text-muted-foreground font-medium">Field Operations</span>
                                    </div>
                                    <span className="font-bold text-brand-brown-dark">18</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-brand-gold" />
                                        <span className="text-muted-foreground font-medium">Medical Assistance</span>
                                    </div>
                                    <span className="font-bold text-brand-brown-dark">12</span>
                                </div>
                                <div className="flex items-center justify-between text-xs">
                                    <div className="flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full bg-brand-mint-dark" />
                                        <span className="text-muted-foreground font-medium">Education Support</span>
                                    </div>
                                    <span className="font-bold text-brand-brown-dark">15</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Quick Missions */}
                    <div className="bg-brand-brown rounded-xl shadow-lg p-6 text-white overflow-hidden relative group">
                        <div className="absolute top-[-20px] right-[-20px] w-32 h-32 bg-white/10 rounded-full blur-2xl group-hover:bg-white/20 transition-all" />
                        <h3 className="text-lg font-serif mb-4 relative z-10">Active Missions</h3>
                        <div className="space-y-4 relative z-10">
                            {[
                                { title: "Medical Camp Govandi", time: "Starts in 2h", urgency: "High" },
                                { title: "Food Distribution", time: "Ongoing", urgency: "High" }
                            ].map((m, i) => (
                                <div key={i} className="p-3 bg-white/10 backdrop-blur-md rounded-lg border border-white/10 hover:bg-white/20 transition-all cursor-pointer">
                                    <div className="flex justify-between items-start mb-1">
                                        <span className="text-xs font-bold">{m.title}</span>
                                        <div className="w-1.5 h-1.5 rounded-full bg-brand-gold animate-pulse" />
                                    </div>
                                    <div className="flex justify-between items-center text-[10px] text-white/70">
                                        <span>{m.time}</span>
                                        <span className="px-1.5 py-0.5 rounded bg-brand-gold/20 text-brand-gold font-bold">{m.urgency}</span>
                                    </div>
                                </div>
                            ))}
                            <button className="w-full py-2 bg-brand-gold text-white text-xs font-bold rounded-lg hover:bg-brand-gold-dark transition-colors shadow-lg shadow-black/10">
                                Manage Missions
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}

function PlusIcon({ size }) {
    return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
    );
}
