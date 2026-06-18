import React, { useEffect, useCallback, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import RigCheckDashboard from "../RigCheckDashboard.jsx";

/**
 * DiagnosticModal — Fullscreen overlay that wraps the existing RigCheckDashboard.
 *
 * The RigCheckDashboard component is imported and rendered as-is.
 * No logic changes — only presentation (modal container).
 *
 * Close methods:
 *  - X button (top-right)
 *  - Click outside modal
 *  - Escape key
 */

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.25 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

const modalVariants = {
  hidden: { opacity: 0, scale: 0.92, y: 30 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 20,
    transition: { duration: 0.2, ease: "easeIn" },
  },
};

function DiagnosticModal({ isOpen, onClose }) {
  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };

    document.addEventListener("keydown", handleKeyDown);
    // Prevent body scroll when modal is open
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  const handleBackdropClick = useCallback(
    (e) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose]
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          key="diagnostic-modal-backdrop"
          variants={backdropVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          onClick={handleBackdropClick}
          className="fixed inset-0 z-[100] flex items-start justify-center overflow-y-auto bg-black/70 px-3 py-6 backdrop-blur-xl sm:items-center sm:px-6 sm:py-8"
        >
          <motion.div
            key="diagnostic-modal-content"
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="relative w-full max-w-[1200px] overflow-hidden rounded-2xl border border-slate-700/50 bg-slate-950/95 shadow-[0_0_80px_rgba(34,211,238,0.08),0_25px_50px_rgba(0,0,0,0.6)] backdrop-blur-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              className="absolute right-4 top-4 z-10 grid h-9 w-9 place-items-center rounded-xl border border-slate-700/50 bg-slate-900/80 text-slate-400 shadow-lg backdrop-blur-sm transition-all duration-200 hover:border-red-400/40 hover:bg-red-950/30 hover:text-red-300"
              aria-label="Close diagnostic modal"
            >
              <X className="h-4 w-4" />
            </button>

            {/* Existing RigCheckDashboard — rendered untouched */}
            <div className="max-h-[85vh] overflow-y-auto">
              <RigCheckDashboard />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default memo(DiagnosticModal);
