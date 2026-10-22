import React, { useState, useEffect, useMemo, useCallback, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronDown } from "lucide-react";
import { GENRES } from "./GenreDiscovery.jsx";
import GameCard from "./GameCard.jsx";
import ComingSoonCard from "./ComingSoonCard.jsx";
import { fetchGames } from "./services/gameService.js";

/**
 * GameGallery — Game discovery grid.
 *
 * Now lives BELOW the GenreDiscovery section.
 * Accepts `selectedGenre` prop to filter games by genre category.
 *
 * Responsive grid:
 *   Desktop  → 4 columns
 *   Tablet   → 3 columns
 *   Mobile   → 2 columns
 *
 * Renders filtered games + Coming Soon placeholders.
 * Uses Framer Motion for staggered entrance animation.
 */

const COMING_SOON_COUNT = 4;
const INITIAL_VISIBLE_COUNT = 50;
const LOAD_MORE_COUNT = 50;

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.15,
    },
  },
};

/**
 * Filter games by selected genre category.
 * Genre categories map to one or more `game.genre` values,
 * and the "roguelike" category also matches by tags.
 */
function filterGames(games, selectedGenre, searchQuery) {
  let result = games;

  if (selectedGenre) {
    const genreDef = GENRES.find((g) => g.key === selectedGenre);
    if (genreDef && genreDef.matchTags) {
      result = result.filter((game) => {
        return game.all_tags.some((tag) => genreDef.matchTags.includes(tag));
      });
    }
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    result = result.filter(
      (game) =>
        game.title.toLowerCase().includes(q) ||
        game.all_tags.some((t) => t.includes(q))
    );
  }

  return result;
}

