import { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Eye, EyeOff, Heart, Mail, Lock, AlertCircle } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { LoadingSpinner } from "../components/ui/StatCard";

// ── Google logo SVG ───────────────────────────────────────────────────────────
function GoogleLogo() {
    return (
        <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
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
        <div style={{
            background: "rgba(255,255,255,0.12)",
            backdropFilter: "blur(8px)",
            border: "1px solid rgba(255,255,255,0.2)",
            borderRadius: "0.875rem",
            padding: "0.875rem 1.25rem",
            textAlign: "center",
            minWidth: 100,
        }}>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: "#fff", lineHeight: 1 }}>
                {value}
            </div>
            <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.75)", marginTop: 4, letterSpacing: "0.03em" }}>
                {label}
            </div>
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Login Page
// ─────────────────────────────────────────────────────────────────────────────

export default function Login() {
    const navigate   = useNavigate();
    const location   = useLocation();
    const { login, loginWithGoogle, isAuthenticated, loading: authLoading } = useAuth();

    const from = location.state?.from?.pathname || "/dashboard";

    // Form state
    const [email,       setEmail]       = useState("");
    const [password,    setPassword]    = useState("");
    const [showPass,    setShowPass]    = useState(false);
    const [error,       setError]       = useState("");
    const [isLoading,   setIsLoading]   = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);

    // Redirect if already authenticated
    useEffect(() => {
        if (!authLoading && isAuthenticated) {
            navigate(from, { replace: true });
        }
    }, [isAuthenticated, authLoading, navigate, from]);

    if (authLoading) {
        return (
            <div style={{
                minHeight: "100svh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "var(--color-surface)",
            }}>
                <LoadingSpinner size={32} label="Checking session…" />
            </div>
        );
    }

    // ── Handlers ──────────────────────────────────────────────────────────────

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
            // error toast is already shown by AuthContext; set inline msg too
            setError(err.message?.replace("Firebase: ", "").replace(/ \(auth\/.*\)\.?/, "") || "Login failed.");
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
        } catch (err) {
            setError("Google sign-in failed. Please try again.");
        } finally {
            setGoogleLoading(false);
        }
    };

    // ── Render ────────────────────────────────────────────────────────────────

    return (
        <div style={{
            minHeight: "100svh",
            display:   "flex",
            background: "var(--color-surface)",
        }}>
            {/* ── Left hero panel ──────────────────────────────────────────── */}
            <div
                className="hero-gradient"
                style={{
                    flex:           "0 0 48%",
                    display:        "flex",
                    flexDirection:  "column",
                    alignItems:     "center",
                    justifyContent: "center",
                    padding:        "3rem 3.5rem",
                    position:       "relative",
                    overflow:       "hidden",
                }}
            >
                {/* Background decoration circles */}
                {[
                    { size: 320, top: "-80px", left: "-80px", opacity: 0.08 },
                    { size: 220, bottom: "60px", right: "-40px", opacity: 0.1 },
                    { size: 140, top: "55%", left: "20%", opacity: 0.06 },
                ].map((c, i) => (
                    <div key={i} style={{
                        position:     "absolute",
                        width:        c.size,
                        height:       c.size,
                        borderRadius: "50%",
                        background:   "rgba(255,255,255," + c.opacity + ")",
                        top:          c.top,
                        bottom:       c.bottom,
                        left:         c.left,
                        right:        c.right,
                        pointerEvents: "none",
                    }} />
                ))}

                {/* Logo + brand */}
                <div style={{
                    display:    "flex",
                    alignItems: "center",
                    gap:        "0.875rem",
                    marginBottom: "2.5rem",
                    alignSelf:  "flex-start",
                }}>
                    <div style={{
                        width:          48,
                        height:         48,
                        borderRadius:   "0.875rem",
                        background:     "rgba(255,255,255,0.2)",
                        backdropFilter: "blur(8px)",
                        display:        "flex",
                        alignItems:     "center",
                        justifyContent: "center",
                        border:         "1px solid rgba(255,255,255,0.3)",
                    }}>
                        <Heart size={24} color="#fff" strokeWidth={2.5} />
                    </div>
                    <div>
                        <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "#fff", lineHeight: 1.1 }}>
                            SVAS
                        </div>
                        <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.7)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                            Smart Volunteer Allocation
                        </div>
                    </div>
                </div>

                {/* Main headline */}
                <div style={{ alignSelf: "flex-start", marginBottom: "2rem" }}>
                    <h1 style={{
                        fontSize:      "2.25rem",
                        fontWeight:    800,
                        color:         "#fff",
                        lineHeight:    1.2,
                        margin:        0,
                        letterSpacing: "-0.02em",
                    }}>
                        Empowering Communities Through
                    </h1>
                    <h1 style={{
                        fontSize:      "2.25rem",
                        fontWeight:    800,
                        color:         "var(--color-brand-cream)",
                        lineHeight:    1.2,
                        margin:        "0.25rem 0 0",
                        letterSpacing: "-0.02em",
                    }}>
                        Smart Volunteerism
                    </h1>
                    <p style={{
                        fontSize:   "1rem",
                        color:      "rgba(255,255,255,0.78)",
                        marginTop:  "1rem",
                        lineHeight: 1.7,
                        maxWidth:   460,
                    }}>
                        AI-powered need detection, intelligent volunteer matching,
                        and real-time decision dashboards — all in one platform.
                    </p>
                </div>

                {/* Stats row */}
                <div style={{
                    display:  "flex",
                    gap:      "0.875rem",
                    flexWrap: "wrap",
                    alignSelf: "flex-start",
                }}>
                    <HeroStat value="10x"  label="Faster Matching"    />
                    <HeroStat value="95%"  label="Task Completion"    />
                    <HeroStat value="500+" label="Active Volunteers"  />
                </div>

                {/* Feature pills */}
                <div style={{
                    display:    "flex",
                    flexWrap:   "wrap",
                    gap:        "0.5rem",
                    marginTop:  "2rem",
                    alignSelf:  "flex-start",
                }}>
                    {["Gemini AI", "Firebase", "Real-time Dashboard", "FCM Alerts", "BigQuery Analytics"].map((f) => (
                        <span key={f} style={{
                            fontSize:       "0.72rem",
                            fontWeight:     500,
                            color:          "rgba(255,255,255,0.85)",
                            background:     "rgba(255,255,255,0.12)",
                            border:         "1px solid rgba(255,255,255,0.2)",
                            borderRadius:   "999px",
                            padding:        "0.25rem 0.75rem",
                            whiteSpace:     "nowrap",
                            backdropFilter: "blur(4px)",
                        }}>
                            {f}
                        </span>
                    ))}
                </div>
            </div>

            {/* ── Right login panel ─────────────────────────────────────────── */}
            <div style={{
                flex:           "1 1 52%",
                display:        "flex",
                alignItems:     "center",
                justifyContent: "center",
                padding:        "2rem 1.5rem",
                overflowY:      "auto",
            }}>
                <div style={{ width: "100%", maxWidth: 420 }}>

                    {/* Heading */}
                    <div style={{ marginBottom: "2rem" }}>
                        <h2 style={{
                            fontSize:      "1.75rem",
                            fontWeight:    700,
                            color:         "var(--color-gray-900)",
                            margin:        0,
                            letterSpacing: "-0.01em",
                        }}>
                            Sign in to SVAS
                        </h2>
                        <p style={{
                            fontSize:   "0.9rem",
                            color:      "var(--color-gray-500)",
                            marginTop:  "0.375rem",
                        }}>
                            Manage volunteers and community needs
                        </p>
                    </div>

                    {/* Google sign-in button */}
                    <button
                        type="button"
                        onClick={handleGoogleLogin}
                        disabled={isLoading || googleLoading}
                        style={{
                            display:        "flex",
                            alignItems:     "center",
                            justifyContent: "center",
                            gap:            "0.625rem",
                            width:          "100%",
                            padding:        "0.625rem 1.25rem",
                            borderRadius:   "0.625rem",
                            border:         "1.5px solid var(--color-gray-200)",
                            background:     "#fff",
                            fontSize:       "0.9375rem",
                            fontWeight:     500,
                            color:          "var(--color-gray-700)",
                            cursor:         isLoading || googleLoading ? "not-allowed" : "pointer",
                            opacity:        isLoading || googleLoading ? 0.65 : 1,
                            transition:     "all 150ms ease",
                            boxShadow:      "0 1px 3px rgba(0,0,0,0.06)",
                            marginBottom:   "1.5rem",
                        }}
                        onMouseEnter={(e) => { if (!isLoading && !googleLoading) e.currentTarget.style.borderColor = "var(--color-accent)"; }}
                        onMouseLeave={(e) => { e.currentTarget.style.borderColor = "var(--color-gray-200)"; }}
                    >
                        {googleLoading
                            ? <LoadingSpinner size={18} color="var(--color-primary)" />
                            : <GoogleLogo />
                        }
                        {googleLoading ? "Signing in…" : "Continue with Google"}
                    </button>

                    {/* Divider */}
                    <div style={{
                        display:    "flex",
                        alignItems: "center",
                        gap:        "0.875rem",
                        marginBottom: "1.5rem",
                    }}>
                        <div style={{ flex: 1, height: 1, background: "var(--color-gray-200)" }} />
                        <span style={{ fontSize: "0.8rem", color: "var(--color-gray-400)", whiteSpace: "nowrap" }}>
                            or sign in with email
                        </span>
                        <div style={{ flex: 1, height: 1, background: "var(--color-gray-200)" }} />
                    </div>

                    {/* Error message */}
                    {error && (
                        <div style={{
                            display:      "flex",
                            alignItems:   "flex-start",
                            gap:          "0.5rem",
                            background:   "var(--color-danger-50)",
                            border:       "1px solid var(--color-danger-100)",
                            borderRadius: "0.625rem",
                            padding:      "0.75rem 1rem",
                            marginBottom: "1.25rem",
                        }}>
                            <AlertCircle size={16} style={{ color: "var(--color-danger)", flexShrink: 0, marginTop: 1 }} />
                            <span style={{ fontSize: "0.875rem", color: "var(--color-danger)", lineHeight: 1.5 }}>
                                {error}
                            </span>
                        </div>
                    )}

                    {/* Email + password form */}
                    <form onSubmit={handleEmailLogin} style={{ display: "flex", flexDirection: "column", gap: "1.125rem" }}>

                        {/* Email */}
                        <div className="form-group" style={{ margin: 0 }}>
                            <label className="form-label" htmlFor="email">
                                Email Address
                            </label>
                            <div style={{ position: "relative" }}>
                                <Mail
                                    size={16}
                                    style={{
                                        position:  "absolute",
                                        left:      "0.875rem",
                                        top:       "50%",
                                        transform: "translateY(-50%)",
                                        color:     "var(--color-gray-400)",
                                        pointerEvents: "none",
                                    }}
                                />
                                <input
                                    id="email"
                                    type="email"
                                    className="form-input"
                                    placeholder="you@ngo.org"
                                    value={email}
                                    onChange={(e) => { setEmail(e.target.value); setError(""); }}
                                    autoComplete="email"
                                    disabled={isLoading || googleLoading}
                                    style={{ paddingLeft: "2.5rem" }}
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div className="form-group" style={{ margin: 0 }}>
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.375rem" }}>
                                <label className="form-label" htmlFor="password" style={{ margin: 0 }}>
                                    Password
                                </label>
                                <a
                                    href="#"
                                    style={{ fontSize: "0.8rem", color: "var(--color-primary)", fontWeight: 500 }}
                                    onClick={(e) => e.preventDefault()}
                                >
                                    Forgot password?
                                </a>
                            </div>
                            <div style={{ position: "relative" }}>
                                <Lock
                                    size={16}
                                    style={{
                                        position:  "absolute",
                                        left:      "0.875rem",
                                        top:       "50%",
                                        transform: "translateY(-50%)",
                                        color:     "var(--color-gray-400)",
                                        pointerEvents: "none",
                                    }}
                                />
                                <input
                                    id="password"
                                    type={showPass ? "text" : "password"}
                                    className="form-input"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => { setPassword(e.target.value); setError(""); }}
                                    autoComplete="current-password"
                                    disabled={isLoading || googleLoading}
                                    style={{ paddingLeft: "2.5rem", paddingRight: "2.75rem" }}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPass((s) => !s)}
                                    tabIndex={-1}
                                    style={{
                                        position:   "absolute",
                                        right:      "0.75rem",
                                        top:        "50%",
                                        transform:  "translateY(-50%)",
                                        background: "transparent",
                                        border:     "none",
                                        cursor:     "pointer",
                                        color:      "var(--color-gray-400)",
                                        padding:    "0.25rem",
                                        display:    "flex",
                                        alignItems: "center",
                                    }}
                                    aria-label={showPass ? "Hide password" : "Show password"}
                                >
                                    {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                                </button>
                            </div>
                        </div>

                        {/* Submit */}
                        <button
                            type="submit"
                            className="btn btn-primary btn-lg"
                            disabled={isLoading || googleLoading}
                            style={{ width: "100%", marginTop: "0.25rem" }}
                        >
                            {isLoading ? (
                                <>
                                    <LoadingSpinner size={18} color="#fff" />
                                    Signing in…
                                </>
                            ) : (
                                "Sign In"
                            )}
                        </button>
                    </form>

                    {/* Footer note */}
                    <p style={{
                        fontSize:   "0.8rem",
                        color:      "var(--color-gray-400)",
                        textAlign:  "center",
                        marginTop:  "1.75rem",
                        lineHeight: 1.6,
                    }}>
                        By signing in you agree to the SVAS platform terms.<br/>
                        Contact your NGO administrator to create an account.
                    </p>

                    {/* Dev helper */}
                    {import.meta.env.VITE_APP_ENV === "development" && (
                        <div style={{
                            marginTop:    "1.5rem",
                            padding:      "0.875rem",
                            background:   "var(--color-brand-cream-50)",
                            border:       "1px solid var(--color-brand-cream)",
                            borderRadius: "0.625rem",
                        }}>
                            <p style={{ fontSize: "0.72rem", color: "var(--color-gray-500)", margin: "0 0 0.5rem", fontWeight: 600 }}>
                                🛠 DEV MODE — Quick fill
                            </p>
                            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                                {[
                                    { label: "Admin",       email: "admin@svas.org",       pw: "admin123" },
                                    { label: "Coordinator", email: "coord@svas.org",        pw: "coord123" },
                                    { label: "Volunteer",   email: "volunteer@svas.org",    pw: "vol12345" },
                                ].map(({ label, email: e, pw }) => (
                                    <button
                                        key={label}
                                        type="button"
                                        className="btn btn-outline btn-sm"
                                        onClick={() => { setEmail(e); setPassword(pw); setError(""); }}
                                    >
                                        {label}
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
