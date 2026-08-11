/**
 * gameService.js
 * Centralized service for making API calls to the RigCheck backend.
 */

// In development, Vite proxies API requests. In production, this would be an absolute URL.
const API_BASE_URL = "";

/**
 * Fetch a paginated list of lightweight game cards.
 * @param {number} limit
 * @param {number} offset
 * @returns {Promise<Array>} Array of game objects.
 */
export async function fetchGames(limit = 500, offset = 0) {
  try {
    const response = await fetch(`${API_BASE_URL}/games?limit=${limit}&offset=${offset}`);
    if (!response.ok) throw new Error("Failed to fetch games");
    return await response.json();
  } catch (error) {
    console.error("Error fetching games:", error);
    return [];
  }
}

/**
 * Fetch detailed metadata for a single game by its Steam App ID.
 * @param {number} appid
 * @returns {Promise<Object|null>} Detailed game object or null if not found.
 */
export async function fetchGame(appid) {
  try {
    const response = await fetch(`${API_BASE_URL}/games/${appid}`);
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error("Failed to fetch game details");
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching game ${appid}:`, error);
    return null;
  }
}

/**
 * Search for games by name (case-insensitive substring match).
 * @param {string} query
 * @param {number} limit
 * @returns {Promise<Array>} Array of matching game objects.
 */
export async function searchGames(query, limit = 50) {
  if (!query) return [];
  try {
    const response = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}&limit=${limit}`);
    if (!response.ok) throw new Error("Failed to search games");
    return await response.json();
  } catch (error) {
    console.error("Error searching games:", error);
    return [];
  }
}