function GameGallery({ onGenreHover, selectedGenre, searchQuery, onClearGenre, onGameClick, onGamesLoaded }) {
  const [games, setGames] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [visibleCount, setVisibleCount] = useState(INITIAL_VISIBLE_COUNT);

  // Reset visible count back to initial whenever genre or search query changes
  useEffect(() => {
    setVisibleCount(INITIAL_VISIBLE_COUNT);
  }, [selectedGenre, searchQuery]);

  useEffect(() => {
    let mounted = true;
    
    async function loadGames() {
      setIsLoading(true);
      const data = await fetchGames(1000, 0);
      
      if (!mounted) return;

      // Map backend schema to what GameCard expects
      const mapped = data.map((g) => {
        let priceVal = "Price Unavailable";
        if (g.price && typeof g.price.final !== 'undefined') {
          priceVal = g.price.final === 0 ? 0 : g.price.final / 100;
        }

        // Flatten genres and categories into a single lowercased tags array
        const all_tags = [];
        if (Array.isArray(g.genres)) {
          g.genres.forEach(gn => {
             if (typeof gn === 'string') all_tags.push(gn.toLowerCase());
             else if (gn.description) all_tags.push(gn.description.toLowerCase());
          });
        }
        if (Array.isArray(g.categories)) {
          g.categories.forEach(c => {
             if (typeof c === 'string') all_tags.push(c.toLowerCase());
             else if (c.description) all_tags.push(c.description.toLowerCase());
          });
        }
        
        // Also add keywords from short_description just in case
        const desc = (g.short_description || "").toLowerCase();
        if (desc.includes("roguelike") || desc.includes("rogue-like") || desc.includes("rogue-lite") || desc.includes("loop")) {
          all_tags.push("roguelike");
        }

        const uniqueTags = Array.from(new Set(all_tags));
        const displayTags = uniqueTags
          .filter(t => !t.includes("steam") && !t.includes("controller") && !t.includes("sound") && !t.includes("remote play")) // filter out noise
          .map(t => t.replace(/\b\w/g, c => c.toUpperCase())); // Title Case

        return {
          id: g.appid,
          appid: g.appid,
          title: g.name,
          genre: g.genres && g.genres.length > 0 ? (typeof g.genres[0] === 'string' ? g.genres[0] : g.genres[0].description || "Game") : "Game",
          tags: displayTags, // Cleaned, capitalized unique tags for the UI
          all_tags: all_tags, // For internal filtering
          price: priceVal,
          price_inr: priceVal, 
          image: g.header_image,
          description: g.short_description
        };
      });
      
      setGames(mapped);
      if (onGamesLoaded) onGamesLoaded(mapped.length);
      setIsLoading(false);
    }
    
    loadGames();
    
    return () => { mounted = false; };
  }, []);

  const filteredGames = useMemo(
    () => filterGames(games, selectedGenre, searchQuery),
    [games, selectedGenre, searchQuery]
  );

  const visibleGames = useMemo(
    () => filteredGames.slice(0, visibleCount),
    [filteredGames, visibleCount]
  );

  const handleGenreHover = useCallback(
    (genre) => onGenreHover?.(genre),
    [onGenreHover]
  );

  // Resolve display name for the active genre filter
  const activeGenreLabel = useMemo(() => {
    if (!selectedGenre) return null;
    const g = GENRES.find((g) => g.key === selectedGenre);
    return g?.name ?? selectedGenre;
  }, [selectedGenre]);

  return (
    <div id="game-gallery" className="relative z-10 w-full overflow-x-hidden scroll-mt-8">
      {/* Background ambient effects */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute left-1/4 top-0 h-[600px] w-[600px] rounded-full bg-cyan-500/[0.03] blur-[120px]" />
        <div className="absolute right-1/4 top-1/3 h-[500px] w-[500px] rounded-full bg-violet-500/[0.03] blur-[120px]" />
        <div className="absolute bottom-0 left-1/2 h-[400px] w-[800px] -translate-x-1/2 rounded-full bg-cyan-500/[0.02] blur-[100px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-[1440px] px-4 py-8 sm:px-6 lg:px-10">
        {/* Section header with optional filter indicator */}
        <div className="mb-8 flex flex-col items-center gap-4 text-center sm:mb-10">
          <motion.h2
            key={selectedGenre || "all"}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="text-2xl font-black tracking-tight text-white sm:text-3xl"
          >
            {searchQuery ? `Search Results for "${searchQuery}"` : selectedGenre ? activeGenreLabel : "All Games"}
          </motion.h2>

          {/* Active filter badge + "Show All Games" reset */}
          <AnimatePresence>
            {selectedGenre && (
              <motion.button
                key="clear-genre"
                initial={{ opacity: 0, scale: 0.9, y: 5 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 5 }}
                transition={{ duration: 0.3 }}
                onClick={onClearGenre}
                className="inline-flex items-center gap-2 rounded-full border border-slate-700/50 bg-slate-900/60 px-4 py-2 text-xs font-semibold text-slate-400 backdrop-blur-md transition-all duration-300 hover:border-cyan-400/30 hover:text-cyan-300 sm:text-sm"
              >
                Show All Games
                <X className="h-3.5 w-3.5" />
              </motion.button>
            )}
          </AnimatePresence>

          {/* Decorative divider */}
          <div className="h-px w-24 bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent" />

          {/* Game count */}
          {!isLoading && (
            <p className="text-xs text-slate-500 sm:text-sm">
              Showing <span className="font-semibold text-slate-300">{visibleGames.length}</span> of{" "}
              <span className="font-semibold text-slate-300">{filteredGames.length}</span>{" "}
              {filteredGames.length === 1 ? "game" : "games"}
              {searchQuery ? " found" : selectedGenre ? " in this genre" : " available"}
            </p>
          )}
        </div>

        {/* Gallery Grid */}
        <motion.div
          key={selectedGenre || "all"}
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4 lg:gap-5"
        >
          {isLoading ? (
            /* Skeleton Loading State using ComingSoonCard */
            Array.from({ length: 8 }, (_, i) => (
              <ComingSoonCard key={`skeleton-${i}`} index={i} />
            ))
          ) : (
            /* Active game cards */
            visibleGames.map((game) => (
              <GameCard 
                key={game.id} 
                game={game} 
                onGenreHover={handleGenreHover}
                onClick={onGameClick} 
              />
            ))
          )}

          {/* Coming Soon placeholders — only show when unfiltered, loaded, and reached the end */}
          {!isLoading && !selectedGenre && !searchQuery && visibleCount >= filteredGames.length &&
            Array.from({ length: COMING_SOON_COUNT }, (_, i) => (
              <ComingSoonCard key={`coming-soon-${i}`} index={i} />
            ))}
        </motion.div>

        {/* View More Games Button & Progress */}
        {!isLoading && visibleCount < filteredGames.length && (
          <div className="mt-12 flex flex-col items-center justify-center gap-4">
            {/* Subtle progress indicator */}
            <div className="flex flex-col items-center gap-2">
              <div className="h-1 w-48 overflow-hidden rounded-full border border-slate-700/40 bg-slate-800/80">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-violet-500 shadow-[0_0_12px_rgba(34,211,238,0.5)] transition-all duration-500 ease-out"
                  style={{
                    width: `${Math.min(100, Math.round((visibleGames.length / filteredGames.length) * 100))}%`,
                  }}
                />
              </div>
              <span className="text-[11px] font-medium tracking-wide text-slate-400">
                Showing {visibleGames.length} of {filteredGames.length} games
              </span>
            </div>

            {/* Load More Button */}
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setVisibleCount((prev) => prev + LOAD_MORE_COUNT)}
              className="group relative inline-flex items-center gap-2.5 overflow-hidden rounded-xl border border-cyan-500/30 bg-slate-900/80 px-8 py-3.5 text-sm font-bold tracking-wide text-cyan-300 shadow-[0_0_25px_rgba(34,211,238,0.12)] backdrop-blur-md transition-all duration-300 hover:border-cyan-400/60 hover:bg-slate-900/95 hover:text-white hover:shadow-[0_0_35px_rgba(34,211,238,0.25)]"
            >
              <span className="relative z-10 flex items-center gap-2">
                View More Games
                <ChevronDown className="h-4 w-4 transition-transform duration-300 group-hover:translate-y-0.5" />
              </span>
              <div className="absolute inset-0 -translate-x-full bg-gradient-to-r from-cyan-500/10 via-cyan-400/20 to-transparent transition-transform duration-500 group-hover:translate-x-0" />
            </motion.button>
          </div>
        )}

        {/* Footer spacer */}
        <div className="h-20" />
      </div>
    </div>
  );
}

export default memo(GameGallery);
