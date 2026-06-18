import React, { useState, useCallback } from "react";
import BackgroundVideoLayer from "./BackgroundVideoLayer.jsx";
import HeroSection from "./HeroSection.jsx";
import GenreDiscovery from "./GenreDiscovery.jsx";
import GameGallery from "./GameGallery.jsx";
import FloatingCTA from "./FloatingCTA.jsx";
import LoginButton from "./LoginButton.jsx";
import DiagnosticModal from "./DiagnosticModal.jsx";
import GameDetailModal from "./GameDetailModal.jsx";

/**
 * App — Root application component.
 *
 * Page Flow:
 *   0. BackgroundVideoLayer — fullscreen cinematic video behind all content
 *   1. HeroSection          — full-viewport RigCheck branding + "Browse Genres" CTA
 *   2. GenreDiscovery       — 6 cinematic genre tiles (hover → video, click → filter + scroll)
 *   3. GameGallery          — filterable game grid
 *   4. FloatingCTA          — "Ask RigCheck AI" button
 *   5. DiagnosticModal      — system diagnostic overlay
 *   6. GameDetailModal      — cinematic game detail overlay
 *
 * State:
 *  - showDiagnostic: controls the diagnostic modal visibility
 *  - activeGenre: tracks hovered genre → drives background video crossfade
 *  - selectedGenre: the genre filter applied to the game gallery
 *  - selectedGame: tracks the clicked game to show details
 */

export default function App() {
  const [showDiagnostic, setShowDiagnostic] = useState(false);

  // Genre hover state — drives background video crossfade
  const [activeGenre, setActiveGenre] = useState(null);

  // Active genre filter for game gallery
  const [selectedGenre, setSelectedGenre] = useState(null);

  // Active game for detail modal
  const [selectedGame, setSelectedGame] = useState(null);

  const openDiagnostic = useCallback(() => setShowDiagnostic(true), []);
  const closeDiagnostic = useCallback(() => setShowDiagnostic(false), []);
  const handleGenreHover = useCallback((genre) => setActiveGenre(genre), []);
  const handleGenreSelect = useCallback((genre) => setSelectedGenre(genre), []);
  const handleClearGenre = useCallback(() => setSelectedGenre(null), []);
  const handleGameClick = useCallback((game) => setSelectedGame(game), []);
  const closeGameDetail = useCallback(() => setSelectedGame(null), []);

  return (
    <main className="min-h-screen font-['Inter',ui-sans-serif,system-ui,sans-serif] text-slate-100">
      {/* ── Background Video Layer ── */}
      <BackgroundVideoLayer activeGenre={activeGenre} />

      {/* ── Section 1: Hero ── */}
      <HeroSection />

      {/* ── Section 2: Genre Discovery ── */}
      <GenreDiscovery
        onGenreHover={handleGenreHover}
        onGenreSelect={handleGenreSelect}
      />

      {/* ── Section 3: Game Gallery ── */}
      <GameGallery
        onGenreHover={handleGenreHover}
        selectedGenre={selectedGenre}
        onClearGenre={handleClearGenre}
        onGameClick={handleGameClick}
      />

      {/* ── Game Detail Modal ── */}
      <GameDetailModal 
        game={selectedGame}
        onClose={closeGameDetail}
        onOpenDiagnostic={openDiagnostic}
      />

      {/* Floating "Ask RigCheck AI" Button */}
      <FloatingCTA onClick={openDiagnostic} />

      {/* Login Button — top right */}
      <LoginButton />

      {/* Diagnostic Modal — wraps existing RigCheckDashboard */}
      <DiagnosticModal isOpen={showDiagnostic} onClose={closeDiagnostic} />
    </main>
  );
}
