import React, { useEffect, useCallback, useMemo, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Play, Cpu, Monitor, Download, HardDrive, Gamepad2, ArrowRight } from "lucide-react";

/**
 * GameDetailModal — Cinematic game detail overlay.
 *
 * Triggered when a user clicks a game card.
 * Features:
 * - Fullscreen blur backdrop
 * - Hero artwork with title, price, tags
 * - Game description
 * - Screenshot carousel (placeholder logic)
 * - System requirements (derived from minRam and minGpuTier)
 * - RigCheck Compatibility CTA
 */

const GPU_TIERS = {
  1: "Integrated / Low (Intel UHD)",
  2: "Entry (GTX 1050 / RX 560)",
  3: "Mid (GTX 1660 / RX 5600)",
  4: "High (RTX 3070 / RX 6800)",
  5: "Ultra (RTX 4080+)",
};

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.3 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

const modalVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] },
  },
  exit: {
    opacity: 0,
    scale: 0.98,
    y: 10,
    transition: { duration: 0.2, ease: "easeIn" },
  },
};

function GameDetailModal({ game, onClose, onOpenDiagnostic }) {
  // Close on Escape key
  useEffect(() => {
    if (!game) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden"; // Prevent background scrolling

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [game, onClose]);

  const handleBackdropClick = useCallback(
    (e) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose]
  );

  // Derived properties
  const priceLabel = useMemo(() => {
    if (!game) return "";
    return game.price === 0 ? "Free to Play" : `₹${game.price.toLocaleString("en-IN")}`;
  }, [game]);

  const requirements = useMemo(() => {
    if (!game) return null;
    return {
      min: {
        ram: `${game.minRam} GB`,
        gpu: GPU_TIERS[game.minGpuTier] || "Unknown",
        cpu: "Intel Core i5 / AMD Ryzen 5 (See store)",
        storage: "60 GB Available space",
      },
      rec: {
        ram: `${Math.ceil(game.minRam * 1.5)} GB`,
        gpu: GPU_TIERS[Math.min(game.minGpuTier + 1, 5)] || "Unknown",
        cpu: "Intel Core i7 / AMD Ryzen 7 (See store)",
        storage: "60 GB SSD Available space",
      },
    };
  }, [game]);

  return (
    <AnimatePresence>
      {game && (
        <motion.div
          key="game-detail-backdrop"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          onClick={handleBackdropClick}
          className="fixed inset-0 z-[100] flex items-center justify-center overflow-hidden bg-black/80 px-4 py-6 backdrop-blur-[20px] sm:px-6 sm:py-8 lg:px-12"
        >
          <motion.div
            key="game-detail-content"
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="relative flex h-full w-full max-w-[1280px] flex-col overflow-hidden rounded-3xl border border-slate-700/50 bg-[#0a0c14] shadow-[0_0_100px_rgba(0,0,0,0.8)]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              className="absolute right-5 top-5 z-50 grid h-10 w-10 place-items-center rounded-full bg-black/40 text-white backdrop-blur-md transition-colors hover:bg-white/20"
              aria-label="Close details"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Scrollable Content Container */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden pb-20">
              {/* ── HERO BANNER ── */}
              <div className="relative h-[400px] w-full shrink-0 sm:h-[500px] lg:h-[600px]">
                {/* Artwork */}
                <div className="absolute inset-0">
                  <img
                    src={game.image}
                    alt={game.title}
                    className="h-full w-full object-cover object-top opacity-60 mix-blend-screen"
                  />
                  {/* Gradients to fade smoothly into background */}
                  <div className="absolute inset-0 bg-gradient-to-t from-[#0a0c14] via-[#0a0c14]/40 to-transparent" />
                  <div className="absolute inset-0 bg-gradient-to-r from-[#0a0c14]/80 via-transparent to-transparent" />
                </div>

                {/* Hero Content */}
                <div className="absolute bottom-0 left-0 flex w-full flex-col justify-end px-6 pb-12 sm:px-10 sm:pb-16 lg:px-16">
                  {/* Genre badge */}
                  <span className="mb-4 inline-block w-fit rounded-full border border-cyan-400/30 bg-cyan-950/40 px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-cyan-400 backdrop-blur-md">
                    {game.genre}
                  </span>

                  <h1 className="mb-4 text-3xl font-black leading-tight tracking-tight text-white drop-shadow-xl sm:text-5xl lg:text-6xl">
                    {game.title}
                  </h1>

                  <div className="flex flex-wrap items-center gap-4 text-sm font-medium text-slate-300">
                    <span className="rounded-lg bg-white/10 px-3 py-1.5 font-bold text-white backdrop-blur-md">
                      {priceLabel}
                    </span>
                    {game.tags.slice(0, 4).map((tag) => (
                      <span key={tag} className="flex items-center gap-1.5">
                        <span className="h-1 w-1 rounded-full bg-slate-500" />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* ── TWO COLUMN LAYOUT ── */}
              <div className="mx-auto flex max-w-[1440px] flex-col gap-8 px-6 sm:px-10 lg:flex-row lg:gap-12 lg:px-16">
                
                {/* LEFT COLUMN: Info & Requirements */}
                <div className="flex-1 space-y-12 min-w-0">
                  {/* Overview */}
                  <section>
                    <h2 className="mb-4 text-xl font-bold text-white">About the Game</h2>
                    <p className="leading-relaxed text-slate-300 sm:text-lg">
                      {game.description}
                    </p>
                  </section>

                  {/* Screenshots Placeholder Carousel */}
                  <section>
                    <h2 className="mb-4 text-xl font-bold text-white">Gallery</h2>
                    <div className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory hide-scrollbar">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={`shot-${i}`}
                          className="relative aspect-video w-[280px] shrink-0 snap-center overflow-hidden rounded-xl border border-slate-800 bg-slate-900 sm:w-[400px]"
                        >
                          {/* Placeholder using main image with different filters to look like distinct screenshots */}
                          <img
                            src={game.image}
                            alt={`${game.title} screenshot ${i}`}
                            className="h-full w-full object-cover"
                            style={{
                              filter: `hue-rotate(${i * 45}deg) brightness(${1 - i * 0.1}) saturate(${1 + i * 0.2})`,
                              transform: `scale(${1 + i * 0.1})`,
                            }}
                          />
                          <div className="absolute inset-0 grid place-items-center bg-black/20">
                            <Play className="h-10 w-10 text-white/50" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* System Requirements */}
                  <section>
                    <h2 className="mb-6 text-xl font-bold text-white">System Requirements</h2>
                    
                    <div className="grid gap-4 sm:gap-6 xl:grid-cols-2">
                      {/* Minimum */}
                      <div className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-5 sm:p-6">
                        <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-400">
                          Minimum
                        </h3>
                        <ul className="space-y-4 text-sm">
                          <li className="flex gap-3 text-slate-300">
                            <Monitor className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
                            <div>
                              <span className="block font-semibold text-white">Graphics</span>
                              {requirements.min.gpu}
                            </div>
                          </li>
                          <li className="flex gap-3 text-slate-300">
                            <Cpu className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
                            <div>
                              <span className="block font-semibold text-white">Memory</span>
                              {requirements.min.ram} RAM
                            </div>
                          </li>
                          <li className="flex gap-3 text-slate-300">
                            <HardDrive className="mt-0.5 h-4 w-4 shrink-0 text-cyan-400" />
                            <div>
                              <span className="block font-semibold text-white">Storage</span>
                              {requirements.min.storage}
                            </div>
                          </li>
                        </ul>
                      </div>

                      {/* Recommended */}
                      <div className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-5 sm:p-6">
                        <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-400">
                          Recommended
                        </h3>
                        <ul className="space-y-4 text-sm">
                          <li className="flex gap-3 text-slate-300">
                            <Monitor className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
                            <div>
                              <span className="block font-semibold text-white">Graphics</span>
                              {requirements.rec.gpu}
                            </div>
                          </li>
                          <li className="flex gap-3 text-slate-300">
                            <Cpu className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
                            <div>
                              <span className="block font-semibold text-white">Memory</span>
                              {requirements.rec.ram} RAM
                            </div>
                          </li>
                          <li className="flex gap-3 text-slate-300">
                            <HardDrive className="mt-0.5 h-4 w-4 shrink-0 text-violet-400" />
                            <div>
                              <span className="block font-semibold text-white">Storage</span>
                              {requirements.rec.storage}
                            </div>
                          </li>
                        </ul>
                      </div>
                    </div>
                  </section>
                </div>

                {/* RIGHT COLUMN: Sidebar (RigCheck & Store) */}
                <div className="w-full shrink-0 space-y-6 lg:w-[320px] xl:w-[340px]">
                  
                  {/* RigCheck Compatibility Card */}
                  <div className="overflow-hidden rounded-2xl border border-cyan-400/20 bg-gradient-to-b from-cyan-950/40 to-slate-900/40 p-6 shadow-xl backdrop-blur-xl">
                    <div className="mb-6 flex items-center gap-3">
                      <div className="grid h-10 w-10 place-items-center rounded-xl bg-cyan-400/10">
                        <Gamepad2 className="h-5 w-5 text-cyan-400" />
                      </div>
                      <h3 className="font-black text-white">RigCheck Analysis</h3>
                    </div>

                    <div className="mb-6 text-center">
                      <div className="text-sm font-medium text-slate-400">Compatibility Score</div>
                      <div className="mt-1 flex items-baseline justify-center gap-1 font-black text-slate-500">
                        <span className="text-4xl text-white">--</span>
                        <span className="text-xl">/100</span>
                      </div>
                      <p className="mt-2 text-xs text-slate-400">Run diagnostic to calculate</p>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        onClose(); // Close this modal first
                        onOpenDiagnostic(); // Then open the RigCheck tool
                      }}
                      className="group flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-400 px-4 py-3.5 text-sm font-bold text-slate-950 transition-all hover:bg-cyan-300 active:scale-95"
                    >
                      Analyze My PC
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </button>
                  </div>

                  {/* Available On Placeholders */}
                  <div className="rounded-2xl border border-slate-800/60 bg-slate-900/30 p-6">
                    <h3 className="mb-4 text-sm font-bold text-slate-400">Available On</h3>
                    <div className="space-y-3">
                      {["Steam", "Epic Games", "Xbox"].map((platform) => (
                        <button
                          key={platform}
                          className="flex w-full items-center justify-between rounded-xl border border-white/5 bg-white/5 px-4 py-3 text-sm font-medium text-slate-300 transition-colors hover:bg-white/10"
                        >
                          {platform}
                          <Download className="h-4 w-4 opacity-50" />
                        </button>
                      ))}
                    </div>
                  </div>

                </div>

              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default memo(GameDetailModal);
