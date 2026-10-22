import React, { useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, User, Mail, Shield, Calendar, Clock, Hash, CheckCircle2 } from "lucide-react";

/**
 * ProfileModal — Cyberpunk-themed modal displaying the authenticated user's real account information.
 */
export default function ProfileModal({ isOpen, onClose, currentUser }) {
  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
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

  if (!isOpen) return null;

  const provider = currentUser?.auth_provider || "email";
  const initial = (currentUser?.display_name || currentUser?.email || "U")[0].toUpperCase();

  const formatDate = (isoString) => {
    if (!isoString) return "N/A";
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <AnimatePresence>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        onClick={handleBackdropClick}
      >
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/75 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className="relative z-10 w-full max-w-lg overflow-hidden rounded-3xl border border-cyan-400/25 bg-gradient-to-br from-slate-900/95 via-slate-950/95 to-slate-900/95 p-6 shadow-[0_20px_60px_rgba(0,0,0,0.8),0_0_40px_rgba(34,211,238,0.12)] backdrop-blur-2xl ring-1 ring-white/10"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-2xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.2)]">
                <User className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Gamer Profile</h2>
                <p className="text-xs text-slate-400">Authenticated RigCheck Account Details</p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close Profile"
              className="grid h-9 w-9 place-items-center rounded-xl border border-slate-700/60 bg-slate-900/60 text-slate-400 transition-colors hover:border-cyan-400/40 hover:bg-slate-800 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* User Hero Banner */}
          <div className="my-5 flex items-center gap-4 rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.04] p-4">
            {currentUser?.avatar_url || currentUser?.avatar ? (
              <img
                src={currentUser.avatar_url || currentUser.avatar}
                alt={currentUser.display_name}
                className="h-16 w-16 rounded-2xl border-2 border-cyan-400/40 object-cover shadow-[0_0_20px_rgba(34,211,238,0.3)]"
              />
            ) : (
              <div className="grid h-16 w-16 place-items-center rounded-2xl border-2 border-cyan-400/40 bg-cyan-400/15 text-2xl font-black text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)]">
                {initial}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <h3 className="truncate text-lg font-bold text-white">
                  {currentUser?.display_name || "Gamer"}
                </h3>
                <CheckCircle2 className="h-4 w-4 text-cyan-400 shrink-0" title="Verified Account" />
              </div>
              <p className="truncate text-xs text-slate-400">
                {currentUser?.email || (provider === "steam" ? "No email linked (Steam Account)" : "Verified Gamer")}
              </p>
              <div className="mt-2 inline-flex items-center gap-1.5 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-0.5 text-[11px] font-semibold text-cyan-300">
                <Shield className="h-3 w-3" />
                <span className="capitalize">{provider} Provider</span>
              </div>
            </div>
          </div>

          {/* Detailed Info Grid */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
            {/* Email */}
            <div className="rounded-xl border border-white/5 bg-slate-950/50 p-3">
              <span className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Mail className="h-3.5 w-3.5 text-cyan-400" /> Email
              </span>
              <p className="mt-1 font-semibold text-slate-200 truncate" title={currentUser?.email || "None"}>
                {currentUser?.email || "N/A (Steam Auth)"}
              </p>
            </div>

            {/* Provider */}
            <div className="rounded-xl border border-white/5 bg-slate-950/50 p-3">
              <span className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Shield className="h-3.5 w-3.5 text-cyan-400" /> Authentication
              </span>
              <p className="mt-1 font-semibold text-slate-200 capitalize">
                {provider === "google" ? "Google OAuth 2.0" : provider === "steam" ? "Steam OpenID 2.0" : "Email & Password"}
              </p>
            </div>

            {/* Created At */}
            <div className="rounded-xl border border-white/5 bg-slate-950/50 p-3">
              <span className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Calendar className="h-3.5 w-3.5 text-cyan-400" /> Member Since
              </span>
              <p className="mt-1 font-semibold text-slate-200">
                {formatDate(currentUser?.created_at)}
              </p>
            </div>

            {/* Last Login */}
            <div className="rounded-xl border border-white/5 bg-slate-950/50 p-3">
              <span className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Clock className="h-3.5 w-3.5 text-cyan-400" /> Last Active
              </span>
              <p className="mt-1 font-semibold text-slate-200">
                {formatDate(currentUser?.last_login)}
              </p>
            </div>

            {/* User ID */}
            <div className="col-span-1 sm:col-span-2 rounded-xl border border-white/5 bg-slate-950/50 p-3">
              <span className="flex items-center gap-1.5 text-slate-400 font-medium">
                <Hash className="h-3.5 w-3.5 text-cyan-400" /> Internal Account ID
              </span>
              <p className="mt-1 font-mono text-[11px] text-slate-300 truncate">
                {currentUser?.id || "N/A"}
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-5 py-2 text-xs font-bold text-cyan-300 transition-all hover:bg-cyan-400/20 hover:text-cyan-200 hover:shadow-[0_0_20px_rgba(34,211,238,0.25)]"
            >
              Done
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
