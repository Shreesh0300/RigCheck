import React, { memo } from "react";
import { motion } from "framer-motion";

/**
 * GameCard — A single game tile for the gallery grid.
 *
 * Features:
 * - Lazy-loaded artwork with aspect-ratio container
 * - Genre badge (top-left)
 * - Price badge (top-right)
 * - Title overlay with gradient fade
 * - Scale + glow on hover
 * - Framer Motion staggered entrance
 */

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

function GameCard({ game, onGenreHover, onClick }) {
  const priceLabel = game.price === 0 ? "Free" : `₹${game.price.toLocaleString("en-IN")}`;

  return (
    <motion.div
      variants={cardVariants}
      className="game-card group relative overflow-hidden rounded-2xl border border-slate-800/60 bg-slate-950/80 shadow-lg shadow-black/30 cursor-pointer hover:z-20"
      onMouseEnter={() => onGenreHover?.(game.genre)}
      onMouseLeave={() => onGenreHover?.(null)}
      onClick={() => onClick?.(game)}
    >
      {/* Artwork container */}
      <div className="relative aspect-[3/4] w-full overflow-hidden">
        <img
          src={game.image}
          alt={game.title}
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-110"
        />

        {/* Gradient overlays */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#02040a] via-[#02040a]/20 to-transparent opacity-80" />
        <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[#02040a]/40" />

        {/* Genre badge — top left */}
        <span className="absolute left-3 top-3 rounded-full border border-cyan-400/20 bg-black/60 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-cyan-300 backdrop-blur-md">
          {game.genre}
        </span>

        {/* Price badge — top right */}
        <span className="absolute right-3 top-3 rounded-lg bg-black/60 px-2 py-1 text-[11px] font-extrabold text-white backdrop-blur-md">
          {priceLabel}
        </span>

        {/* Title overlay — bottom */}
        <div className="absolute inset-x-0 bottom-0 px-4 pb-4 pt-10">
          <h3 className="text-sm font-black leading-tight tracking-tight text-white drop-shadow-lg sm:text-base">
            {game.title}
          </h3>
          {/* Tag row */}
          <div className="mt-2 flex flex-wrap gap-1">
            {game.tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-slate-600/30 bg-slate-800/50 px-2 py-0.5 text-[9px] font-medium text-slate-400 backdrop-blur-sm"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Hover glow overlay */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl border-2 border-transparent transition-all duration-300 group-hover:border-cyan-400/30 group-hover:shadow-[inset_0_0_30px_rgba(34,211,238,0.06),0_0_40px_rgba(34,211,238,0.12)]" />
    </motion.div>
  );
}

export default memo(GameCard);
