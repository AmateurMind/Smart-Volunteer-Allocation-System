import { lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { PageLoader } from "./components/ui/StatCard";
import Layout from "./components/Layout/Layout";

// ── Lazy load pages ─────────────────────────────────────────────────────────
const Login      = lazy(() => import("./pages/Login"));
const Dashboard  = lazy(() => import("./pages/Dashboard"));
const Analysis   = lazy(() => import("./pages/Analysis"));
const Matching   = lazy(() => import("./pages/Matching"));
const Volunteers = lazy(() => import("./pages/Volunteers"));

/**
 * Higher-order component to protect private routes.
 * Redirects to /login if the user is not authenticated.
 */
function ProtectedRoute({ children }) {
    const { isAuthenticated, loading } = useAuth();
    const location = useLocation();

    if (loading) return <PageLoader label="Verifying session…" />;

    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    return children;
}

export default function App() {
    return (
        <Suspense fallback={<PageLoader />}>
            <Routes>
                {/* Public routes */}
                <Route path="/login" element={<Login />} />

                {/* Protected app routes */}
                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <Layout />
                        </ProtectedRoute>
                    }
                >
                    <Route index element={<Navigate to="/dashboard" replace />} />
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="analysis"  element={<Analysis />} />
                    <Route path="matching"  element={<Matching />} />
                    <Route path="volunteers" element={<Volunteers />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
        </Suspense>
    );
}
