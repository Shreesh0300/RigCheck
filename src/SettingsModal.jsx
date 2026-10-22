import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Settings, Monitor, Sliders, Check, RotateCcw } from "lucide-react";

const SETTINGS_KEY = "rigcheck_user_settings";

const DEFAULT_SETTINGS = {
  resolution: "1440p",
  targetFps: "60",
  qualityPreset: "High",
  reducedMotion: false,
};

export default function SettingsModal({ isOpen, onClose }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [savedFeedback, setSavedFeedback] = useState(false);
  const [clearedFeedback, setClearedFeedback] = useState(false);

  // Load settings on open
  useEffect(() => {
    if (isOpen) {
      try {
        const stored = localStorage.getItem(SETTINGS_KEY);
        if (stored) {
          setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(stored) });
        }
      } catch (e) {
        // Fallback to default
      }
    }
  }, [isOpen]);

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

  const updateSetting = (key, value) => {
    setSettings((prev) => {
      const next = { ...prev, [key]: value };
      try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(next));
      } catch (e) {
        // Storage error handling
      }
      return next;
    });
    setSavedFeedback(true);
    setTimeout(() => setSavedFeedback(false), 1500);
  };

  const handleResetRig = () => {
    try {
      localStorage.removeItem("rigcheck_saved_rig");
      localStorage.removeItem("rigcheck_diagnostic_cache");
      setClearedFeedback(true);
      setTimeout(() => setClearedFeedback(false), 2000);
    } catch (e) {
      // Storage error
    }
  };

  if (!isOpen) return null;

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
                <Settings className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-xl font-bold tracking-tight text-white">Preferences & Settings</h2>
                <p className="text-xs text-slate-400">Diagnostic Simulation & App Configuration</p>
              </div>
            </div>
            <button
              onClick={onClose}
              aria-label="Close Settings"
              className="grid h-9 w-9 place-items-center rounded-xl border border-slate-700/60 bg-slate-900/60 text-slate-400 transition-colors hover:border-cyan-400/40 hover:bg-slate-800 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Form Options */}
          <div className="my-5 flex flex-col space-y-4 text-xs">
            {/* Setting 1: Target Resolution */}
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="flex items-center gap-2 font-semibold text-slate-200">
                  <Monitor className="h-4 w-4 text-cyan-400" /> Target Diagnostic Resolution
                </span>
                <span className="text-[11px] text-slate-400 font-mono">{settings.resolution}</span>
              </div>
              <p className="mb-3 text-slate-400 text-[11px]">
                Determines the GPU render resolution evaluated during game compatibility scans.
              </p>
              <div className="grid grid-cols-3 gap-2">
                {["1080p", "1440p", "4K"].map((res) => (
                  <button
                    key={res}
                    type="button"
                    onClick={() => updateSetting("resolution", res)}
                    className={`rounded-xl border py-2 font-bold transition-all ${
                      settings.resolution === res
                        ? "border-cyan-400 bg-cyan-400/20 text-cyan-200 shadow-[0_0_15px_rgba(34,211,238,0.3)]"
                        : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-white"
                    }`}
                  >
                    {res}
                  </button>
                ))}
              </div>
            </div>

            {/* Setting 2: Target Framerate */}
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="flex items-center gap-2 font-semibold text-slate-200">
                  <Sliders className="h-4 w-4 text-cyan-400" /> Target Framerate Threshold
                </span>
                <span className="text-[11px] text-slate-400 font-mono">{settings.targetFps} FPS</span>
              </div>
              <p className="mb-3 text-slate-400 text-[11px]">
                Baseline refresh rate target required for a game to qualify as "Playable".
              </p>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: "60 FPS", val: "60" },
                  { label: "120 FPS", val: "120" },
                  { label: "144 FPS", val: "144" },
                ].map((fps) => (
                  <button
                    key={fps.val}
                    type="button"
                    onClick={() => updateSetting("targetFps", fps.val)}
                    className={`rounded-xl border py-2 font-bold transition-all ${
                      settings.targetFps === fps.val
                        ? "border-cyan-400 bg-cyan-400/20 text-cyan-200 shadow-[0_0_15px_rgba(34,211,238,0.3)]"
                        : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-white"
                    }`}
                  >
                    {fps.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Setting 3: Hardware Diagnostics Cache */}
            <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 flex items-center justify-between">
              <div>
                <span className="font-semibold text-slate-200 block">Reset Hardware Cache</span>
                <span className="text-slate-400 text-[11px] block mt-0.5">
                  Clears locally saved diagnostic rig specifications.
                </span>
              </div>
              <button
                type="button"
                onClick={handleResetRig}
                className="flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 font-semibold text-rose-300 transition-colors hover:bg-rose-500/20 hover:text-rose-200"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>{clearedFeedback ? "Cleared!" : "Reset"}</span>
              </button>
            </div>
          </div>

          {/* Footer & Feedback */}
          <div className="mt-4 flex items-center justify-between border-t border-white/10 pt-4">
            <span className="text-[11px] text-cyan-400 font-medium h-4 flex items-center gap-1">
              {savedFeedback && (
                <>
                  <Check className="h-3.5 w-3.5" /> Preference saved
                </>
              )}
            </span>
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
