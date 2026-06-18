import React, { useState, useCallback, memo } from "react";
import { motion } from "framer-motion";
import { Swords, Mountain, Crosshair, Heart, Castle, Repeat } from "lucide-react";

/**
 * GenreDiscovery — Cinematic genre browser section.
 *
 * Displays 6 large genre tiles in a 3×2 desktop / 2-column mobile grid.
 * Netflix-style hover interactions: scale, glow, dim siblings.
 *
 * Props:
 *  - onGenreHover(genre | null) — reports hovered genre to parent (controls BackgroundVideoLayer)
 *  - onGenreSelect(genreKey | null) — sets the selected genre filter
 *
 * Video mapping (implemented in BackgroundVideoLayer.jsx):
 *   activeGenre === "action-rpg"   → /bgv/RPGOPW.mp4
 *   activeGenre === "simulation"   → /bgv/SS.mp4
 *   activeGenre === "competitive"  → /bgv/Comp.mp4
 *   activeGenre === "indie"        → /bgv/indie.mp4
 *   activeGenre === "strategy"     → /bgv/str.mp4
 *   activeGenre === "roguelike"    → /bgv/loop.mp4
 */

const GENRES = [
  {
    key: "action-rpg",
    name: "Action / Adventure / RPG",
    tagline: "Open Worlds · Story Driven Adventures · Epic Exploration",
    descriptors: ["Open Worlds", "Story Driven Adventures", "Epic Exploration"],
    icon: Swords,
    image: "/images/genre_action_rpg.png",
    // Maps to these game.genre values in gameData.js
    matchGenres: ["Action", "RPG", "Horror", "Racing"],
    videoSrc: "/bgv/RPGOPW.mp4",
    accentColor: "rgba(239, 68, 68, 0.5)",     // red
    glowColor: "rgba(239, 68, 68, 0.25)",
  },
  {
    key: "simulation",
    name: "Simulation / Sandbox",
    tagline: "Build Worlds · Manage Empires · Shape Reality",
    descriptors: ["Build Worlds", "Manage Empires", "Shape Reality"],
    icon: Mountain,
    image: "/images/genre_simulation.png",
    matchGenres: ["Simulation", "Sandbox"],
    videoSrc: "/bgv/SS.mp4",
    accentColor: "rgba(34, 197, 94, 0.5)",      // green
    glowColor: "rgba(34, 197, 94, 0.25)",
  },
  {
    key: "competitive",
    name: "Competitive / Combat",
    tagline: "Test Your Skills · Fight to Win · Prove Yourself",
    descriptors: ["Test Your Skills", "Fight to Win", "Prove Yourself"],
    icon: Crosshair,
    image: "/images/genre_competitive.png",
    matchGenres: ["Fighting", "FPS"],
    videoSrc: "/bgv/Comp.mp4",
    accentColor: "rgba(59, 130, 246, 0.5)",     // blue
    glowColor: "rgba(59, 130, 246, 0.25)",
  },
  {
    key: "indie",
    name: "Cozy / Indie / Casual",
    tagline: "Relax · Explore · Enjoy the Journey",
    descriptors: ["Relax", "Explore", "Enjoy the Journey"],
    icon: Heart,
    image: "/images/genre_indie_cozy.png",
    matchGenres: ["Casual", "Platformer", "Puzzle"],
    videoSrc: "/bgv/indie.mp4",
    accentColor: "rgba(236, 72, 153, 0.5)",     // pink
    glowColor: "rgba(236, 72, 153, 0.25)",
  },
  {
    key: "strategy",
    name: "Strategy / Grand Planning",
    tagline: "Command Armies · Outwit Opponents · Conquer Realms",
    descriptors: ["Command Armies", "Outwit Opponents", "Conquer Realms"],
    icon: Castle,
    image: "/images/genre_strategy.png",
    matchGenres: ["Strategy"],
    videoSrc: "/bgv/str.mp4",
    accentColor: "rgba(234, 179, 8, 0.5)",      // amber
    glowColor: "rgba(234, 179, 8, 0.25)",
  },
  {
    key: "roguelike",
    name: "Roguelikes / Loop Builders",
    tagline: "Die · Learn · Repeat · Master the Loop",
    descriptors: ["Die", "Learn", "Repeat", "Master the Loop"],
    icon: Repeat,
    image: "/images/genre_roguelike.png",
    // Special: matches games whose tags include "Rogue-like" or "Roguelike"
    matchGenres: [],
    matchTags: ["Rogue-like", "Roguelike"],
    videoSrc: "/bgv/loop.mp4",
    accentColor: "rgba(139, 92, 246, 0.5)",     // violet
    glowColor: "rgba(139, 92, 246, 0.25)",
  },
];

// Export for use in GameGallery filtering
export { GENRES };

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 40, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

