import React, { useState, useEffect, useCallback, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Compass,
  ArrowLeft,
  Sparkles,
  RefreshCw,
  SlidersHorizontal,
  History,
  Trash2,
  X,
  Check,
  AlertCircle,
  LogIn,
  Gamepad2,
  Star,
  CheckCircle2,
} from "lucide-react";
import GameCard from "./GameCard.jsx";
import {
  fetchPersonalizedRecommendations,
  fetchUserPreferences,
  updateUserPreferences,
  fetchAiHistory,
  deleteAiHistoryItem,
  clearAllAiHistory,
} from "./services/recommendationService.js";

const GENRE_OPTIONS = [
  "Action",
  "RPG",
  "Adventure",
  "Strategy",
  "Simulation",
  "Indie",
  "Roguelike",
  "Shooter",
  "Horror",
  "Racing",
  "Casual",
  "Sports",
  "Puzzle",
];

const INTEREST_OPTIONS = [
  "Single-player",
  "Multiplayer",
  "Co-op",
  "Open World",
  "Story Rich",
  "Competitive",
  "Sandbox",
  "Sci-Fi",
  "Fantasy",
];

function ForYouPage({ onBack, onGameClick, isLoggedIn, onRequireLogin, currentUser }) {
  const [recommendations, setRecommendations] = useState([]);
  const [alreadyPlayed, setAlreadyPlayed] = useState([]);
  const [isColdStart, setIsColdStart] = useState(false);
  const [feedRevision, setFeedRevision] = useState(1);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // Preferences & Onboarding State
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [selectedInterests, setSelectedInterests] = useState([]);
  const [savingPreferences, setSavingPreferences] = useState(false);

  // AI History State
  const [showAiHistory, setShowAiHistory] = useState(false);
  const [aiHistoryList, setAiHistoryList] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Fetch recommendations
  const loadFeed = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const data = await fetchPersonalizedRecommendations({ limit: 24, refresh: isRefresh });
      setRecommendations(data.recommendations || []);
      setAlreadyPlayed(data.already_played_recommendations || []);
      setIsColdStart(Boolean(data.is_cold_start));
      setFeedRevision(data.feed_revision || 1);
    } catch (err) {
      console.error("Failed to load FYP recommendations:", err);
      setError(err.message || "Failed to load personalized recommendations");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Fetch preferences
  const loadPreferences = useCallback(async () => {
    if (!isLoggedIn) return;
    try {
      const prefs = await fetchUserPreferences();
      setSelectedGenres(prefs.preferred_genres || []);
      setSelectedInterests(prefs.interests || []);
      // If user hasn't completed onboarding, prompt them gently once
      if (prefs.onboarding_completed === false && (prefs.preferred_genres || []).length === 0) {
        setShowPreferencesModal(true);
      }
    } catch (e) {
      // Graceful fallback
    }
  }, [isLoggedIn]);

  // Initial mount
  useEffect(() => {
    loadFeed();
    loadPreferences();
  }, [loadFeed, loadPreferences]);

  // Handle preference toggle
  const toggleGenre = (genre) => {
    setSelectedGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
  };

  const toggleInterest = (interest) => {
    setSelectedInterests((prev) =>
      prev.includes(interest) ? prev.filter((i) => i !== interest) : [...prev, interest]
    );
  };

  const handleSavePreferences = async (skip = false) => {
    setSavingPreferences(true);
    try {
      await updateUserPreferences({
        preferred_genres: skip ? selectedGenres : selectedGenres,
        interests: skip ? selectedInterests : selectedInterests,
        onboarding_completed: true,
      });
      setShowPreferencesModal(false);
      // Reload feed with new preferences
      await loadFeed(true);
    } catch (err) {
      console.error("Failed to save preferences:", err);
    } finally {
      setSavingPreferences(false);
    }
  };

  // AI History handling
  const handleOpenAiHistory = async () => {
    setShowAiHistory(true);
    setLoadingHistory(true);
    try {
      const history = await fetchAiHistory(50);
      setAiHistoryList(history);
    } catch (err) {
      console.error("Failed to fetch AI history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleDeleteHistoryItem = async (queryId) => {
    try {
      await deleteAiHistoryItem(queryId);
      setAiHistoryList((prev) => prev.filter((item) => item.id !== queryId));
      loadFeed(true);
    } catch (err) {
      console.error("Failed to delete history item:", err);
    }
  };

  const handleClearAllHistory = async () => {
    if (!window.confirm("Are you sure you want to clear your Ask RigCheck AI search history?")) return;
    try {
      await clearAllAiHistory();
      setAiHistoryList([]);
      loadFeed(true);
    } catch (err) {
      console.error("Failed to clear AI history:", err);
    }
  };

  return (
    <div className="relative min-h-screen w-full bg-[#030712] pb-24 text-slate-100">
      {/* ── Ambient Background Lighting ── */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="absolute -top-40 left-1/4 h-[500px] w-[500px] rounded-full bg-violet-600/[0.08] blur-[150px]" />
        <div className="absolute top-1/3 right-1/4 h-[550px] w-[550px] rounded-full bg-cyan-500/[0.06] blur-[160px]" />
        <div className="absolute bottom-10 left-1/2 h-[400px] w-[600px] -translate-x-1/2 rounded-full bg-indigo-500/[0.05] blur-[180px]" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 pt-6 sm:px-6 lg:px-8">
        {/* ── Top Navigation Bar ── */}
        <header className="mb-8 flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onBack}
              className="group flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/80 text-slate-300 shadow-md backdrop-blur-md transition-all duration-200 hover:border-cyan-400/40 hover:bg-slate-800 hover:text-white"
              title="Back to Catalog"
              aria-label="Back to Catalog"
            >
              <ArrowLeft className="h-5 w-5 transition-transform duration-200 group-hover:-translate-x-0.5" />
            </button>
            <div className="flex items-center gap-2.5">
              <div className="grid h-10 w-10 place-items-center rounded-2xl border border-violet-400/30 bg-violet-500/10 text-violet-300 shadow-[0_0_20px_rgba(167,139,250,0.25)]">
                <Compass className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-xl font-black tracking-tight text-white sm:text-2xl">
                  For <span className="text-violet-400">You</span>
                </h1>
                <p className="text-[11px] font-medium text-slate-400">
                  RigCheck Personalized Recommendation Feed
                </p>
              </div>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            {isLoggedIn && (
              <>
                {/* AI History Button */}
                <button
                  type="button"
                  onClick={handleOpenAiHistory}
                  className="flex h-9 items-center gap-1.5 rounded-xl border border-slate-700/60 bg-slate-900/80 px-3 text-xs font-semibold text-slate-300 backdrop-blur-md transition-all hover:border-cyan-400/40 hover:bg-slate-800 hover:text-cyan-200"
                >
                  <History className="h-3.5 w-3.5 text-cyan-400" />
                  <span>AI History</span>
                </button>

                {/* Edit Preferences Button */}
                <button
                  type="button"
                  onClick={() => setShowPreferencesModal(true)}
                  className="flex h-9 items-center gap-1.5 rounded-xl border border-slate-700/60 bg-slate-900/80 px-3 text-xs font-semibold text-slate-300 backdrop-blur-md transition-all hover:border-violet-400/40 hover:bg-slate-800 hover:text-violet-200"
                >
                  <SlidersHorizontal className="h-3.5 w-3.5 text-violet-400" />
                  <span>Preferences</span>
                </button>
              </>
            )}

            {/* Refresh Feed Button */}
            <button
              type="button"
              disabled={refreshing || loading}
              onClick={() => loadFeed(true)}
              className="flex h-9 items-center gap-1.5 rounded-xl border border-violet-500/30 bg-violet-500/10 px-3.5 text-xs font-bold text-violet-300 shadow-[0_0_15px_rgba(167,139,250,0.15)] backdrop-blur-md transition-all hover:border-violet-400 hover:bg-violet-500/20 active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} />
              <span>{refreshing ? "Refreshing..." : "Refresh Feed"}</span>
            </button>
          </div>
        </header>

        {/* ── Guest State Banner ── */}
        {!isLoggedIn && (
          <div className="mb-8 overflow-hidden rounded-2xl border border-violet-500/30 bg-gradient-to-r from-violet-950/60 via-slate-950/80 to-slate-900/60 p-6 shadow-xl backdrop-blur-xl">
            <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-400/30 bg-violet-500/10 px-2.5 py-0.5 text-[10px] font-bold text-violet-300 uppercase tracking-wider mb-2">
                  <Sparkles className="h-3 w-3" /> Guest Discovery Mode
                </span>
                <h2 className="text-lg font-black text-white sm:text-xl">
                  Sign In for Tailored Personalization
                </h2>
                <p className="mt-1 max-w-xl text-xs text-slate-300 sm:text-sm">
                  Sign in or create an account to unlock recommendations tuned to your favourite genres, played games, backlog, and RigCheck AI searches.
                </p>
              </div>
              <button
                type="button"
                onClick={onRequireLogin}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-violet-500 px-5 py-2.5 text-xs font-extrabold text-slate-950 shadow-lg shadow-violet-500/20 transition-all hover:brightness-110 active:scale-95 shrink-0"
              >
                <LogIn className="h-4 w-4" />
                <span>Sign In / Register</span>
              </button>
            </div>
          </div>
        )}

        {/* ── Hero Info & Active Signals ── */}
        <section className="mb-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-2xl font-black text-white sm:text-3xl">
                Recommended For You
              </h2>
              <p className="mt-1 text-xs text-slate-400 sm:text-sm">
                {isColdStart
                  ? "Top-rated community highlights and discovery picks to get you started."
                  : "Hand-crafted recommendations based on your library, ratings, preferences, and AI searches."}
              </p>
            </div>
            {isLoggedIn && (
              <div className="flex items-center gap-2 text-[11px] font-medium text-slate-400">
                <span className="inline-flex items-center gap-1 rounded-full border border-slate-800 bg-slate-900/90 px-2.5 py-1">
                  Feed Revision: <strong className="text-cyan-400 font-bold ml-1">{feedRevision}</strong>
                </span>
                {isColdStart && (
                  <span className="rounded-full border border-amber-400/30 bg-amber-500/10 px-2.5 py-1 text-amber-300 font-bold">
                    Discovery Mode
                  </span>
                )}
              </div>
            )}
          </div>
        </section>

        {/* ── Loading Skeleton State ── */}
        {loading && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {Array.from({ length: 12 }).map((_, idx) => (
              <div
                key={idx}
                className="aspect-[3/4] animate-pulse rounded-2xl border border-slate-800/60 bg-slate-900/40"
              />
            ))}
          </div>
        )}

        {/* ── Error State ── */}
        {!loading && error && (
          <div className="my-12 flex flex-col items-center justify-center rounded-2xl border border-rose-500/20 bg-rose-950/20 p-8 text-center backdrop-blur-md">
            <AlertCircle className="h-10 w-10 text-rose-400 mb-3" />
            <h3 className="text-base font-bold text-white mb-1">Failed to Load Feed</h3>
            <p className="text-xs text-rose-300/80 mb-4">{error}</p>
            <button
              type="button"
              onClick={() => loadFeed(false)}
              className="rounded-xl bg-slate-800 px-4 py-2 text-xs font-bold text-white hover:bg-slate-700 transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* ── Empty State ── */}
        {!loading && !error && recommendations.length === 0 && (
          <div className="my-16 flex flex-col items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/50 p-12 text-center backdrop-blur-md">
            <Gamepad2 className="h-12 w-12 text-slate-600 mb-3" />
            <h3 className="text-lg font-bold text-white mb-1">No Recommendations Found</h3>
            <p className="text-xs text-slate-400 max-w-sm mb-5">
              Select your preferred genres or explore games in the catalog to generate personalized recommendations.
            </p>
            <button
              type="button"
              onClick={() => setShowPreferencesModal(true)}
              className="rounded-xl bg-violet-600 px-5 py-2.5 text-xs font-bold text-white hover:bg-violet-500 transition-colors shadow-lg shadow-violet-600/30"
            >
              Select Preferred Genres
            </button>
          </div>
        )}

        {/* ── Main Recommendation Grid ── */}
        {!loading && !error && recommendations.length > 0 && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
            {recommendations.map((game) => (
              <GameCard
                key={game.appid}
                game={game}
                onClick={() => onGameClick?.(game)}
              />
            ))}
          </div>
        )}

        {/* ── Already Played Section (Separate Section) ── */}
        {!loading && !error && alreadyPlayed.length > 0 && (
          <section className="mt-16 border-t border-slate-800/80 pt-10">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-xl font-black text-white sm:text-2xl">
                    From Your Played Collection
                  </h3>
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  Games you have already played — kept separate from your recommendations.
                </p>
              </div>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-400">
                {alreadyPlayed.length} Games Played
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
              {alreadyPlayed.map((game) => (
                <GameCard
                  key={`played-${game.appid}`}
                  game={game}
                  onClick={() => onGameClick?.(game)}
                />
              ))}
            </div>
          </section>
        )}
      </div>

      {/* ── Genre & Interest Onboarding / Edit Preferences Modal ── */}
      <AnimatePresence>
        {showPreferencesModal && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              className="relative w-full max-w-xl rounded-2xl border border-violet-500/30 bg-slate-950 p-6 shadow-2xl"
            >
              <button
                type="button"
                onClick={() => setShowPreferencesModal(false)}
                className="absolute right-4 top-4 text-slate-400 hover:text-white"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>

              <div className="mb-5 flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-violet-500/10 text-violet-400 border border-violet-400/20">
                  <SlidersHorizontal className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-black text-white">Your Gaming Preferences</h3>
                  <p className="text-xs text-slate-400">
                    Pick your favourite genres and themes to tune your personalized feed.
                  </p>
                </div>
              </div>

              {/* Genres Section */}
              <div className="mb-5">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-2.5">
                  Favourite Genres
                </label>
                <div className="flex flex-wrap gap-2">
                  {GENRE_OPTIONS.map((genre) => {
                    const isSelected = selectedGenres.includes(genre);
                    return (
                      <button
                        key={genre}
                        type="button"
                        onClick={() => toggleGenre(genre)}
                        className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all ${
                          isSelected
                            ? "border-violet-400 bg-violet-500/25 text-violet-200 shadow-[0_0_12px_rgba(167,139,250,0.3)]"
                            : "border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3 text-violet-300" />}
                        <span>{genre}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Interests Section */}
              <div className="mb-6">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-2.5">
                  Gameplay Themes & Interests
                </label>
                <div className="flex flex-wrap gap-2">
                  {INTEREST_OPTIONS.map((interest) => {
                    const isSelected = selectedInterests.includes(interest);
                    return (
                      <button
                        key={interest}
                        type="button"
                        onClick={() => toggleInterest(interest)}
                        className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all ${
                          isSelected
                            ? "border-cyan-400 bg-cyan-500/25 text-cyan-200 shadow-[0_0_12px_rgba(34,211,238,0.3)]"
                            : "border-slate-800 bg-slate-900/80 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                        }`}
                      >
                        {isSelected && <Check className="h-3 w-3 text-cyan-300" />}
                        <span>{interest}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Modal Action Buttons */}
              <div className="flex items-center justify-between border-t border-slate-800 pt-4">
                <button
                  type="button"
                  onClick={() => handleSavePreferences(true)}
                  className="text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Skip for now
                </button>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setShowPreferencesModal(false)}
                    className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={savingPreferences}
                    onClick={() => handleSavePreferences(false)}
                    className="rounded-xl bg-violet-600 px-5 py-2 text-xs font-bold text-white hover:bg-violet-500 shadow-lg shadow-violet-600/30 transition-all disabled:opacity-50"
                  >
                    {savingPreferences ? "Saving..." : "Save Preferences"}
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ── AI Search History Drawer / Modal ── */}
      <AnimatePresence>
        {showAiHistory && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative flex h-[85vh] w-full max-w-2xl flex-col rounded-2xl border border-cyan-400/30 bg-slate-950 p-6 shadow-2xl"
            >
              <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <div className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
                    <History className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-white">Ask RigCheck AI Search History</h3>
                    <p className="text-[11px] text-slate-400">
                      Your past AI queries and recommendations used to shape your For You feed.
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setShowAiHistory(false)}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-900 hover:text-white"
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* History Content List */}
              <div className="flex-1 overflow-y-auto pr-1 space-y-3">
                {loadingHistory && (
                  <div className="py-16 text-center text-xs text-slate-400">
                    <RefreshCw className="mx-auto h-6 w-6 animate-spin text-cyan-400 mb-2" />
                    Loading search history...
                  </div>
                )}

                {!loadingHistory && aiHistoryList.length === 0 && (
                  <div className="py-20 text-center text-slate-500">
                    <Sparkles className="mx-auto h-8 w-8 mb-2 opacity-50 text-cyan-400" />
                    <p className="text-sm font-semibold text-slate-300">No search queries yet</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Use the "Ask RigCheck AI" feature on the homepage to find games matching your rig and tastes!
                    </p>
                  </div>
                )}

                {!loadingHistory &&
                  aiHistoryList.map((item) => (
                    <div
                      key={item.id}
                      className="group flex items-start justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-900/60 p-3.5 transition-all hover:border-cyan-400/30 hover:bg-slate-900"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-cyan-300 line-clamp-1">
                            "{item.query}"
                          </span>
                          <span className="text-[10px] text-slate-500 shrink-0">
                            {new Date(item.timestamp).toLocaleDateString()}
                          </span>
                        </div>

                        {item.recommended_game && (
                          <div className="mt-2 flex items-center gap-2.5 rounded-lg bg-black/40 p-1.5 border border-slate-800">
                            {item.recommended_game.header_image && (
                              <img
                                src={item.recommended_game.header_image}
                                alt={item.recommended_game.title}
                                className="h-8 w-14 rounded object-cover"
                              />
                            )}
                            <div className="min-w-0 flex-1">
                              <span className="text-[10px] uppercase font-bold text-violet-400 block">
                                Top AI Match
                              </span>
                              <span className="text-xs font-bold text-white truncate block">
                                {item.recommended_game.title}
                              </span>
                            </div>
                          </div>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => handleDeleteHistoryItem(item.id)}
                        className="rounded-lg p-2 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                        title="Delete query record"
                        aria-label="Delete query record"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
              </div>

              {/* Bottom Actions */}
              {!loadingHistory && aiHistoryList.length > 0 && (
                <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3">
                  <button
                    type="button"
                    onClick={handleClearAllHistory}
                    className="flex items-center gap-1.5 text-xs font-semibold text-rose-400 hover:text-rose-300 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Clear All History</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAiHistory(false)}
                    className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-800"
                  >
                    Close
                  </button>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default memo(ForYouPage);
