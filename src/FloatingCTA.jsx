import React, { memo } from "react";
import { Sparkles } from "lucide-react";

/**
 * FloatingCTA — "Ask RigCheck AI" floating action button.
 *
 * - Fixed position: top-right corner
 * - Glassmorphism styling with cyan glow
 * - Subtle pulse animation (CSS keyframes in styles.css)
 * - Always visible (z-index: 50)
 */

function FloatingCTA({ onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="floating-cta fixed left-6 top-6 z-50 inline-flex items-center gap-2.5 rounded-2xl border border-cyan-400/25 bg-slate-950/70 px-5 py-3 text-sm font-black text-cyan-300 shadow-[0_0_35px_rgba(34,211,238,0.25),0_0_80px_rgba(34,211,238,0.08)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-cyan-400/50 hover:bg-slate-900/80 hover:text-cyan-200 hover:shadow-[0_0_50px_rgba(34,211,238,0.4),0_0_100px_rgba(34,211,238,0.15)] active:scale-[0.97]"
      aria-label="Open RigCheck AI Diagnostic"
    >
      <Sparkles className="h-4 w-4 animate-pulse-glow" />
      Ask RigCheck AI
    </button>
  );
}

export default memo(FloatingCTA);
