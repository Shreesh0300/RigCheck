import React, { memo } from "react";
import { motion } from "framer-motion";
import { Gamepad2, Sparkles, ChevronDown } from "lucide-react";

/**
 * HeroSection — Full-viewport landing hero for RigCheck.
 *
 * Content:
 *  - RigCheck logo + branding
 *  - Tagline: "Discover your next game. Know if your PC can run it."
 *  - "Browse Genres" CTA button that scrolls to #genre-discovery
 *  - Animated scroll-cue chevron
 */

function HeroSection() {
  const scrollToGenres = () => {
    const el = document.getElementById("genre-discovery");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <section className="relative z-10 flex min-h-[100dvh] w-full flex-col items-center justify-center overflow-hidden px-4">
      {/* Background ambient orbs */}
      <div className="pointer-events-none absolute inset-0 z-0">
        <div className="absolute left-1/4 top-1/4 h-[500px] w-[500px] rounded-full bg-cyan-500/[0.04] blur-[140px]" />
        <div className="absolute right-1/4 bottom-1/4 h-[400px] w-[400px] rounded-full bg-violet-500/[0.04] blur-[120px]" />
        <div className="absolute left-1/2 top-1/2 h-[300px] w-[600px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-cyan-400/[0.02] blur-[100px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center">
        {/* Logo */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="mb-8 flex items-center gap-4"
        >
          <div className="relative grid h-16 w-16 place-items-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 shadow-[0_0_40px_rgba(34,211,238,0.25)]">
            <Gamepad2 className="h-8 w-8 text-cyan-300" />
            <Sparkles className="absolute -right-2 -top-2 h-5 w-5 rounded-full bg-violet-500 p-0.5 text-white" />
          </div>
          <h1 className="text-4xl font-black tracking-tight text-white sm:text-5xl lg:text-6xl">
            Rig<span className="text-cyan-400">Check</span>
          </h1>
        </motion.div>

        {/* Tagline */}
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.25, ease: "easeOut" }}
          className="mb-4 max-w-xl text-lg leading-relaxed text-slate-300 sm:text-xl"
        >
          Discover your next game.
        </motion.p>
        <motion.p
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.4, ease: "easeOut" }}
          className="mb-12 max-w-xl text-base leading-relaxed text-slate-500 sm:text-lg"
        >
          Know if your PC can run it.
        </motion.p>

        {/* Decorative divider */}
        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.8, delay: 0.5, ease: "easeOut" }}
          className="mb-12 h-px w-48 bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent"
        />

        {/* Browse Genres CTA */}
        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.65, ease: "easeOut" }}
          onClick={scrollToGenres}
          className="hero-cta-btn group relative inline-flex items-center gap-3 rounded-2xl border border-cyan-400/25 bg-cyan-400/[0.08] px-8 py-4 text-base font-bold text-cyan-300 shadow-[0_0_40px_rgba(34,211,238,0.15)] backdrop-blur-xl transition-all duration-400 hover:-translate-y-1 hover:border-cyan-400/50 hover:bg-cyan-400/[0.15] hover:text-cyan-200 hover:shadow-[0_0_60px_rgba(34,211,238,0.3)] active:scale-[0.97] sm:text-lg"
        >
          Browse Genres
          <ChevronDown className="h-5 w-5 transition-transform duration-300 group-hover:translate-y-0.5" />
        </motion.button>
      </div>

      {/* Scroll cue chevron — animated bounce */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, delay: 1.2 }}
        className="absolute bottom-8 left-1/2 z-10 -translate-x-1/2"
      >
        <div
          className="scroll-cue-bounce flex cursor-pointer flex-col items-center gap-0.5 text-slate-600 transition-colors duration-300 hover:text-cyan-400"
          onClick={scrollToGenres}
        >
          <ChevronDown className="h-5 w-5" />
          <ChevronDown className="h-5 w-5 -mt-3" />
        </div>
      </motion.div>
    </section>
  );
}

export default memo(HeroSection);
