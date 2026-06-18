import React, { useState, useEffect, useCallback, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { User, X, Mail, Lock, LogIn, Eye, EyeOff } from "lucide-react";

/**
 * LoginButton — Fixed top-right login button that opens a small login modal.
 *
 * This is a frontend placeholder only — no real auth logic is implemented.
 * The login form is purely visual and will be wired up later.
 */

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.15 } },
};

const panelVariants = {
  hidden: { opacity: 0, scale: 0.9, y: -10 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] },
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: -8,
    transition: { duration: 0.15, ease: "easeIn" },
  },
};

function LoginButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [isOpen, close]);

  return (
    <>
      {/* Trigger Button — top right */}
      <button
        type="button"
        onClick={open}
        className="fixed right-6 top-6 z-50 inline-flex items-center gap-2 rounded-2xl border border-slate-600/30 bg-slate-950/70 px-4 py-2.5 text-sm font-bold text-slate-300 shadow-[0_0_20px_rgba(139,92,246,0.12)] backdrop-blur-xl transition-all duration-300 hover:-translate-y-0.5 hover:border-violet-400/40 hover:bg-slate-900/80 hover:text-white hover:shadow-[0_0_30px_rgba(139,92,246,0.25)] active:scale-[0.97]"
        aria-label="Open login"
      >
        <User className="h-4 w-4" />
        Sign In
      </button>

      {/* Login Modal */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="login-overlay"
            variants={overlayVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={close}
            className="fixed inset-0 z-[110] flex items-start justify-end bg-black/50 px-4 pt-20 backdrop-blur-sm sm:px-6"
          >
            <motion.div
              key="login-panel"
              variants={panelVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm overflow-hidden rounded-2xl border border-slate-700/50 bg-slate-950/95 shadow-[0_0_60px_rgba(139,92,246,0.1),0_20px_40px_rgba(0,0,0,0.5)] backdrop-blur-2xl"
            >
              {/* Header */}
              <div className="relative border-b border-slate-800/60 px-6 pb-5 pt-6">
                <button
                  type="button"
                  onClick={close}
                  className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-lg border border-slate-700/40 bg-slate-900/60 text-slate-500 transition hover:border-red-400/30 hover:text-red-300"
                  aria-label="Close login"
                >
                  <X className="h-3.5 w-3.5" />
                </button>

                <div className="mb-3 grid h-11 w-11 place-items-center rounded-xl border border-violet-400/20 bg-violet-500/10 shadow-[0_0_20px_rgba(139,92,246,0.15)]">
                  <LogIn className="h-5 w-5 text-violet-300" />
                </div>
                <h2 className="text-lg font-black text-white">Welcome Back</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Sign in to save your rig profile & preferences
                </p>
              </div>

              {/* Form */}
              <div className="space-y-4 px-6 py-5">
                {/* Email */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    <Mail className="h-3 w-3 text-violet-400" />
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    className="w-full rounded-lg border border-slate-800 bg-slate-900/60 px-3.5 py-2.5 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-violet-400/50 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.08)]"
                  />
                </div>

                {/* Password */}
                <div className="space-y-1.5">
                  <label className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    <Lock className="h-3 w-3 text-violet-400" />
                    Password
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full rounded-lg border border-slate-800 bg-slate-900/60 px-3.5 py-2.5 pr-10 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-violet-400/50 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.08)]"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Forgot password */}
                <div className="flex justify-end">
                  <button
                    type="button"
                    className="text-[11px] font-semibold text-violet-400/70 transition hover:text-violet-300"
                  >
                    Forgot password?
                  </button>
                </div>

                {/* Submit */}
                <button
                  type="button"
                  className="mt-1 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-violet-500 text-sm font-black text-white shadow-[0_0_25px_rgba(139,92,246,0.35)] transition-all duration-200 hover:-translate-y-0.5 hover:from-violet-500 hover:to-violet-400 hover:shadow-[0_0_35px_rgba(139,92,246,0.5)] active:scale-[0.98]"
                >
                  <LogIn className="h-4 w-4" />
                  Sign In
                </button>
              </div>

              {/* Divider */}
              <div className="flex items-center gap-3 px-6">
                <div className="h-px flex-1 bg-slate-800" />
                <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                  or continue with
                </span>
                <div className="h-px flex-1 bg-slate-800" />
              </div>

              {/* Social buttons (placeholders) */}
              <div className="flex gap-3 px-6 py-4">
                <button
                  type="button"
                  className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-800 bg-slate-900/50 text-xs font-bold text-slate-300 transition hover:border-slate-700 hover:bg-slate-800/60"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                  </svg>
                  Google
                </button>
                <button
                  type="button"
                  className="flex h-10 flex-1 items-center justify-center gap-2 rounded-lg border border-slate-800 bg-slate-900/50 text-xs font-bold text-slate-300 transition hover:border-slate-700 hover:bg-slate-800/60"
                >
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2a10 10 0 0 0-9.96 9.04l5.35 2.21a2.83 2.83 0 0 1 1.6-.49c.06 0 .11 0 .17.01l2.4-3.47v-.05a3.77 3.77 0 1 1 3.77 3.77h-.09l-3.41 2.44c0 .08.01.16.01.24a2.84 2.84 0 0 1-5.66.29L2.1 14.46A10 10 0 1 0 12 2zm-5.84 14.3l-1.71-.71a2.13 2.13 0 0 0 3.87.84 2.13 2.13 0 0 0-1.03-2.83l1.77.73a1.57 1.57 0 1 1-2.9 1.97zm9.6-5.05a2.52 2.52 0 1 0-2.52-2.52 2.52 2.52 0 0 0 2.52 2.52z" />
                  </svg>
                  Steam
                </button>
              </div>

              {/* Footer */}
              <div className="border-t border-slate-800/60 px-6 py-4 text-center">
                <p className="text-xs text-slate-500">
                  Don't have an account?{" "}
                  <button type="button" className="font-bold text-violet-400 transition hover:text-violet-300">
                    Sign Up
                  </button>
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default memo(LoginButton);
