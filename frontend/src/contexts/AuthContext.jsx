import { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
    signInWithEmailAndPassword,
    signInWithPopup,
    signOut,
    onAuthStateChanged,
    updateProfile,
} from "firebase/auth";
import { doc, getDoc, setDoc, serverTimestamp } from "firebase/firestore";
import { auth, db, googleProvider, getFCMToken } from "../services/firebase";
import { updateFcmToken, deleteFcmToken } from "../services/api";
import toast from "react-hot-toast";

// ─────────────────────────────────────────────────────────────────────────────
// Context creation
// ─────────────────────────────────────────────────────────────────────────────

const AuthContext = createContext(null);

// ─────────────────────────────────────────────────────────────────────────────
// Provider
// ─────────────────────────────────────────────────────────────────────────────

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);           // Firebase User object
    const [userProfile, setUserProfile] = useState(null); // Firestore user document
    const [loading, setLoading] = useState(true);     // initial auth state check

    // ── Fetch / create the Firestore user profile ─────────────────────────────
    const fetchUserProfile = useCallback(async (firebaseUser) => {
        if (!firebaseUser) {
            setUserProfile(null);
            return;
        }

        try {
            const userDocRef = doc(db, "users", firebaseUser.uid);
            const userSnap = await getDoc(userDocRef);

            if (userSnap.exists()) {
                const profileData = { id: userSnap.id, ...userSnap.data() };
                setUserProfile(profileData);
            } else {
                // First login – create a minimal user document
                const newProfile = {
                    uid: firebaseUser.uid,
                    email: firebaseUser.email || "",
                    name: firebaseUser.displayName || firebaseUser.email?.split("@")[0] || "User",
                    role: "VOLUNTEER",
                    profile_image_url: firebaseUser.photoURL || null,
                    phone: firebaseUser.phoneNumber || null,
                    is_active: true,
                    created_at: serverTimestamp(),
                    updated_at: serverTimestamp(),
                };

                await setDoc(userDocRef, newProfile);
                setUserProfile({ id: firebaseUser.uid, ...newProfile });
            }
        } catch (err) {
            console.error("[AuthContext] Failed to fetch user profile:", err);
            // Use a fallback profile derived from the Firebase user object
            setUserProfile({
                uid: firebaseUser.uid,
                email: firebaseUser.email || "",
                name: firebaseUser.displayName || "User",
                role: "VOLUNTEER",
                is_active: true,
            });
        }
    }, []);

    // ── Register FCM token with the backend ───────────────────────────────────
    const registerFCMToken = useCallback(async () => {
        try {
            const token = await getFCMToken();
            if (token) {
                await updateFcmToken(token);
            }
        } catch (err) {
            // Non-critical – log and move on
            console.warn("[AuthContext] FCM token registration failed:", err.message);
        }
    }, []);

    // ── Auth state listener ───────────────────────────────────────────────────
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
            setUser(firebaseUser);

            if (firebaseUser) {
                await fetchUserProfile(firebaseUser);
                // Register FCM token after sign-in (non-blocking)
                registerFCMToken();
            } else {
                setUserProfile(null);
            }

            setLoading(false);
        });

        return unsubscribe; // cleanup on unmount
    }, [fetchUserProfile, registerFCMToken]);

    // ─────────────────────────────────────────────────────────────────────────
    // Auth actions
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * Sign in with email and password.
     * @param {string} email
     * @param {string} password
     * @returns {Promise<import("firebase/auth").UserCredential>}
     */
    const login = useCallback(async (email, password) => {
        try {
            const credential = await signInWithEmailAndPassword(auth, email, password);
            toast.success(`Welcome back, ${credential.user.displayName || email.split("@")[0]}!`);
            return credential;
        } catch (err) {
            const message = _authErrorMessage(err.code);
            toast.error(message);
            throw err;
        }
    }, []);

    /**
     * Sign in with Google OAuth popup.
     * @returns {Promise<import("firebase/auth").UserCredential>}
     */
    const loginWithGoogle = useCallback(async () => {
        try {
            const credential = await signInWithPopup(auth, googleProvider);
            const isNewUser = credential._tokenResponse?.isNewUser;

            if (isNewUser) {
                toast.success("Account created! Welcome to SVAS 🌟");
            } else {
                toast.success(`Welcome back, ${credential.user.displayName || "there"}!`);
            }

            return credential;
        } catch (err) {
            if (err.code === "auth/popup-closed-by-user") {
                // User dismissed the popup – not an error worth toasting
                return null;
            }
            const message = _authErrorMessage(err.code);
            toast.error(message);
            throw err;
        }
    }, []);

    /**
     * Sign the current user out.
     */
    const logout = useCallback(async () => {
        try {
            // Unregister FCM token so stale notifications aren't sent
            await deleteFcmToken().catch(() => {});
            await signOut(auth);
            setUser(null);
            setUserProfile(null);
            toast.success("Signed out successfully.");
        } catch (err) {
            console.error("[AuthContext] Logout failed:", err);
            toast.error("Failed to sign out. Please try again.");
            throw err;
        }
    }, []);

    /**
     * Refresh the Firestore user profile (e.g. after a role change).
     */
    const refreshProfile = useCallback(async () => {
        if (user) {
            await fetchUserProfile(user);
        }
    }, [user, fetchUserProfile]);

    /**
     * Update the display name on both Firebase Auth and Firestore.
     * @param {string} newName
     */
    const updateDisplayName = useCallback(async (newName) => {
        if (!user) return;
        try {
            await updateProfile(user, { displayName: newName });
            const userDocRef = doc(db, "users", user.uid);
            await setDoc(userDocRef, { name: newName, updated_at: serverTimestamp() }, { merge: true });
            setUserProfile((prev) => prev ? { ...prev, name: newName } : prev);
            toast.success("Display name updated.");
        } catch (err) {
            toast.error("Failed to update name.");
            throw err;
        }
    }, [user]);

    // ─────────────────────────────────────────────────────────────────────────
    // Computed role helpers
    // ─────────────────────────────────────────────────────────────────────────

    const role = userProfile?.role?.toUpperCase() || "VOLUNTEER";

    const isAdmin = role === "ADMIN";
    const isCoordinator = role === "COORDINATOR" || role === "ADMIN";
    const isVolunteer = true; // all authenticated users have at minimum volunteer access

    // ─────────────────────────────────────────────────────────────────────────
    // Context value
    // ─────────────────────────────────────────────────────────────────────────

    const value = {
        // State
        user,
        userProfile,
        loading,

        // Actions
        login,
        loginWithGoogle,
        logout,
        refreshProfile,
        updateDisplayName,

        // Role helpers
        role,
        isAdmin,
        isCoordinator,
        isVolunteer,

        // Convenience
        isAuthenticated: !!user,
        displayName: user?.displayName || userProfile?.name || "User",
        email: user?.email || "",
        photoURL: user?.photoURL || userProfile?.profile_image_url || null,
        uid: user?.uid || null,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Hook
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Access the authentication context.
 *
 * @returns {{
 *   user: import("firebase/auth").User|null,
 *   userProfile: Object|null,
 *   loading: boolean,
 *   login: Function,
 *   loginWithGoogle: Function,
 *   logout: Function,
 *   refreshProfile: Function,
 *   updateDisplayName: Function,
 *   role: string,
 *   isAdmin: boolean,
 *   isCoordinator: boolean,
 *   isVolunteer: boolean,
 *   isAuthenticated: boolean,
 *   displayName: string,
 *   email: string,
 *   photoURL: string|null,
 *   uid: string|null,
 * }}
 */
export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an <AuthProvider>.");
    }
    return context;
}

// ─────────────────────────────────────────────────────────────────────────────
// Private helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Convert a Firebase Auth error code into a user-friendly message.
 * @param {string} code  Firebase error code (e.g. "auth/wrong-password")
 * @returns {string}
 */
function _authErrorMessage(code) {
    const messages = {
        "auth/user-not-found":          "No account found with this email address.",
        "auth/wrong-password":          "Incorrect password. Please try again.",
        "auth/invalid-email":           "Invalid email address format.",
        "auth/user-disabled":           "This account has been disabled.",
        "auth/email-already-in-use":    "An account with this email already exists.",
        "auth/weak-password":           "Password must be at least 6 characters.",
        "auth/too-many-requests":       "Too many failed attempts. Please try again later.",
        "auth/network-request-failed":  "Network error. Check your internet connection.",
        "auth/popup-blocked":           "Popup was blocked. Allow popups for this site.",
        "auth/account-exists-with-different-credential":
            "An account already exists with a different sign-in method.",
        "auth/invalid-credential":      "Invalid credentials. Please try again.",
        "auth/operation-not-allowed":   "This sign-in method is not enabled.",
    };

    return messages[code] || `Authentication error (${code}). Please try again.`;
}

export default AuthContext;
