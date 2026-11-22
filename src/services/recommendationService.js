/**
 * recommendationService.js
 * Frontend service for RigCheck Personalized Recommendation Engine (FYP),
 * User Preferences, and Ask RigCheck AI Search History.
 */
import { getCsrfToken } from "./libraryService.js";

/**
 * Fetch personalized game recommendations.
 * @param {Object} options
 * @param {number} [options.limit=20]
 * @param {boolean} [options.refresh=false]
 * @returns {Promise<Object>} { success, feed_revision, is_cold_start, recommendations, already_played_recommendations, total_recommendations }
 */
export async function fetchPersonalizedRecommendations({ limit = 20, refresh = false } = {}) {
  const url = `/api/recommendations/personalized?limit=${encodeURIComponent(limit)}&refresh=${encodeURIComponent(refresh)}`;
  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 401) {
      return {
        authenticated: false,
        success: false,
        feed_revision: 0,
        is_cold_start: true,
        recommendations: [],
        already_played_recommendations: [],
      };
    }
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to load personalized recommendations");
  }
  const data = await res.json();
  return { ...data, authenticated: true };
}

/**
 * Fetch authenticated user's genre & interest preferences.
 * @returns {Promise<Object>} { preferred_genres, interests, onboarding_completed, feed_revision }
 */
export async function fetchUserPreferences() {
  const res = await fetch("/api/preferences");
  if (!res.ok) {
    if (res.status === 401) {
      return {
        preferred_genres: [],
        interests: [],
        onboarding_completed: false,
        feed_revision: 1,
      };
    }
    throw new Error("Failed to fetch preferences");
  }
  const data = await res.json();
  return data.preferences;
}

/**
 * Update user's genre and interest preferences.
 * @param {Object} prefs - { preferred_genres?: string[], interests?: string[], onboarding_completed?: boolean }
 * @returns {Promise<Object>} Updated preferences
 */
export async function updateUserPreferences(prefs) {
  const csrf = getCsrfToken();
  const res = await fetch("/api/preferences", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
    body: JSON.stringify(prefs),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update preferences");
  }
  const data = await res.json();
  return data.preferences;
}

/**
 * Fetch user's Ask RigCheck AI search history.
 * @param {number} [limit=50]
 * @returns {Promise<Array>} Array of AI query records
 */
export async function fetchAiHistory(limit = 50) {
  const res = await fetch(`/api/ai-history?limit=${encodeURIComponent(limit)}`);
  if (!res.ok) {
    if (res.status === 401) return [];
    throw new Error("Failed to fetch AI history");
  }
  const data = await res.json();
  return data.history || [];
}

/**
 * Delete a single AI search query from history.
 * @param {string} queryId
 * @returns {Promise<boolean>}
 */
export async function deleteAiHistoryItem(queryId) {
  const csrf = getCsrfToken();
  const res = await fetch(`/api/ai-history/${encodeURIComponent(queryId)}`, {
    method: "DELETE",
    headers: {
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete query record");
  }
  return true;
}

/**
 * Clear all AI search history records for the current user.
 * @returns {Promise<boolean>}
 */
export async function clearAllAiHistory() {
  const csrf = getCsrfToken();
  const res = await fetch("/api/ai-history", {
    method: "DELETE",
    headers: {
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to clear AI history");
  }
  return true;
}

/**
 * Log a user interaction with an AI recommended game.
 * @param {Object} interaction - { appid: number, action: string, query_id?: string }
 */
export async function logAiInteraction(interaction) {
  const csrf = getCsrfToken();
  try {
    await fetch("/api/ai-history/interaction", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      },
      body: JSON.stringify(interaction),
    });
  } catch (e) {
    // Non-blocking interaction telemetry
  }
}
