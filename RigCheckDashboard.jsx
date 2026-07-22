import React, { useState, useCallback, useEffect } from "react";
import {
  Cpu,
  Gamepad2,
  Gauge,
  Loader2,
  Monitor,
  Search,
  Sparkles,
  Zap,
  Check,
  ChevronDown,
  AlertTriangle,
  Frown,
  ExternalLink,
  HardDrive,
} from "lucide-react";
import GAMES from "./src/gameData.js";

/* ─── Helpers ──────────────────────────────────────────────────────── */

function getComponentStatusLabel(component, data) {
  if (!data) return "N/A";
  if (component === "gpu" || component === "cpu") {
    if (data.status === "BELOW_RECOMMENDED") return "Below Recommended";
    if (data.status === "BELOW_MINIMUM") return "Below Minimum";
    return "Excellent";
  }
  if (component === "ram") {
    if (data.status === "FAIL") {
      return data.label ? data.label.replace("❌ ", "").trim() : "Need More RAM";
    }
    return "Enough";
  }
  if (component === "storage") {
    if (data.status === "FAIL") {
      if (data.detail) {
        let msg = data.detail.replace("❌ ", "").trim();
        return msg.replace(/\b[a-z]/g, (char) => char.toUpperCase());
      }
      return "Need More Free Storage";
    }
    return "Enough";
  }
  return "PASS";
}

function getComponentStatusColor(component, data) {
  if (!data) return "text-slate-400";
  if (data.status === "PASS") return "text-emerald-400";
  if (data.status === "BELOW_RECOMMENDED") return "text-amber-400";
  if (data.status === "BELOW_MINIMUM") return "text-rose-500";
  if (data.status === "FAIL") return "text-rose-500";
  return "text-slate-400";
}

/**
 * Returns true only when ALL four compatibility categories are passing (no red status).
 * Red statuses: BELOW_MINIMUM (GPU/CPU) and FAIL (RAM/Storage).
 * BELOW_RECOMMENDED (amber) is a warning but not a blocker for hardware advice.
 * Hardware Advice is only meaningful when the rig can fully run the game.
 */
function allComponentsPass(compat) {
  if (!compat) return false;
  const isRed = (data) => data && (data.status === "BELOW_MINIMUM" || data.status === "FAIL");
  return !isRed(compat.gpu) && !isRed(compat.cpu) && !isRed(compat.ram) && !isRed(compat.storage);
}

/* ─── Constants ────────────────────────────────────────────────────── */

/** Map the select value to the integer the backend expects. */
const GPU_TIER_MAP = {
  "tier-1": 1,
  "tier-2": 2,
  "tier-3": 3,
  "tier-4": 4,
  "tier-5": 5,
};

/** Banner images keyed by game title. */
const GAME_IMAGES = {
  // Original 10
  "Uncharted: Legacy of Thieves Collection": "/images/uncharted.png",
  "Cities: Skylines":                        "/images/cities_skylines.png",
  "Forza Horizon 5":                         "/images/forza_horizon_5.png",
  "Resident Evil 4":                         "/images/resident_evil_village.png",
  "Resident Evil Village":                   "/images/resident_evil_village.png",
  "Slay the Spire":                          "/images/slay_the_spire.png",
  "Tekken 8":                                "/images/tekken_8.png",
  "Celeste":                                 "/images/celeste.png",
  "Crusader Kings III":                      "/images/crusader_kings.png",
  "Overcooked! 2":                           "/images/celeste.png",
  "Return of the Obra Dinn":                 "/images/dead_space_remake.png",
  // New 10
  "GTA V":                                   "/images/gta_v.png",
  "Valorant":                                "/images/valorant.png",
  "The Witcher 3":                           "/images/witcher_3.png",
  "Stardew Valley":                          "/images/stardew_valley.png",
  "Cyberpunk 2077":                          "/images/cyberpunk_2077.png",
  "Minecraft":                               "/images/minecraft.png",
  "Apex Legends":                            "/images/apex_legends.png",
  "Age of Empires IV":                       "/images/age_of_empires.png",
  "Hades":                                   "/images/hades.png",
  "Microsoft Flight Simulator":              "/images/flight_simulator.png",
  "Dead Space Remake":                       "/images/dead_space_remake.png",
  "The Last of Us Part I":                   "/images/last_of_us.png",
  "Dying Light 2":                           "/images/dying_light_2.png",
};

