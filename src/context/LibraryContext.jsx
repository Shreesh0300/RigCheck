import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import {
  fetchUserLibrary,
  updateGameLibraryStatus,
  getCsrfToken,
} from "../services/libraryService.js";

const LibraryContext = createContext(null);

export function LibraryProvider({ children, isLoggedIn, onRequireLogin }) {
  // Map of appid -> { is_favourite, want_to_play, already_played, rating, review, ... }
  const [libraryMap, setLibraryMap] = useState({});
  // List of enriched game objects currently in the user's library
  const [libraryGames, setLibraryGames] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [authPromptOpen, setAuthPromptOpen] = useState(false);

  // Load library whenever user logs in
  const loadLibrary = useCallback(async () => {
    if (!isLoggedIn) {
      setLibraryMap({});
      setLibraryGames([]);
      return;
    }
    setIsLoading(true);
    try {
      const games = await fetchUserLibrary();
      const map = {};
      games.forEach((g) => {
        if (g.appid) {
          map[g.appid] = {
            appid: g.appid,
            is_favourite: Boolean(g.is_favourite),
            want_to_play: Boolean(g.want_to_play),
            already_played: Boolean(g.already_played),
            rating: g.rating ?? null,
            review: g.review ?? null,
          };
        }
      });
      setLibraryMap(map);
      setLibraryGames(games);
    } catch (err) {
      console.error("Failed to load user library:", err);
    } finally {
      setIsLoading(false);
    }
  }, [isLoggedIn]);

  useEffect(() => {
    loadLibrary();
  }, [loadLibrary]);

  const getGameStatus = useCallback(
    (appid) => {
      if (!appid) {
        return {
          appid: 0,
          is_favourite: false,
          want_to_play: false,
          already_played: false,
          rating: null,
          review: null,
        };
      }
      return (
        libraryMap[appid] || {
          appid,
          is_favourite: false,
          want_to_play: false,
          already_played: false,
          rating: null,
          review: null,
        }
      );
    },
    [libraryMap]
  );

  const toggleStatus = useCallback(
    async (appid, statusKey, gameMeta = null) => {
      if (!isLoggedIn) {
        setAuthPromptOpen(true);
        if (onRequireLogin) onRequireLogin();
        return false;
      }
      if (!appid) return false;

      const current = getGameStatus(appid);
      const newStatus = !current[statusKey];
      const updates = { [statusKey]: newStatus };

      // Optimistic update
      const updatedItem = { ...current, ...updates };
      setLibraryMap((prev) => ({
        ...prev,
        [appid]: updatedItem,
      }));

      // Update libraryGames list optimistically
      setLibraryGames((prev) => {
        const index = prev.findIndex((g) => g.appid === appid);
        const hasAnyState =
          updatedItem.is_favourite || updatedItem.want_to_play || updatedItem.already_played;

        if (index >= 0) {
          if (!hasAnyState && !updatedItem.rating && !updatedItem.review) {
            return prev.filter((g) => g.appid !== appid);
          }
          const copy = [...prev];
          copy[index] = { ...copy[index], ...updatedItem };
          return copy;
        } else if (hasAnyState && gameMeta) {
          return [
            {
              ...gameMeta,
              appid,
              ...updatedItem,
              image: gameMeta.image || gameMeta.header_image,
              title: gameMeta.title || gameMeta.name,
            },
            ...prev,
          ];
        }
        return prev;
      });

      try {
        const token = getCsrfToken();
        const serverState = await updateGameLibraryStatus(appid, updates, token);
        setLibraryMap((prev) => ({
          ...prev,
          [appid]: { ...prev[appid], ...serverState },
        }));
        return true;
      } catch (err) {
        console.error("Failed to update status on server:", err);
        // Revert on error
        setLibraryMap((prev) => ({
          ...prev,
          [appid]: current,
        }));
        loadLibrary();
        return false;
      }
    },
    [isLoggedIn, getGameStatus, onRequireLogin, loadLibrary]
  );

  // Directly set full state or rating/review (useful for reviews in Stage 2C)
  const setLocalStatus = useCallback((appid, statusUpdate) => {
    setLibraryMap((prev) => ({
      ...prev,
      [appid]: { ...(prev[appid] || { appid }), ...statusUpdate },
    }));
    setLibraryGames((prev) => {
      const idx = prev.findIndex((g) => g.appid === appid);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = { ...copy[idx], ...statusUpdate };
        return copy;
      }
      return prev;
    });
  }, []);

  return (
    <LibraryContext.Provider
      value={{
        libraryMap,
        libraryGames,
        isLoading,
        getGameStatus,
        toggleStatus,
        setLocalStatus,
        refreshLibrary: loadLibrary,
        authPromptOpen,
        setAuthPromptOpen,
      }}
    >
      {children}
    </LibraryContext.Provider>
  );
}

export function useLibrary() {
  const ctx = useContext(LibraryContext);
  if (!ctx) {
    throw new Error("useLibrary must be used within a LibraryProvider");
  }
  return ctx;
}
