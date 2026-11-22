import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Heart,
  Bookmark,
  CheckCircle2,
  Gamepad2,
  ArrowLeft,
  Search,
  Sparkles,
  Star,
} from "lucide-react";
import { useLibrary } from "./context/LibraryContext.jsx";
import GameCard from "./GameCard.jsx";

const tabVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  exit: { opacity: 0, y: -10, transition: { duration: 0.2 } },
};

export default function MyGamesPage({ onBack, onGameClick }) {
  const { libraryGames, libraryMap, isLoading } = useLibrary();
  const [activeTab, setActiveTab] = useState("all"); // 'all' | 'favourites' | 'want_to_play' | 'already_played'
  const [filterQuery, setFilterQuery] = useState("");

  // Categorize games
  const favourites = useMemo(
    () => libraryGames.filter((g) => libraryMap[g.appid]?.is_favourite || g.is_favourite),
    [libraryGames, libraryMap]
  );

  const wantToPlay = useMemo(
    () => libraryGames.filter((g) => libraryMap[g.appid]?.want_to_play || g.want_to_play),
    [libraryGames, libraryMap]
  );

  const alreadyPlayed = useMemo(
    () => libraryGames.filter((g) => libraryMap[g.appid]?.already_played || g.already_played),
    [libraryGames, libraryMap]
  );

  // Filter helper
  const filterList = (list) => {
    if (!filterQuery) return list;
    const q = filterQuery.toLowerCase();
    return list.filter(
      (g) =>
        (g.title || g.name || "").toLowerCase().includes(q) ||
        (Array.isArray(g.genres) && g.genres.some((genre) => (typeof genre === "string" ? genre : genre.description || "").toLowerCase().includes(q)))
    );
  };

  const filteredFavourites = useMemo(() => filterList(favourites), [favourites, filterQuery]);
  const filteredWantToPlay = useMemo(() => filterList(wantToPlay), [wantToPlay, filterQuery]);
  const filteredAlreadyPlayed = useMemo(() => filterList(alreadyPlayed), [alreadyPlayed, filterQuery]);

  const totalCount = libraryGames.length;

  const renderGameSection = (title, icon, games, emptyMsg, accentColor, emptyAction) => (
    <section className="mb-14">
      {/* Section Header */}
      <div className="mb-6 flex items-center justify-between border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className={`grid h-9 w-9 place-items-center rounded-xl ${accentColor.bg} ${accentColor.border} border`}>
            {icon}
          </div>
          <h2 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
            {title}
          </h2>
          <span className="rounded-full border border-slate-700/60 bg-slate-900/80 px-2.5 py-0.5 text-xs font-bold text-slate-300">
            {games.length}
          </span>
        </div>
      </div>

      {/* Grid or Empty State */}
      {games.length === 0 ? (
        <div className="rounded-2xl border border-slate-800/80 bg-slate-950/40 p-10 text-center backdrop-blur-sm">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-slate-900/80 text-slate-500">
            {icon}
          </div>
          <p className="text-sm font-medium text-slate-400">{emptyMsg}</p>
          {emptyAction && (
            <button
              type="button"
              onClick={onBack}
              className="mt-4 inline-flex items-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-950/40 px-4 py-2 text-xs font-bold text-cyan-300 transition-all hover:bg-cyan-900/50"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Discover Games
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 sm:gap-6 lg:grid-cols-4 xl:grid-cols-4">
          {games.map((game) => {
            const mappedGame = {
              ...game,
              id: game.appid,
              title: game.title || game.name,
              image: game.header_image || game.image,
              genre: Array.isArray(game.genres) && game.genres.length > 0
                ? (typeof game.genres[0] === "string" ? game.genres[0] : game.genres[0].description)
                : "Game",
              tags: Array.isArray(game.genres)
                ? game.genres.map((g) => (typeof g === "string" ? g : g.description || ""))
                : [],
            };
            return (
              <GameCard
                key={`${title}-${game.appid}`}
                game={mappedGame}
                onClick={onGameClick}
              />
            );
          })}
        </div>
      )}
    </section>
  );

  return (
    <div className="relative min-h-screen px-4 pb-24 pt-20 sm:px-6 lg:px-12">
      {/* Background radial gradient */}
      <div className="pointer-events-none fixed inset-0 z-0 bg-[radial-gradient(circle_at_top,_var(--tw-gradient-stops))] from-cyan-950/20 via-black to-black opacity-80" />

      <div className="relative z-10 mx-auto max-w-7xl">
        {/* Navigation / Header */}
        <div className="mb-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div>
            <button
              type="button"
              onClick={onBack}
              className="group mb-4 flex items-center gap-2 rounded-xl border border-slate-700/60 bg-slate-900/60 px-3.5 py-1.5 text-xs font-bold text-slate-300 backdrop-blur-md transition-all hover:border-cyan-400/40 hover:text-cyan-300"
            >
              <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
              Back to Discover
            </button>
            <div className="flex items-center gap-3">
              <div className="grid h-12 w-12 place-items-center rounded-2xl border border-cyan-400/30 bg-cyan-950/40 text-cyan-400 shadow-[0_0_20px_rgba(34,211,238,0.15)]">
                <Gamepad2 className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-3xl font-black tracking-tight text-white sm:text-4xl">
                  My Game <span className="text-cyan-400">Library</span>
                </h1>
                <p className="text-xs text-slate-400 sm:text-sm">
                  Manage your personal favourites, backlog, and completed games
                </p>
              </div>
            </div>
          </div>

          {/* Quick Stats Pill */}
          <div className="flex items-center gap-3 rounded-2xl border border-slate-800/80 bg-slate-950/80 p-2 backdrop-blur-md">
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-rose-300">
              <Heart className="h-4 w-4 fill-rose-500 text-rose-500" />
              <span>{favourites.length} Favourites</span>
            </div>
            <div className="h-4 w-px bg-slate-800" />
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-cyan-300">
              <Bookmark className="h-4 w-4 fill-cyan-400 text-cyan-400" />
              <span>{wantToPlay.length} Want to Play</span>
            </div>
            <div className="h-4 w-px bg-slate-800" />
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold text-emerald-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>{alreadyPlayed.length} Played</span>
            </div>
          </div>
        </div>

        {/* Filter / Search Bar */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          {/* Category Tabs */}
          <div className="flex flex-wrap gap-2">
            {[
              { id: "all", label: "All Categories", count: totalCount },
              { id: "favourites", label: "Favourites", count: favourites.length, icon: <Heart className="h-3.5 w-3.5" /> },
              { id: "want_to_play", label: "Want to Play", count: wantToPlay.length, icon: <Bookmark className="h-3.5 w-3.5" /> },
              { id: "already_played", label: "Already Played", count: alreadyPlayed.length, icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-bold transition-all ${
                  activeTab === tab.id
                    ? "border border-cyan-400/50 bg-cyan-950/50 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.2)]"
                    : "border border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[10px] text-slate-300">
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          {/* Library Search */}
          <div className="relative w-full sm:w-64">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search in library..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-900/70 py-2 pl-9 pr-4 text-xs text-white placeholder-slate-500 backdrop-blur-md focus:border-cyan-400/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30"
            />
          </div>
        </div>

        {/* Category Sections */}
        <AnimatePresence mode="wait">
          {isLoading ? (
            <div className="flex h-64 items-center justify-center">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent shadow-[0_0_20px_rgba(34,211,238,0.3)]" />
            </div>
          ) : (
            <motion.div
              key={activeTab}
              variants={tabVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
            >
              {(activeTab === "all" || activeTab === "favourites") &&
                renderGameSection(
                  "Favourites",
                  <Heart className="h-5 w-5 fill-rose-500 text-rose-500" />,
                  filteredFavourites,
                  "No favourite games added yet. Click the heart icon on any game card to add it here.",
                  { bg: "bg-rose-500/10", border: "border-rose-500/30" },
                  true
                )}

              {(activeTab === "all" || activeTab === "want_to_play") &&
                renderGameSection(
                  "Want to Play",
                  <Bookmark className="h-5 w-5 fill-cyan-400 text-cyan-400" />,
                  filteredWantToPlay,
                  "Your wishlist is empty. Bookmark games you want to play next.",
                  { bg: "bg-cyan-500/10", border: "border-cyan-500/30" },
                  true
                )}

              {(activeTab === "all" || activeTab === "already_played") &&
                renderGameSection(
                  "Already Played",
                  <CheckCircle2 className="h-5 w-5 text-emerald-400" />,
                  filteredAlreadyPlayed,
                  "No played games recorded. Mark games you've completed to track them and leave reviews.",
                  { bg: "bg-emerald-500/10", border: "border-emerald-500/30" },
                  true
                )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