function GenreDiscovery({ onGenreHover, onGenreSelect }) {
  const [hoveredGenre, setHoveredGenre] = useState(null);

  const handleMouseEnter = useCallback(
    (genre) => {
      setHoveredGenre(genre.key);
      onGenreHover?.(genre.key);
    },
    [onGenreHover]
  );

  const handleMouseLeave = useCallback(() => {
    setHoveredGenre(null);
    onGenreHover?.(null);
  }, [onGenreHover]);

  const handleClick = useCallback(
    (genre) => {
      onGenreSelect?.(genre.key);
      // Smooth scroll to game gallery
      setTimeout(() => {
        const el = document.getElementById("game-gallery");
        if (el) el.scrollIntoView({ behavior: "smooth" });
      }, 100);
    },
    [onGenreSelect]
  );

  return (
    <section
      id="genre-discovery"
      className="relative z-10 w-full overflow-hidden px-4 py-16 sm:px-6 sm:py-24 lg:px-10"
    >
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="mx-auto mb-12 max-w-[1440px] text-center sm:mb-16"
      >
        <h2 className="mb-3 text-2xl font-black tracking-tight text-white sm:text-3xl lg:text-4xl">
          What do you want to <span className="text-cyan-400">play</span>?
        </h2>
        <p className="text-sm text-slate-500 sm:text-base">
          Choose a genre to explore curated games
        </p>
      </motion.div>

      {/* Genre grid — 3×2 desktop, 2-col mobile */}
      <motion.div
        variants={containerVariants}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-50px" }}
        className={`genre-grid mx-auto grid max-w-[1440px] grid-cols-2 gap-4 sm:gap-5 lg:grid-cols-3 lg:gap-6 ${
          hoveredGenre ? "has-hover" : ""
        }`}
      >
        {GENRES.map((genre) => {
          const Icon = genre.icon;
          const isHovered = hoveredGenre === genre.key;

          return (
            <motion.div
              key={genre.key}
              variants={cardVariants}
              className={`genre-card group relative cursor-pointer overflow-hidden rounded-3xl border transition-all duration-500 ${
                isHovered
                  ? "genre-card-active border-white/20 z-20"
                  : hoveredGenre
                  ? "genre-card-dimmed border-slate-800/40"
                  : "border-slate-800/60"
              }`}
              style={{
                "--accent": genre.accentColor,
                "--glow": genre.glowColor,
              }}
              onMouseEnter={() => handleMouseEnter(genre)}
              onMouseLeave={handleMouseLeave}
              onClick={() => handleClick(genre)}
            >
              {/* Artwork background */}
              <div className="relative aspect-[4/3] w-full overflow-hidden sm:aspect-[16/10]">
                <img
                  src={genre.image}
                  alt={genre.name}
                  loading="lazy"
                  decoding="async"
                  className="genre-card-img h-full w-full object-cover transition-all duration-700 ease-out"
                />

                {/* Gradient overlays */}
                <div className="absolute inset-0 bg-gradient-to-t from-[#02040a] via-[#02040a]/60 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[#02040a]/50" />

                {/* Icon badge — top left */}
                <div
                  className="absolute left-4 top-4 grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-black/50 backdrop-blur-md transition-all duration-300 sm:h-12 sm:w-12 sm:rounded-2xl"
                  style={{
                    borderColor: isHovered ? genre.accentColor : undefined,
                    boxShadow: isHovered
                      ? `0 0 20px ${genre.glowColor}`
                      : undefined,
                  }}
                >
                  <Icon
                    className="h-5 w-5 text-slate-300 transition-colors duration-300 sm:h-6 sm:w-6"
                    style={{
                      color: isHovered ? "white" : undefined,
                    }}
                  />
                </div>

                {/* Text overlay — bottom */}
                <div className="absolute inset-x-0 bottom-0 px-5 pb-5 pt-12 sm:px-6 sm:pb-6">
                  {/* Genre name */}
                  <h3 className="mb-2 text-base font-black leading-tight tracking-tight text-white drop-shadow-lg sm:text-lg lg:text-xl">
                    {genre.name}
                  </h3>

                  {/* Tagline — always visible */}
                  <p className="text-xs font-medium text-slate-400 sm:text-sm">
                    {genre.tagline}
                  </p>

                  {/* Extended descriptors — revealed on hover */}
                  <div
                    className="mt-3 flex flex-wrap gap-1.5 transition-all duration-500"
                    style={{
                      opacity: isHovered ? 1 : 0,
                      transform: isHovered
                        ? "translateY(0)"
                        : "translateY(8px)",
                      maxHeight: isHovered ? "80px" : "0px",
                      overflow: "hidden",
                    }}
                  >
                    {genre.descriptors.map((desc) => (
                      <span
                        key={desc}
                        className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-300 backdrop-blur-sm sm:text-xs"
                      >
                        {desc}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Hover glow border overlay */}
              <div
                className="pointer-events-none absolute inset-0 rounded-3xl border-2 border-transparent transition-all duration-500"
                style={{
                  borderColor: isHovered
                    ? genre.accentColor.replace("0.5", "0.3")
                    : "transparent",
                  boxShadow: isHovered
                    ? `inset 0 0 40px ${genre.glowColor}, 0 0 60px ${genre.glowColor}`
                    : "none",
                }}
              />
            </motion.div>
          );
        })}
      </motion.div>
    </section>
  );
}

export default memo(GenreDiscovery);