const FALLBACK_IMAGE = "/images/dead_space_remake.png";


/** Derive a UI-friendly FPS label from the confidence score. */
function estimateFps(confidence) {
  if (confidence >= 85) return "90+ FPS";
  if (confidence >= 70) return "60–90 FPS";
  if (confidence >= 55) return "45–60 FPS";
  if (confidence >= 40) return "30–45 FPS";
  return "30 FPS cap";
}

/** Parse the hardware_advice string from the backend into a tier label + description. */
function parseHardwareAdvice(raw) {
  if (!raw) return { tier: "N/A", detail: "No hardware advice available." };
  // The backend returns e.g. "ULTRA: You can max out every setting. Enjoy the eye-candy!"
  const match = raw.match(/^([A-Z/]+):\s*(.+)$/);
  if (match) return { tier: match[1].trim(), detail: match[2].trim() };
  return { tier: "", detail: raw };
}

/** Format a number with Indian-locale commas, e.g. 4000 → "4,000" */
function fmt(n) {
  return n.toLocaleString("en-IN");
}

/**
 * Format a game's actual price_inr from the backend response.
 * Never falls back to user budget — only uses the game's own price.
 */
function formatGamePrice(priceInr) {
  if (priceInr === null || priceInr === undefined) return "Price Unavailable";
  if (priceInr === 0) return "Free to Play";
  return `\u20B9${fmt(priceInr)}`;
}

/* ─── Sub-Components ───────────────────────────────────────────────── */

/* ─── Persisted Input State ───────────────────────────────────────────
 * Module-level singleton — survives component unmount/remount.
 * Ensures "Re-Run PC Diagnostic" always restores the user's last-entered
 * values instead of resetting to demo defaults.
 * ─────────────────────────────────────────────────────────────────── */
let _persistedInputs = {
  vibeQuery:   "I want a horror survival game with zombies",
  maxBudget:   4000,
  gpuModel:    "RTX 4050",
  ramSize:     32,
  cpuModel:    "Intel Core i5-12400F",
  freeStorage: 256,
};

function MatchRing({ value = 0 }) {
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative grid h-24 w-24 shrink-0 place-items-center rounded-full bg-slate-950/60 shadow-[0_0_35px_rgba(34,211,238,0.3)]">
      <svg className="absolute inset-0 h-full w-full -rotate-90" viewBox="0 0 96 96">
        <circle cx="48" cy="48" r={radius} fill="none" stroke="rgba(30,41,59,0.95)" strokeWidth="7" />
        <circle
          cx="48"
          cy="48"
          r={radius}
          fill="none"
          stroke="url(#matchGrad)"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
        <defs>
          <linearGradient id="matchGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="50%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#22d3ee" />
          </linearGradient>
        </defs>
      </svg>
      <div className="text-center leading-none">
        <div className="text-2xl font-black text-cyan-100">{value}%</div>
        <div className="mt-0.5 text-[10px] font-bold uppercase tracking-widest text-cyan-400">Match</div>
      </div>
    </div>
  );
}

function Pill({ children }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-cyan-400/15 bg-slate-800/60 px-2.5 py-1 text-[11px] font-semibold text-slate-300">
      <Check className="h-3 w-3 text-emerald-400" />
      {children}
    </span>
  );
}

