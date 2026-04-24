// ─────────────────────────────────────────────────────────────────────────────
//  SVAS Frontend – Firebase Service Initialisation
//  Initialises the Firebase app and exports: auth, db (Firestore), messaging
// ─────────────────────────────────────────────────────────────────────────────

import { initializeApp, getApps, getApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  connectAuthEmulator,
} from "firebase/auth";
import {
  getFirestore,
  connectFirestoreEmulator,
} from "firebase/firestore";
import { getMessaging, getToken, onMessage } from "firebase/messaging";

// ── Firebase configuration (loaded from Vite env vars) ───────────────────────
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

// ── Initialise the Firebase app (idempotent – safe to import multiple times) ──
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();

// ── Firebase Authentication ───────────────────────────────────────────────────
export const auth = getAuth(app);

// Google OAuth provider with custom parameters
export const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({
  prompt: "select_account",
});

// ── Cloud Firestore ───────────────────────────────────────────────────────────
export const db = getFirestore(app);

// ── Firebase Cloud Messaging ──────────────────────────────────────────────────
// FCM requires a secure context (HTTPS or localhost) and browser support.
// We wrap it in a try/catch so the app works even without notification support.
let messaging = null;

try {
  if (
    typeof window !== "undefined" &&
    "Notification" in window &&
    "serviceWorker" in navigator
  ) {
    messaging = getMessaging(app);
  }
} catch (err) {
  console.warn(
    "[SVAS] Firebase Messaging could not be initialised:",
    err.message
  );
}

export { messaging };

// ── FCM token helper ──────────────────────────────────────────────────────────

/**
 * Request permission and retrieve the FCM device registration token.
 *
 * @returns {Promise<string|null>}  The FCM token string, or null if unavailable.
 */
export async function getFCMToken() {
  if (!messaging) {
    console.warn("[SVAS] Messaging is not initialised – cannot get FCM token.");
    return null;
  }

  const vapidKey = import.meta.env.VITE_FIREBASE_VAPID_KEY;

  if (!vapidKey || vapidKey === "your-vapid-key") {
    console.warn(
      "[SVAS] VITE_FIREBASE_VAPID_KEY is not configured. FCM token skipped."
    );
    return null;
  }

  try {
    // Request notification permission first
    const permission = await Notification.requestPermission();
    if (permission !== "granted") {
      console.info("[SVAS] Notification permission denied by user.");
      return null;
    }

    const token = await getToken(messaging, { vapidKey });
    if (token) {
      return token;
    }

    console.warn(
      "[SVAS] No registration token available. " +
        "Request permission to generate one."
    );
    return null;
  } catch (err) {
    console.error("[SVAS] Failed to retrieve FCM token:", err);
    return null;
  }
}

/**
 * Register a foreground message handler.
 * The callback receives the FCM message payload when a notification arrives
 * while the app tab is open (foreground state).
 *
 * @param {(payload: object) => void} callback
 * @returns {() => void}  Unsubscribe function.
 */
export function onForegroundMessage(callback) {
  if (!messaging) return () => {};
  return onMessage(messaging, callback);
}

// ── Emulator support (development only) ──────────────────────────────────────
if (
  import.meta.env.VITE_APP_ENV === "development" &&
  import.meta.env.VITE_USE_EMULATORS === "true"
) {
  try {
    connectAuthEmulator(auth, "http://localhost:9099", { disableWarnings: true });
    connectFirestoreEmulator(db, "localhost", 8080);
    console.info("[SVAS] Connected to Firebase Emulators.");
  } catch (err) {
    // Already connected – safe to ignore
  }
}

export default app;
