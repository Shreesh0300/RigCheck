/**
 * libraryService.js
 * Centralized service for User Game Library & Review API endpoints.
 */

export function getCsrfToken() {
  const match = document.cookie.match(new RegExp("(^| )rigcheck_csrf=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : "";
}

/**
 * Fetch games in the user's library, optionally filtered by category.
 * @param {string|null} category - 'favourite', 'want_to_play', 'already_played', or null for all
 * @returns {Promise<Array>} Array of library game records with metadata
 */
export async function fetchUserLibrary(category = null) {
  const url = category ? `/api/library?category=${encodeURIComponent(category)}` : "/api/library";
  const res = await fetch(url);
  if (!res.ok) {
    if (res.status === 401) return [];
    throw new Error("Failed to fetch user library");
  }
  const data = await res.json();
  return data.games || [];
}

/**
 * Fetch library status for a specific game.
 * @param {number} appid
 * @returns {Promise<Object>} Status object
 */
export async function fetchGameLibraryStatus(appid) {
  const res = await fetch(`/api/library/${appid}`);
  if (!res.ok) {
    if (res.status === 401) {
      return {
        appid,
        is_favourite: false,
        want_to_play: false,
        already_played: false,
        rating: null,
        review: null,
      };
    }
    throw new Error("Failed to fetch game status");
  }
  const data = await res.json();
  return data.state;
}

/**
 * Update library status flags for a game.
 * @param {number} appid
 * @param {Object} updates - { is_favourite?: boolean, want_to_play?: boolean, already_played?: boolean }
 * @param {string} [csrfToken]
 * @returns {Promise<Object>} Updated status
 */
export async function updateGameLibraryStatus(appid, updates, csrfToken = null) {
  const token = csrfToken || getCsrfToken();
  const res = await fetch(`/api/library/${appid}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
    body: JSON.stringify(updates),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update library status");
  }
  const data = await res.json();
  return data.state;
}

/**
 * Remove a game from a library category or reset all categories.
 * @param {number} appid
 * @param {string|null} category
 * @param {string} [csrfToken]
 * @returns {Promise<Object>} Updated status
 */
export async function removeGameLibraryCategory(appid, category = null, csrfToken = null) {
  const token = csrfToken || getCsrfToken();
  const url = category ? `/api/library/${appid}/${category}` : `/api/library/${appid}`;
  const res = await fetch(url, {
    method: "DELETE",
    headers: {
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to remove from library");
  }
  const data = await res.json();
  return data.state;
}

/**
 * Fetch public reviews and community rating for a game.
 * @param {number} appid
 * @returns {Promise<Object>} Review data { average_rating, total_ratings, total_reviews, reviews }
 */
export async function fetchGameReviews(appid) {
  const res = await fetch(`/api/games/${appid}/reviews`);
  if (!res.ok) {
    throw new Error("Failed to load reviews");
  }
  return await res.json();
}

/**
 * Submit or update a user rating and review.
 * @param {number} appid
 * @param {number} rating - 1 to 10
 * @param {string|null} comment
 * @param {string} [csrfToken]
 * @returns {Promise<Object>} Updated activity state
 */
export async function submitGameReview(appid, rating, comment = null, csrfToken = null) {
  const token = csrfToken || getCsrfToken();
  const res = await fetch(`/api/games/${appid}/review`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
    body: JSON.stringify({ rating, comment }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to submit review");
  }
  const data = await res.json();
  return data.state;
}

/**
 * Delete the active user's review for a game.
 * @param {number} appid
 * @param {string} [csrfToken]
 * @returns {Promise<Object>} Updated activity state
 */
export async function deleteGameReview(appid, csrfToken = null) {
  const token = csrfToken || getCsrfToken();
  const res = await fetch(`/api/games/${appid}/review`, {
    method: "DELETE",
    headers: {
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete review");
  }
  const data = await res.json();
  return data.state;
}

/**
 * Report an inappropriate public review.
 * @param {number} appid
 * @param {string} targetUserId
 * @param {string} [reason]
 * @param {string} [csrfToken]
 * @returns {Promise<Object>} Result
 */
export async function reportGameReview(appid, targetUserId, reason = null, csrfToken = null) {
  const token = csrfToken || getCsrfToken();
  const res = await fetch(`/api/games/${appid}/reviews/report`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-CSRF-Token": token } : {}),
    },
    body: JSON.stringify({ target_user_id: targetUserId, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to report review");
  }
  return await res.json();
}