/** Inline SVG Steam logo – avoids an external dependency. */
function SteamLogo({ className = "h-4 w-4" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2a10 10 0 0 0-9.96 9.04l5.35 2.21a2.83 2.83 0 0 1 1.6-.49c.06 0 .11 0 .17.01l2.4-3.47v-.05a3.77 3.77 0 1 1 3.77 3.77h-.09l-3.41 2.44c0 .08.01.16.01.24a2.84 2.84 0 0 1-5.66.29L2.1 14.46A10 10 0 1 0 12 2zm-5.84 14.3l-1.71-.71a2.13 2.13 0 0 0 3.87.84 2.13 2.13 0 0 0-1.03-2.83l1.77.73a1.57 1.57 0 1 1-2.9 1.97zm9.6-5.05a2.52 2.52 0 1 0-2.52-2.52 2.52 2.52 0 0 0 2.52 2.52z" />
    </svg>
  );
}

/** "View on Steam" / "Get the Game" button for the hero card. */
function StoreButton({ url }) {
  if (!url) return null;
  const isSteam = url.includes("store.steampowered.com");
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-4 inline-flex items-center gap-2 rounded-lg border border-[#66c0f4]/30 bg-gradient-to-r from-[#1b2838] to-[#2a475e] px-4 py-2.5 text-xs font-bold uppercase tracking-wide text-white shadow-lg shadow-[#1b2838]/40 transition-all duration-200 hover:-translate-y-0.5 hover:border-[#66c0f4]/60 hover:shadow-[0_8px_24px_rgba(102,192,244,0.25)]"
    >
      <SteamLogo className="h-4 w-4" />
      {isSteam ? "View on Steam" : "Get the Game"}
      <ExternalLink className="h-3 w-3 opacity-50" />
    </a>
  );
}

/** Smaller Steam link for alternative game cards. */
function AltStoreLink({ url }) {
  if (!url) return null;
  const isSteam = url.includes("store.steampowered.com");
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-full border border-[#66c0f4]/20 bg-[#1b2838]/60 px-2.5 py-1 text-[10px] font-semibold text-[#66c0f4] transition hover:border-[#66c0f4]/50 hover:bg-[#2a475e]/80"
    >
      <SteamLogo className="h-3 w-3" />
      {isSteam ? "Steam" : "Store"}
    </a>
  );
}

/** Shown when there are no results yet (initial state). */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700/60 bg-slate-950/40 px-8 py-20 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl border border-cyan-400/15 bg-cyan-400/5">
        <Sparkles className="h-6 w-6 text-cyan-400/60" />
      </div>
      <h3 className="text-base font-bold text-slate-300">Ready to Diagnose</h3>
      <p className="mt-2 max-w-sm text-xs leading-relaxed text-slate-500">
        Describe your vibe, set your hardware specs, and hit{" "}
        <span className="font-bold text-cyan-400">Run Diagnostics</span> to get personalised game
        recommendations from the RigCheck engine.
      </p>
    </div>
  );
}

/** Shown when the API returned an error or no match. */
function ErrorState({ message }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-amber-500/20 bg-amber-950/10 px-8 py-16 text-center">
      <Frown className="mb-3 h-10 w-10 text-amber-400/70" />
      <h3 className="text-base font-bold text-amber-300">No Match Found</h3>
      <p className="mt-2 max-w-md text-xs leading-relaxed text-slate-400">{message}</p>
    </div>
  );
}

/* ─── Main Dashboard ───────────────────────────────────────────────── */

