import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Eye, EyeOff, Heart, Mail, Lock, AlertCircle, ArrowRight } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { LoadingSpinner } from "../components/ui/StatCard";

// ── Google logo SVG ───────────────────────────────────────────────────────────
function GoogleLogo() {
    return (
        <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </svg>
    );
}

// ── Stat pill shown on the hero side ─────────────────────────────────────────
function HeroStat({ value, label }) {
    return (
        <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl p-5 text-center min-w-[120px] transition-transform hover:scale-105 duration-300">
            <div className="text-2xl font-bold text-white leading-none">{value}</div>
            <div className="text-[10px] font-bold text-brand-cream/60 uppercase tracking-widest mt-2">{label}</div>
        </div>
    );
}

export default function Login() {
    const navigate   = useNavigate();
    const location   = useLocation();
    const { login, loginWithGoogle, isAuthenticated, loading: authLoading } = useAuth();

    const from = location.state?.from?.pathname || "/dashboard";

    const [email,       setEmail]       = useState("");
    const [password,    setPassword]    = useState("");
    const [showPass,    setShowPass]    = useState(false);
    const [error,       setError]       = useState("");
    const [isLoading,   setIsLoading]   = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);

    useEffect(() => {
        if (!authLoading && isAuthenticated) {
            navigate(from, { replace: true });
        }
    }, [isAuthenticated, authLoading, navigate, from]);

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-brand-cream-50">
                <LoadingSpinner size={40} label="Authenticating..." color="var(--color-brand-brown)" />
            </div>
        );
    }

    const handleEmailLogin = async (e) => {
        e.preventDefault();
        if (!email.trim() || !password) {
            setError("Please enter your email and password.");
            return;
        }
        setError("");
        setIsLoading(true);
        try {
            await login(email.trim(), password);
            navigate(from, { replace: true });
        } catch (err) {
            setError(getReadableAuthError(err));
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleLogin = async () => {
        setError("");
        setGoogleLoading(true);
        try {
            const cred = await loginWithGoogle();
            if (cred) navigate(from, { replace: true });
        } catch {
            setError("Google sign-in failed. Please try again.");
        } finally {
            setGoogleLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col lg:flex-row bg-white font-sans overflow-hidden">
            {/* ── Left hero panel ──────────────────────────────────────────── */}
            <div className="hidden lg:flex lg:w-5/12 bg-brand-brown relative flex-col justify-center p-12 overflow-hidden shadow-2xl">
                {/* Decorative Elements */}
                <div className="absolute top-0 left-0 w-96 h-96 bg-brand-gold/10 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />
                <div className="absolute bottom-0 right-0 w-64 h-64 bg-brand-mint/10 rounded-full blur-3xl translate-x-1/2 translate-y-1/2" />
                
                <div className="relative z-10 flex flex-col gap-10">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-2xl bg-brand-gold flex items-center justify-center shadow-lg shadow-black/20">
                            <Heart size={28} className="text-brand-brown" strokeWidth={2.5} />
                        </div>
                        <div>
                            <h2 className="font-serif text-3xl text-white">SVAS</h2>
                            <p className="text-[10px] text-brand-cream/50 font-bold uppercase tracking-[0.2em] -mt-1">Allocation System</p>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h1 className="font-serif text-5xl xl:text-6xl text-white leading-[1.1] tracking-tight">
                            Smart Decisions <br />
                            <span className="text-brand-gold italic">Empowering</span> <br />
                            Communities.
                        </h1>
                        <p className="text-brand-cream/70 text-lg max-w-md leading-relaxed">
                            AI-powered community need detection and intelligent volunteer matching. Bridge the gap between empathy and efficiency.
                        </p>
                    </div>

                    <div className="flex gap-4 flex-wrap">
                        <HeroStat value="10x" label="Faster" />
                        <HeroStat value="95%" label="Success" />
                        <HeroStat value="AI" label="Gemini 1.5" />
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {["Priority Detection", "Geo-Matching", "Real-time Stats", "Automated Workflows"].map((f) => (
                            <span key={f} className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-[10px] font-bold text-white/60 uppercase tracking-widest">
                                {f}
                            </span>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── Right login panel ─────────────────────────────────────────── */}
            <div className="flex-1 flex flex-col items-center justify-center p-8 lg:p-24 bg-brand-cream-50/30">
                <div className="w-full max-w-[440px] bg-white rounded-3xl p-8 lg:p-12 shadow-xl shadow-brand-brown/5 border border-brand-cream/20">
                    
                    <div className="mb-10 lg:hidden flex justify-center">
                        <div className="w-12 h-12 rounded-2xl bg-brand-brown flex items-center justify-center">
                            <Heart size={24} className="text-brand-gold" />
                        </div>
                    </div>

                    <div className="mb-10">
                        <h2 className="text-3xl font-bold text-brand-brown-dark tracking-tight">Welcome back</h2>
                        <p className="text-muted-foreground mt-2 font-medium">Please enter your details to sign in.</p>
                    </div>

                    <button
                        type="button"
                        onClick={handleGoogleLogin}
                        disabled={isLoading || googleLoading}
                        className="w-full flex items-center justify-center gap-3 py-3.5 px-4 rounded-xl border border-brand-cream/50 bg-white hover:bg-brand-cream-50 hover:border-brand-gold/30 transition-all duration-200 text-sm font-bold text-brand-brown-dark shadow-sm group"
                    >
                        {googleLoading ? <LoadingSpinner size={20} /> : <GoogleLogo />}
                        <span>Continue with Google</span>
                        <ArrowRight size={16} className="ml-auto opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                    </button>

                    <div className="my-8 flex items-center gap-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                        <div className="flex-1 h-[1px] bg-brand-cream/50" />
                        <span>or use email</span>
                        <div className="flex-1 h-[1px] bg-brand-cream/50" />
                    </div>

                    {error && (
                        <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-100 flex gap-3 animate-in fade-in slide-in-from-top-2">
                            <AlertCircle className="text-red-500 shrink-0" size={18} />
                            <p className="text-xs text-red-600 font-medium leading-relaxed">{error}</p>
                        </div>
                    )}

                    <form onSubmit={handleEmailLogin} className="space-y-5">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest ml-1">Email</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                                <input
                                    type="email"
                                    placeholder="your@email.com"
                                    className="w-full pl-12 pr-4 py-3.5 rounded-xl border border-brand-cream/50 focus:border-brand-gold focus:ring-4 focus:ring-brand-gold/10 transition-all outline-none text-sm font-medium"
                                    value={email}
                                    onChange={(e) => { setEmail(e.target.value); setError(""); }}
                                    disabled={isLoading || googleLoading}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center px-1">
                                <label className="text-xs font-bold text-brand-brown/60 uppercase tracking-widest">Password</label>
                                <button type="button" className="text-xs font-bold text-brand-gold hover:text-brand-gold-dark transition-colors">Forgot?</button>
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                                <input
                                    type={showPass ? "text" : "password"}
                                    placeholder="••••••••"
                                    className="w-full pl-12 pr-12 py-3.5 rounded-xl border border-brand-cream/50 focus:border-brand-gold focus:ring-4 focus:ring-brand-gold/10 transition-all outline-none text-sm font-medium"
                                    value={password}
                                    onChange={(e) => { setPassword(e.target.value); setError(""); }}
                                    disabled={isLoading || googleLoading}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPass(!showPass)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-brand-brown-dark transition-colors"
                                >
                                    {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading || googleLoading}
                            className="w-full py-4 rounded-xl bg-brand-brown text-white font-bold text-sm shadow-xl shadow-brand-brown/20 hover:bg-brand-brown-dark hover:-translate-y-0.5 transition-all active:translate-y-0 disabled:opacity-70 disabled:hover:translate-y-0 flex items-center justify-center gap-2"
                        >
                            {isLoading ? <LoadingSpinner size={20} color="white" /> : "Sign In"}
                        </button>
                    </form>

                    <p className="mt-10 text-center text-[11px] text-muted-foreground font-medium uppercase tracking-[0.05em] leading-relaxed">
                        By joining, you agree to our <span className="text-brand-brown-dark cursor-pointer underline">Terms</span> and <span className="text-brand-brown-dark cursor-pointer underline">Privacy Policy</span>.
                    </p>

                    {import.meta.env.VITE_APP_ENV === "development" && (
                        <div className="mt-10 pt-8 border-t border-brand-cream/20">
                            <p className="text-[10px] font-bold text-brand-brown/40 uppercase tracking-widest mb-4">Quick Sign-in (Dev)</p>
                            <div className="flex gap-2 flex-wrap">
                                {[
                                    { label: "Admin", email: "admin@svas.org", pw: "admin123" },
                                    { label: "Coordinator", email: "coordinator1@svas.org", pw: "coord12345" },
                                    { label: "Volunteer", email: "volunteer@svas.org", pw: "vol12345" },
                                ].map((u) => (
                                    <button
                                        key={u.label}
                                        onClick={() => { setEmail(u.email); setPassword(u.pw); setError(""); }}
                                        className="px-3 py-1.5 rounded-lg bg-brand-cream-50 text-[10px] font-bold text-brand-brown-dark hover:bg-brand-gold/10 transition-colors"
                                    >
                                        {u.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function getReadableAuthError(err) {
    const code = err?.code || "";
    const map = {
        "auth/user-not-found": "No account found for this email.",
        "auth/wrong-password": "Incorrect password.",
        "auth/invalid-credential": "Invalid email or password.",
        "auth/invalid-email": "Invalid email format.",
        "auth/user-disabled": "This account is disabled.",
        "auth/operation-not-allowed": "Email/password sign-in is disabled in Firebase Auth.",
        "auth/too-many-requests": "Too many attempts. Try again later.",
        "auth/network-request-failed": "Network request failed. Check internet and try again.",
    };

    if (map[code]) return map[code];
    return err?.message?.replace("Firebase: ", "").replace(/ \(auth\/.*\)\.?/, "") || "Login failed.";
}
