import React, { useMemo, useCallback, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import GAMES from "./gameData.js";
import { GENRES } from "./GenreDiscovery.jsx";
import GameCard from "./GameCard.jsx";
import ComingSoonCard from "./ComingSoonCard.jsx";

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
function filterByGenre(games, selectedGenre) {
  if (!selectedGenre) return games;

  const genreDef = GENRES.find((g) => g.key === selectedGenre);
  if (!genreDef) return games;

  return games.filter((game) => {
    // Match by genre field
    if (genreDef.matchGenres?.length && genreDef.matchGenres.includes(game.genre)) {
      return true;
    }
    // Match by tags (for roguelikes)
    if (genreDef.matchTags?.length) {
      return game.tags.some((tag) => genreDef.matchTags.includes(tag));
    }
    return false;
  });
}

function GameGallery({ onGenreHover, selectedGenre, onClearGenre, onGameClick }) {
  const filteredGames = useMemo(
    () => filterByGenre(GAMES, selectedGenre),
    [selectedGenre]
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
            {selectedGenre ? activeGenreLabel : "All Games"}
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
          <p className="text-xs text-slate-600 sm:text-sm">
            {filteredGames.length} {filteredGames.length === 1 ? "game" : "games"}
            {selectedGenre ? " in this genre" : " available"}
          </p>
        </div>

        {/* Gallery Grid */}
        <motion.div
          key={selectedGenre || "all"}
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4 lg:gap-5"
        >
          {/* Active game cards */}
          {filteredGames.map((game) => (
            <GameCard 
              key={game.id} 
              game={game} 
              onGenreHover={handleGenreHover}
              onClick={onGameClick} 
            />
          ))}

          {/* Coming Soon placeholders — only show when unfiltered */}
          {!selectedGenre &&
            Array.from({ length: COMING_SOON_COUNT }, (_, i) => (
              <ComingSoonCard key={`coming-soon-${i}`} index={i} />
            ))}
        </motion.div>

        {/* Footer spacer */}
        <div className="h-20" />
      </div>
    </div>
  );
}

export default memo(GameGallery);
