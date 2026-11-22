import React, { memo } from "react";
import { Sparkles, Compass } from "lucide-react";

/**
 * FloatingCTA — "Ask RigCheck AI" and "For You" floating action buttons.
 *
 * - Fixed position: top-left corner
 * - Glassmorphism styling with cyan & violet glow matching RigCheck aesthetics
 * - Always accessible (z-index: 50)
 */

function FloatingCTA({ onOpenDiagnostic, onOpenForYou, currentView = "home" }) {
  return (
    <div className="fixed left-6 top-6 z-50 flex items-center gap-2.5">
      {/* Ask RigCheck AI Button */}
      <button
        type="button"
        onClick={onOpenDiagnostic}
        className="floating-cta inline-flex items-center gap-2 rounded-2xl border border-cyan-400/25 bg-slate-950/75 px-4 py-2.5 text-xs font-black text-cyan-300 shadow-[0_0_25px_rgba(34,211,238,0.2)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-cyan-400/50 hover:bg-slate-900/85 hover:text-cyan-200 hover:shadow-[0_0_40px_rgba(34,211,238,0.35)] active:scale-[0.97] sm:px-5 sm:py-3 sm:text-sm"
        aria-label="Open RigCheck AI Diagnostic"
      >
        <Sparkles className="h-4 w-4 text-cyan-400 animate-pulse-glow" />
        <span className="hidden xs:inline">Ask</span> RigCheck AI
      </button>

      {/* For You Button (Phase 5) */}
      <button
        type="button"
        onClick={onOpenForYou}
        className={`floating-fyp inline-flex items-center gap-2 rounded-2xl border px-4 py-2.5 text-xs font-black backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 active:scale-[0.97] sm:px-5 sm:py-3 sm:text-sm ${
          currentView === "for-you"
            ? "border-violet-400 bg-violet-950/80 text-violet-200 shadow-[0_0_35px_rgba(167,139,250,0.4)]"
            : "border-violet-400/30 bg-slate-950/75 text-violet-300 shadow-[0_0_25px_rgba(167,139,250,0.18)] hover:border-violet-400/60 hover:bg-slate-900/85 hover:text-violet-200 hover:shadow-[0_0_40px_rgba(167,139,250,0.35)]"
        }`}
        aria-label="Open For You Recommendations"
      >
        <Compass className={`h-4 w-4 ${currentView === "for-you" ? "text-violet-300 animate-spin" : "text-violet-400"}`} />
        <span>For You</span>
      </button>
    </div>
  );
}

export default memo(FloatingCTA);
