import axios from "axios";
import { auth } from "./firebase";
import toast from "react-hot-toast";

// ─────────────────────────────────────────────────────────────────────────────
// Axios Instance
// ─────────────────────────────────────────────────────────────────────────────

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
});

// ── Request Interceptor – attach Firebase ID token ────────────────────────────
api.interceptors.request.use(
    async (config) => {
        try {
            const user = auth.currentUser;
            if (user) {
                const token = await user.getIdToken();
                config.headers.Authorization = `Bearer ${token}`;
            }
        } catch (err) {
            console.warn("Could not attach auth token:", err.message);
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// ── Response Interceptor – global error handling ──────────────────────────────
api.interceptors.response.use(
    (response) => response,
    (error) => {
        const status = error.response?.status;
        const detail =
            error.response?.data?.detail ||
            error.response?.data?.message ||
            error.message;

        if (status === 401) {
            // Redirect to login on unauthorized
            if (window.location.pathname !== "/login") {
                toast.error("Session expired. Please sign in again.");
                window.location.href = "/login";
            }
        } else if (status === 403) {
            toast.error("Access denied. You don't have permission to do that.");
        } else if (status === 500) {
            toast.error("Server error. Please try again later.");
        } else if (status === 404) {
            // Let the caller handle 404s silently
        } else if (!error.response) {
            // Network error
            toast.error("Network error. Check your connection.");
        }

        return Promise.reject(error);
    }
);

// ─────────────────────────────────────────────────────────────────────────────
// Helper – extract data from response
// ─────────────────────────────────────────────────────────────────────────────

const data = (res) => res.data;

// ─────────────────────────────────────────────────────────────────────────────
// Upload Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Upload a CSV, JSON, text, or image file.
 * @param {FormData} formData – must contain `file` and/or `text_data`, `data_type`, `auto_analyze`
 */
export const uploadData = (formData) =>
    api
        .post("/upload-data", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        })
        .then(data);

/**
 * Get recent upload history.
 * @param {number} limit
 */
export const getUploadHistory = (limit = 20) =>
    api.get("/upload-data/history", { params: { limit } }).then(data);

/**
 * Get a single upload record by ID.
 * @param {string} uploadId
 */
export const getUpload = (uploadId) =>
    api.get(`/upload-data/${uploadId}`).then(data);

/**
 * Delete an upload record.
 * @param {string} uploadId
 */
export const deleteUpload = (uploadId) =>
    api.delete(`/upload-data/${uploadId}`).then(data);

// ─────────────────────────────────────────────────────────────────────────────
// Analysis Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Analyse a single text with Gemini AI.
 * @param {string} text
 * @param {string|null} uploadId
 * @param {boolean} saveAsNeed
 * @param {string|null} location
 * @param {number|null} latitude
 * @param {number|null} longitude
 */
export const analyzeText = (
    text,
    uploadId = null,
    saveAsNeed = true,
    location = null,
    latitude = null,
    longitude = null
) =>
    api
        .post("/analyze", {
            text,
            upload_id: uploadId,
            save_as_need: saveAsNeed,
            location,
            latitude,
            longitude,
        })
        .then(data);

/**
 * Batch-analyse multiple texts.
 * @param {string[]} texts
 * @param {boolean} saveAsNeeds
 * @param {string|null} uploadId
 */
export const analyzeBatch = (texts, saveAsNeeds = true, uploadId = null) =>
    api
        .post("/analyze/batch", {
            texts,
            save_as_needs: saveAsNeeds,
            upload_id: uploadId,
        })
        .then(data);

/**
 * Re-analyse an existing upload record.
 * @param {string} uploadId
 * @param {boolean} saveAsNeeds
 */
export const analyzeFromUpload = (uploadId, saveAsNeeds = true) =>
    api
        .post("/analyze/from-upload", {
            upload_id: uploadId,
            save_as_needs: saveAsNeeds,
        })
        .then(data);

/**
 * List all need records with optional filters.
 * @param {{ category?: string, urgency?: string, status?: string, limit?: number }} params
 */
export const listNeeds = (params = {}) =>
    api.get("/analyze/needs", { params }).then(data);

/**
 * Get a single need record.
 * @param {string} needId
 */
export const getNeed = (needId) =>
    api.get(`/analyze/needs/${needId}`).then(data);

/**
 * Delete (close) a need record.
 * @param {string} needId
 */
export const deleteNeed = (needId) =>
    api.delete(`/analyze/needs/${needId}`).then(data);

// ─────────────────────────────────────────────────────────────────────────────
// Matching & Assignment Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Find best volunteers for a need.
 * @param {string} needId
 * @param {number} topN
 * @param {number|null} maxDistanceKm
 * @param {boolean} includeAiExplanation
 */
export const matchVolunteers = (
    needId,
    topN = 5,
    maxDistanceKm = null,
    includeAiExplanation = false
) =>
    api
        .post("/match", {
            need_id: needId,
            top_n: topN,
            max_distance_km: maxDistanceKm,
            include_ai_explanation: includeAiExplanation,
        })
        .then(data);

/**
 * Manually assign a volunteer to a need.
 * @param {string} needId
 * @param {string} volunteerId
 * @param {string|null} notes
 * @param {string|null} dueDate ISO date string
 * @param {boolean} sendNotification
 */
export const assignVolunteer = (
    needId,
    volunteerId,
    notes = null,
    dueDate = null,
    sendNotification = true
) =>
    api
        .post("/match/assign", {
            need_id: needId,
            volunteer_id: volunteerId,
            notes,
            due_date: dueDate,
            send_notification: sendNotification,
        })
        .then(data);

/**
 * Auto-assign the best volunteer to a need.
 * @param {string} needId
 * @param {boolean} sendNotification
 */
export const autoAssign = (needId, sendNotification = true) =>
    api
        .post(`/match/auto-assign/${needId}`, null, {
            params: { send_notification: sendNotification },
        })
        .then(data);

/**
 * List tasks with optional filters.
 * @param {{ status?: string, volunteer_id?: string, need_id?: string, limit?: number }} params
 */
export const listTasks = (params = {}) =>
    api.get("/match/tasks", { params }).then(data);

/**
 * Get a single task record.
 * @param {string} taskId
 */
export const getTask = (taskId) =>
    api.get(`/match/tasks/${taskId}`).then(data);

/**
 * Update a task's lifecycle status.
 * @param {string} taskId
 * @param {string} status
 * @param {string|null} notes
 * @param {number|null} actualDurationHours
 * @param {number|null} volunteerRating
 */
export const updateTaskStatus = (
    taskId,
    status,
    notes = null,
    actualDurationHours = null,
    volunteerRating = null
) =>
    api
        .patch(`/match/tasks/${taskId}/status`, {
            status,
            notes,
            actual_duration_hours: actualDurationHours,
            volunteer_rating: volunteerRating,
        })
        .then(data);

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Get the full dashboard snapshot.
 */
export const getDashboard = () => api.get("/dashboard").then(data);

/**
 * Get the four headline KPI stats.
 */
export const getDashboardStats = () => api.get("/dashboard/stats").then(data);

/**
 * Get heatmap data for open needs.
 * @param {{ status?: string, category?: string }} params
 */
export const getHeatmapData = (params = {}) =>
    api.get("/dashboard/heatmap", { params }).then(data);

/**
 * Get recent activity feed.
 * @param {number} limit
 */
export const getRecentActivity = (limit = 10) =>
    api.get("/dashboard/recent-activity", { params: { limit } }).then(data);

/**
 * Get BigQuery analytics data.
 * @param {number} days
 */
export const getAnalytics = (days = 30) =>
    api.get("/dashboard/analytics", { params: { days } }).then(data);

/**
 * Get volunteer distribution data.
 */
export const getVolunteerDistribution = () =>
    api.get("/dashboard/volunteer-distribution").then(data);

// ─────────────────────────────────────────────────────────────────────────────
// Volunteer Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Register the current user as a volunteer.
 * @param {Object} volunteerData
 */
export const registerVolunteer = (volunteerData) =>
    api.post("/volunteer/register", volunteerData).then(data);

/**
 * List all volunteers with optional filters.
 * @param {{ page?: number, page_size?: number, skill?: string, available_only?: boolean, search?: string }} params
 */
export const getVolunteers = (params = {}) =>
    api.get("/volunteer/list", { params }).then(data);

/**
 * Get the current user's volunteer profile.
 */
export const getMyProfile = () => api.get("/volunteer/me").then(data);

/**
 * Get a volunteer profile by ID.
 * @param {string} volunteerId
 */
export const getVolunteer = (volunteerId) =>
    api.get(`/volunteer/${volunteerId}`).then(data);

/**
 * Update a volunteer profile.
 * @param {string} volunteerId
 * @param {Object} updateData
 */
export const updateVolunteer = (volunteerId, updateData) =>
    api.put(`/volunteer/${volunteerId}`, updateData).then(data);

/**
 * Get task history for a volunteer.
 * @param {string} volunteerId
 * @param {{ status?: string, limit?: number }} params
 */
export const getVolunteerTasks = (volunteerId, params = {}) =>
    api.get(`/volunteer/${volunteerId}/tasks`, { params }).then(data);

/**
 * Get performance stats for a volunteer.
 * @param {string} volunteerId
 */
export const getVolunteerStats = (volunteerId) =>
    api.get(`/volunteer/${volunteerId}/stats`).then(data);

/**
 * Toggle a volunteer's availability.
 * @param {string} volunteerId
 * @param {boolean} availability
 * @param {string|null} reason
 */
export const toggleAvailability = (volunteerId, availability, reason = null) =>
    api
        .patch(`/volunteer/${volunteerId}/availability`, { availability, reason })
        .then(data);

/**
 * Deactivate a volunteer (admin only).
 * @param {string} volunteerId
 */
export const deactivateVolunteer = (volunteerId) =>
    api.delete(`/volunteer/${volunteerId}`).then(data);

// ─────────────────────────────────────────────────────────────────────────────
// Notification Endpoints
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Send a notification to a specific volunteer.
 * @param {string} volunteerId
 * @param {string} title
 * @param {string} body
 * @param {string} notificationType
 * @param {Object} extraData
 */
export const sendNotification = (
    volunteerId,
    title,
    body,
    notificationType = "GENERAL",
    extraData = {}
) =>
    api
        .post("/notifications/send", {
            volunteer_id: volunteerId,
            title,
            body,
            notification_type: notificationType,
            extra_data: extraData,
        })
        .then(data);

/**
 * Broadcast an urgent need alert.
 * @param {string} needId
 * @param {string[]} targetRoles
 * @param {string|null} customMessage
 */
export const sendUrgentAlert = (
    needId,
    targetRoles = ["COORDINATOR", "VOLUNTEER"],
    customMessage = null
) =>
    api
        .post("/notifications/urgent", {
            need_id: needId,
            target_roles: targetRoles,
            custom_message: customMessage,
        })
        .then(data);

/**
 * Send a reminder for a task.
 * @param {string} taskId
 */
export const sendReminder = (taskId) =>
    api.post(`/notifications/reminder/${taskId}`).then(data);

/**
 * Broadcast a custom notification to all users of given roles.
 * @param {string} title
 * @param {string} body
 * @param {string[]} targetRoles
 * @param {string} notificationType
 * @param {Object} extraData
 */
export const broadcastNotification = (
    title,
    body,
    targetRoles = ["COORDINATOR", "VOLUNTEER"],
    notificationType = "BROADCAST",
    extraData = {}
) =>
    api
        .post("/notifications/broadcast", {
            title,
            body,
            target_roles: targetRoles,
            notification_type: notificationType,
            extra_data: extraData,
        })
        .then(data);

/**
 * Register or refresh the caller's FCM device token.
 * @param {string} fcmToken
 */
export const updateFcmToken = (fcmToken) =>
    api.put("/notifications/fcm-token", { fcm_token: fcmToken }).then(data);

/**
 * Unregister the caller's FCM device token (on logout).
 */
export const deleteFcmToken = () =>
    api.delete("/notifications/fcm-token").then(data);

/**
 * Check notification service health.
 */
export const getNotificationStatus = () =>
    api.get("/notifications/status").then(data);

// ─────────────────────────────────────────────────────────────────────────────
// Health / Meta
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Check the backend health.
 */
export const healthCheck = () => api.get("/health").then(data);

export default api;
