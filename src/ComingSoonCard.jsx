import React, { memo } from "react";
import { motion } from "framer-motion";
import { Lock } from "lucide-react";

/**
 * ComingSoonCard — A locked placeholder card for upcoming games.
 *
 * Visual treatment:
 * - Grayscale + reduced opacity + slight blur
 * - Lock icon overlay
 * - "Coming Soon" label
 * - pointer-events: none (no interactions)
 */

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

function ComingSoonCard({ index = 0 }) {
  return (
    <motion.div
      variants={cardVariants}
      className="pointer-events-none relative aspect-[3/4] w-full select-none overflow-hidden rounded-2xl border border-slate-800/40 bg-slate-950/60"
    >
      {/* Blurred background pattern */}
      <div className="absolute inset-0 opacity-30 blur-[2px] grayscale">
        <div
          className="h-full w-full"
          style={{
            background: `
              radial-gradient(ellipse at ${30 + index * 15}% ${40 + index * 10}%, rgba(34,211,238,0.08) 0%, transparent 50%),
              radial-gradient(ellipse at ${70 - index * 10}% ${60 + index * 5}%, rgba(139,92,246,0.06) 0%, transparent 50%),
              linear-gradient(135deg, #0f172a 0%, #020617 50%, #0f172a 100%)
            `,
          }}
        />
      </div>

      {/* Lock icon + label overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
        <div className="grid h-14 w-14 place-items-center rounded-2xl border border-slate-700/40 bg-slate-900/60 shadow-lg backdrop-blur-sm">
          <Lock className="h-6 w-6 text-slate-500" />
        </div>
        <span className="text-xs font-bold uppercase tracking-widest text-slate-600">
          Coming Soon
        </span>
      </div>

      {/* Subtle border glow */}
      <div className="absolute inset-0 rounded-2xl border border-slate-700/20" />
    </motion.div>
  );
}

export default memo(ComingSoonCard);