export default function RigCheckDashboard({ onGameClick }) {
  /* ── Input State — initialised from persisted values so reopening the
     diagnostic always restores what the user last typed. ── */
  const [vibeQuery,   setVibeQuery]   = useState(_persistedInputs.vibeQuery);
  const [maxBudget,   setMaxBudget]   = useState(_persistedInputs.maxBudget);
  const [gpuModel,    setGpuModel]    = useState(_persistedInputs.gpuModel);
  const [ramSize,     setRamSize]     = useState(_persistedInputs.ramSize);
  const [cpuModel,    setCpuModel]    = useState(_persistedInputs.cpuModel);
  const [freeStorage, setFreeStorage] = useState(_persistedInputs.freeStorage);
  const [isLoading,   setIsLoading]   = useState(false);

  /* ── Persist inputs to module-level state on every change.
     This survives DiagnosticModal open/close cycles (component unmount). ── */
  useEffect(() => {
    _persistedInputs = { vibeQuery, maxBudget, gpuModel, ramSize, cpuModel, freeStorage };
  }, [vibeQuery, maxBudget, gpuModel, ramSize, cpuModel, freeStorage]);

  /* ── Result State (populated from the backend response) ── */
  const [result, setResult] = useState(null);    // full API response object
  const [error, setError] = useState(null);       // error message string

  /* ── Call the FastAPI backend ── */
  const runDiagnostics = useCallback(async () => {
    if (!vibeQuery.trim()) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    const payload = {
      description: vibeQuery.trim(),
      budget: maxBudget,
      gpu_name: gpuModel.trim(),
      ram: ramSize,
      cpu_name: cpuModel.trim() || null,
      storage_gb: freeStorage,
    };

    try {
      // In dev, Vite proxies /recommend → http://127.0.0.1:8000/recommend
      // In production, adjust this URL to wherever the FastAPI server is hosted.
      const response = await fetch("/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || `Server error (${response.status})`);
      }

      const data = await response.json();

      // If the engine found no match it returns an empty recommended_game
      if (!data.recommended_game) {
        setError(data.description || data.message || "No games match your criteria.");
      } else {
        setResult(data);
      }
    } catch (err) {
      setError(err.message || "Could not reach the RigCheck backend.");
    } finally {
      setIsLoading(false);
    }
  }, [vibeQuery, maxBudget, gpuModel, ramSize, cpuModel, freeStorage]);

  /* ── Derived values from the result ── */
  const confidence    = result?.confidence ?? 0;
  const fpsLabel      = result ? estimateFps(confidence) : "";
  const advice        = result ? parseHardwareAdvice(result.hardware_advice) : null;
  const heroImage     = result ? (GAME_IMAGES[result.recommended_game] || FALLBACK_IMAGE) : null;
  const alternatives  = result?.alternative_games ?? [];

  return (
    <main className="min-h-screen bg-[#02040a] font-['Inter',ui-sans-serif,system-ui,sans-serif] text-slate-100">
      <div className="flex min-h-screen flex-col lg:flex-row">
        {/* ───────── LEFT PANEL (Input) ───────── */}
        <aside className="flex w-full flex-col border-b border-slate-800/70 bg-slate-950/90 px-5 py-6 shadow-[inset_-1px_0_0_rgba(148,163,184,0.06)] lg:min-h-screen lg:w-[260px] lg:border-b-0 lg:border-r lg:px-5 lg:py-7">
          {/* Logo */}
          <div className="mb-8 flex items-center gap-3">
            <div className="relative grid h-10 w-10 place-items-center rounded-xl border border-cyan-400/20 bg-cyan-400/10 shadow-[0_0_22px_rgba(34,211,238,0.15)]">
              <Gamepad2 className="h-5 w-5 text-cyan-300" />
              <Sparkles className="absolute -right-1 -top-1 h-3.5 w-3.5 rounded-full bg-violet-500 p-0.5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-white">RigCheck AI</h1>
              <p className="text-[10px] font-semibold text-slate-500">Gaming Concierge</p>
            </div>
          </div>

          {/* Inputs */}
          <div className="space-y-6">
            {/* Vibe Query */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
                <Search className="h-3.5 w-3.5 text-cyan-400" />
                Describe your vibe...
              </label>
              <textarea
                value={vibeQuery}
                onChange={(e) => setVibeQuery(e.target.value)}
                rows={3}
                className="w-full resize-none rounded-lg border border-slate-800 bg-slate-900/60 px-3.5 py-3 text-sm leading-relaxed text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.07)]"
                placeholder="Tell RigCheck what you want to play..."
              />
            </div>

            {/* Max Budget — plain numeric input, no slider */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
                <Zap className="h-3.5 w-3.5 text-cyan-400" />
                Max Budget
              </label>
              <div className="relative">
                <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs font-bold text-cyan-400">₹</span>
                <input
                  type="number"
                  value={maxBudget}
                  onChange={(e) => setMaxBudget(Math.max(0, Number(e.target.value) || 0))}
                  placeholder="e.g. 3500"
                  min={0}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2 pl-7 pr-3 text-xs font-semibold text-slate-200 outline-none transition focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.07)]"
                />
              </div>
            </div>

            {/* GPU Model */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
                <Gauge className="h-3.5 w-3.5 text-cyan-400" />
                Graphics Card
              </label>
              <input
                type="text"
                value={gpuModel}
                onChange={(e) => setGpuModel(e.target.value)}
                placeholder="e.g. RTX 4050"
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 outline-none transition focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.07)]"
              />
            </div>

            {/* RAM Input */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
                <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                Installed RAM (GB)
              </label>
              <input
                type="number"
                value={ramSize}
                onChange={(e) => setRamSize(Number(e.target.value))}
                placeholder="e.g. 16"
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 outline-none transition focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.07)]"
              />
            </div>

            {/* CPU Model */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
                <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                CPU Model
              </label>
              <input
                type="text"
                value={cpuModel}
                onChange={(e) => setCpuModel(e.target.value)}
                placeholder="e.g. Core i5-12400F"
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 outline-none transition focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.07)]"
              />
            </div>

            {/* Free Storage Input */}
            <div className="space-y-2">
              <label className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-slate-300">
                <HardDrive className="h-3.5 w-3.5 text-cyan-400" />
                Free Storage (GB)
              </label>
              <input
                type="number"
                value={freeStorage}
                onChange={(e) => setFreeStorage(Number(e.target.value))}
                placeholder="e.g. 250"
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs font-semibold text-slate-200 outline-none transition focus:border-cyan-400/60 focus:shadow-[0_0_0_3px_rgba(34,211,238,0.07)]"
              />
            </div>
          </div>

          {/* CTA */}
          <button
            type="button"
            onClick={runDiagnostics}
            disabled={isLoading || !vibeQuery.trim()}
            className="mt-8 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-cyan-500 text-sm font-black text-slate-950 shadow-[0_0_28px_rgba(6,182,212,0.5)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-cyan-300 hover:shadow-[0_0_40px_rgba(34,211,238,0.7)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60 lg:mt-auto"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isLoading ? "Running Diagnostics..." : "Run Diagnostics"}
          </button>
        </aside>

        {/* ───────── RIGHT PANEL (Results) ───────── */}
        <section className="flex-1 overflow-y-auto bg-[radial-gradient(circle_at_50%_0%,rgba(14,165,233,0.06),transparent_36%),radial-gradient(circle_at_70%_55%,rgba(124,58,237,0.06),transparent_28%),#02040a] p-5 sm:p-6 lg:p-7">
          {/* Header */}
          <div className="mb-5 flex items-center gap-2.5">
            <div className="grid h-7 w-7 place-items-center rounded-lg border border-violet-400/20 bg-violet-500/15 shadow-[0_0_18px_rgba(139,92,246,0.2)]">
              <Sparkles className="h-3.5 w-3.5 text-violet-300" />
            </div>
            <h2 className="text-sm font-black text-white">Diagnostic Results</h2>
          </div>

          {/* ─── Empty / Error / Result states ─── */}
          {!result && !error && !isLoading && <EmptyState />}
          {error && <ErrorState message={error} />}
          {isLoading && (
            <div className="flex flex-col items-center justify-center rounded-xl border border-slate-800/60 bg-slate-950/50 px-8 py-24">
              <Loader2 className="mb-4 h-10 w-10 animate-spin text-cyan-400" />
              <p className="text-sm font-bold text-slate-400">Analyzing your rig &amp; vibe...</p>
            </div>
          )}

          {result && !isLoading && (
            <>
              {/* ── Hero Result Card ── */}
              <article
                className="overflow-hidden rounded-xl border border-slate-800/80 bg-slate-950/80 shadow-2xl shadow-black/40 cursor-pointer hover:border-cyan-400/30 transition-all duration-200"
                onClick={() => {
                  if (onGameClick) {
                    const staticGame = GAMES.find((g) => g.title === result.recommended_game);
                    if (staticGame) {
                      onGameClick({
                        ...staticGame,
                        // Merge backend price_inr so GameDetailModal shows the real game price,
                        // independent of the user's Max Budget input.
                        price_inr: result.price_inr,
                        compatibility: result.compatibility,
                      });
                    }
                  }
                }}
              >
                {/* Banner Image */}
                <div
                  className="relative h-[180px] bg-cover bg-center sm:h-[200px]"
                  style={{ backgroundImage: `url(${heroImage})` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-b from-black/30 via-transparent to-[#02040a]/90" />
                  <div className="absolute inset-0 bg-gradient-to-r from-[#02040a]/60 via-transparent to-[#02040a]/40" />

                  <div className="relative z-10 flex items-start justify-between p-4">
                    <span className="inline-flex items-center gap-1 rounded-full bg-cyan-400 px-2.5 py-1 text-[10px] font-black uppercase text-slate-950 shadow-[0_0_18px_rgba(34,211,238,0.5)]">
                      <Sparkles className="h-3 w-3" />
                      Top Pick
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-slate-900/70 px-2 py-1 text-[10px] font-bold text-cyan-300 backdrop-blur-sm">
                        {result.compatibility ? `${result.compatibility.estimated_fps} FPS` : fpsLabel}
                      </span>
                      <span className="rounded-md bg-black/70 px-2.5 py-1.5 text-xs font-black text-white backdrop-blur-sm">
                        {formatGamePrice(result.price_inr)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Info */}
                <div className="px-5 pb-5 pt-4 sm:px-6">
                  <div className="flex items-start justify-between gap-6">
                    <div className="min-w-0 flex-1">
                      <h3 className="text-xl font-black tracking-tight text-white sm:text-2xl">
                        {result.recommended_game}
                      </h3>
                      <p className="mt-2.5 text-xs leading-relaxed text-slate-400 sm:text-sm sm:leading-relaxed">
                        {result.description}
                      </p>

                      {/* Match Details (keyword pills) */}
                      {result.matched_keywords?.length > 0 && (
                        <div className="mt-4">
                          <p className="mb-2 flex items-center gap-1.5 text-[11px] font-black text-slate-200">
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                            Match Details
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {result.matched_keywords.map((kw) => (
                              <Pill key={kw}>{kw}</Pill>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Steam store link */}
                      <StoreButton url={result.store_url} />
                    </div>

                    {/* Match Ring */}
                    <div className="hidden sm:block">
                      <MatchRing value={result.compatibility ? result.compatibility.compatibility_pct : confidence} />
                    </div>
                  </div>

                  {/* Mobile ring */}
                  <div className="mt-5 flex justify-center sm:hidden">
                    <MatchRing value={result.compatibility ? result.compatibility.compatibility_pct : confidence} />
                  </div>
                </div>

                {/* Compatibility Block */}
                {result.compatibility && (
                  <div className="border-t border-slate-800/60 px-5 py-4 sm:px-6 space-y-3 bg-slate-900/20">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-slate-400">Overall Compatibility</span>
                      <span className="text-sm font-black text-cyan-400">{result.compatibility.compatibility_pct}%</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
                      <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-2">
                        <span className="block text-[10px] text-slate-500 font-bold uppercase">GPU</span>
                        <span className={`font-semibold ${getComponentStatusColor('gpu', result.compatibility.gpu)}`}>
                          {getComponentStatusLabel('gpu', result.compatibility.gpu)}
                        </span>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-2">
                        <span className="block text-[10px] text-slate-500 font-bold uppercase">CPU</span>
                        <span className={`font-semibold ${getComponentStatusColor('cpu', result.compatibility.cpu)}`}>
                          {getComponentStatusLabel('cpu', result.compatibility.cpu)}
                        </span>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-2">
                        <span className="block text-[10px] text-slate-500 font-bold uppercase">RAM</span>
                        <span className={`font-semibold ${getComponentStatusColor('ram', result.compatibility.ram)}`}>
                          {getComponentStatusLabel('ram', result.compatibility.ram)}
                        </span>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-2">
                        <span className="block text-[10px] text-slate-500 font-bold uppercase">Storage</span>
                        <span className={`font-semibold ${getComponentStatusColor('storage', result.compatibility.storage)}`}>
                          {getComponentStatusLabel('storage', result.compatibility.storage)}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center justify-between text-xs pt-1">
                      <span className="text-slate-400">Settings: <span className="font-bold text-white">{result.compatibility.expected_settings}</span></span>
                      <span className="text-slate-400">Est. FPS: <span className="font-bold text-white">{result.compatibility.estimated_fps} FPS</span></span>
                    </div>
                    {result.compatibility.reduction_reasons?.length > 0 && (
                      <div className="text-[11px] text-rose-400/90 leading-relaxed bg-rose-500/5 p-2 rounded-lg border border-rose-500/10">
                        <span className="font-bold block mb-0.5">Deficiency Alert:</span>
                        {result.compatibility.reduction_reasons.map((r, i) => (
                          <div key={i}>• {r}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Hardware Advice Banner — only shown when ALL four components pass (no red status).
                    A failing GPU, CPU, RAM, or Storage check means the rig can't fully run the game,
                    so hardware advice (which assumes sufficient specs) is not relevant. */}
                {advice && allComponentsPass(result.compatibility) && (
                  <div className="border-t border-slate-800/60 px-5 pb-5 sm:px-6">
                    <div className="mt-4 rounded-lg border border-cyan-400/20 bg-cyan-950/50 px-4 py-3.5 shadow-[0_0_20px_rgba(34,211,238,0.08)]">
                      <div className="flex items-start gap-3">
                        <Monitor className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" />
                        <div>
                          <p className="text-xs font-black uppercase tracking-wide text-cyan-300">
                            Hardware Advice: {advice.tier}
                          </p>
                          <p className="mt-1 text-[11px] font-medium text-cyan-100/60">
                            {advice.detail}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </article>

              {/* ── You Might Also Like ── */}
              {alternatives.length > 0 && (
                <div className="mt-6">
                  <h3 className="mb-3.5 text-sm font-black text-white">You Might Also Like</h3>
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {alternatives.map((game) => {
                      const img = GAME_IMAGES[game.title] || FALLBACK_IMAGE;
                      return (
                        <article
                          key={game.title}
                          className="group overflow-hidden rounded-xl border border-slate-800/80 bg-slate-950 shadow-lg shadow-black/30 transition-all duration-200 hover:-translate-y-0.5 hover:border-cyan-400/30 hover:shadow-cyan-400/5 cursor-pointer"
                          onClick={() => {
                            if (onGameClick) {
                              const staticGame = GAMES.find((g) => g.title === game.title);
                              if (staticGame) {
                                onGameClick({
                                  ...staticGame,
                                  // Pass the backend price_inr for this alternative game
                                  // so GameDetailModal shows the real price, not the budget.
                                  price_inr: game.price_inr,
                                  compatibility: game.compatibility,
                                });
                              }
                            }
                          }}
                        >
                          {/* Banner */}
                          <div
                            className="relative h-24 bg-cover bg-center sm:h-28"
                            style={{ backgroundImage: `url(${img})` }}
                          >
                            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-[#02040a]/95" />
                            <div className="absolute inset-0 bg-gradient-to-r from-[#02040a]/30 via-transparent to-transparent" />

                            {/* Confidence badge */}
                            {game.confidence > 0 && (
                              <span className="absolute right-2 top-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[10px] font-bold text-cyan-300 backdrop-blur-sm">
                                {game.compatibility ? `${game.compatibility.compatibility_pct}% Match` : `${game.confidence}% Match`}
                              </span>
                            )}

                            <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 p-3">
                              <h4 className="line-clamp-1 text-xs font-black text-white">
                                {game.title}
                              </h4>
                            </div>
                          </div>

                          {/* Compatibility Block */}
                          {game.compatibility && (
                            <div className="px-3 pb-3 pt-2 border-t border-slate-900 bg-slate-900/10 space-y-2 text-[11px]">
                              <div className="flex justify-between items-center">
                                <span className="text-slate-500">Compatibility:</span>
                                <span className="font-bold text-cyan-400">{game.compatibility.compatibility_pct}%</span>
                              </div>
                              <div className="grid grid-cols-2 gap-1.5">
                                <div className="p-1.5 rounded bg-slate-950/30 border border-slate-900">
                                  <span className="block text-[9px] text-slate-600 font-bold">GPU</span>
                                  <span className={`font-medium ${getComponentStatusColor('gpu', game.compatibility.gpu)}`}>
                                    {getComponentStatusLabel('gpu', game.compatibility.gpu)}
                                  </span>
                                </div>
                                <div className="p-1.5 rounded bg-slate-950/30 border border-slate-900">
                                  <span className="block text-[9px] text-slate-600 font-bold">CPU</span>
                                  <span className={`font-medium ${getComponentStatusColor('cpu', game.compatibility.cpu)}`}>
                                    {getComponentStatusLabel('cpu', game.compatibility.cpu)}
                                  </span>
                                </div>
                                <div className="p-1.5 rounded bg-slate-950/30 border border-slate-900">
                                  <span className="block text-[9px] text-slate-600 font-bold">RAM</span>
                                  <span className={`font-medium ${getComponentStatusColor('ram', game.compatibility.ram)}`}>
                                    {getComponentStatusLabel('ram', game.compatibility.ram)}
                                  </span>
                                </div>
                                <div className="p-1.5 rounded bg-slate-950/30 border border-slate-900">
                                  <span className="block text-[9px] text-slate-600 font-bold">STORAGE</span>
                                  <span className={`font-medium ${getComponentStatusColor('storage', game.compatibility.storage)}`}>
                                    {getComponentStatusLabel('storage', game.compatibility.storage)}
                                  </span>
                                </div>
                              </div>
                              <div className="flex justify-between text-[10px] text-slate-400 pt-0.5">
                                <span>Settings: <span className="font-semibold text-white">{game.compatibility.expected_settings}</span></span>
                                <span>FPS: <span className="font-semibold text-white">{game.compatibility.estimated_fps}</span></span>
                              </div>
                            </div>
                          )}

                          {/* Tags row */}
                          {game.tags && game.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 px-3 py-2">
                              {game.tags.slice(0, 3).map((tag) => (
                                <span
                                  key={tag}
                                  className="rounded-full border border-slate-700/50 bg-slate-800/40 px-2 py-0.5 text-[9px] font-semibold text-slate-400"
                                >
                                  {tag}
                                </span>
                              ))}
                              {/* Alt store link inline with tags */}
                              <AltStoreLink url={game.store_url} />
                            </div>
                          )}

                          {/* Fallback: show store link even if no tags */}
                          {(!game.tags || game.tags.length === 0) && game.store_url && (
                            <div className="px-3 py-2">
                              <AltStoreLink url={game.store_url} />
                            </div>
                          )}
                        </article>
                      );
                    })}
                  </div>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </main>
  );
}
