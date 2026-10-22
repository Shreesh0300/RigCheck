import React, { useState, useEffect, useCallback } from "react";
import BackgroundVideoLayer from "./BackgroundVideoLayer.jsx";
import HeroSection from "./HeroSection.jsx";
import GenreDiscovery from "./GenreDiscovery.jsx";
import GameGallery from "./GameGallery.jsx";
import FloatingCTA from "./FloatingCTA.jsx";
import SearchBar from "./SearchBar.jsx";
import DiagnosticModal from "./DiagnosticModal.jsx";
import GameDetailModal from "./GameDetailModal.jsx";
import LandingPage from "./LandingPage.jsx";
import ProfileDropdown from "./ProfileDropdown.jsx";
import ProfileModal from "./ProfileModal.jsx";
import SettingsModal from "./SettingsModal.jsx";

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
 *  - isLoggedIn: authenticated session status
 *  - currentUser: verified MongoDB user record
 *  - showDiagnostic: controls the diagnostic modal visibility
 *  - activeGenre: tracks hovered genre → drives background video crossfade
 *  - selectedGenre: the genre filter applied to the game gallery
 *  - selectedGame: tracks the clicked game to show details
 */

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [showDiagnostic, setShowDiagnostic] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);

  // Genre hover state — drives background video crossfade
  const [activeGenre, setActiveGenre] = useState(null);

  // Active genre filter for game gallery
  const [selectedGenre, setSelectedGenre] = useState(null);

  // Search query
  const [searchQuery, setSearchQuery] = useState("");

  // Total loaded games
  const [totalGames, setTotalGames] = useState(0);

  // Active game for detail modal
  const [selectedGame, setSelectedGame] = useState(null);

  // Check existing session on initial load
  useEffect(() => {
    let isMounted = true;
    async function checkExistingSession() {
      try {
        const res = await fetch("/auth/me");
        if (res.ok) {
          const data = await res.json();
          if (isMounted && data.authenticated && data.user) {
            setCurrentUser(data.user);
            setIsLoggedIn(true);
          }
        }
      } catch (err) {
        // Unauthenticated or network issue
      } finally {
        if (isMounted) setAuthChecking(false);
      }
    }
    checkExistingSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleLogin = useCallback((userData) => {
    setCurrentUser(userData);
    setIsLoggedIn(true);
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } catch (e) {
      // Ignore network errors on logout
    }
    setCurrentUser(null);
    setIsLoggedIn(false);
    setShowProfileModal(false);
    setShowSettingsModal(false);
  }, []);

  const openProfile = useCallback(() => setShowProfileModal(true), []);
  const closeProfile = useCallback(() => setShowProfileModal(false), []);
  const openSettings = useCallback(() => setShowSettingsModal(true), []);
  const closeSettings = useCallback(() => setShowSettingsModal(false), []);

  const openDiagnostic = useCallback(() => setShowDiagnostic(true), []);
  const closeDiagnostic = useCallback(() => setShowDiagnostic(false), []);
  const handleGenreHover = useCallback((genre) => setActiveGenre(genre), []);
  const handleGenreSelect = useCallback((genre) => setSelectedGenre(genre), []);
  const handleClearGenre = useCallback(() => setSelectedGenre(null), []);

  const handleGameClick = useCallback((game) => {
    setShowDiagnostic(false);
    setSelectedGame(game);
  }, []);

  const closeGameDetail = useCallback(() => setSelectedGame(null), []);

  if (authChecking) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent shadow-[0_0_20px_rgba(34,211,238,0.3)]" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return <LandingPage onLogin={handleLogin} />;
  }

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
        searchQuery={searchQuery}
        onClearGenre={handleClearGenre}
        onGameClick={handleGameClick}
        onGamesLoaded={setTotalGames}
      />

      {/* Floating "Ask RigCheck AI" Button */}
      <FloatingCTA onClick={openDiagnostic} />

      {/* Search Bar — top right next to user profile */}
      <SearchBar searchQuery={searchQuery} setSearchQuery={setSearchQuery} totalGames={totalGames} />

      {/* Account Profile Dropdown — top right */}
      <div className="fixed right-6 top-6 z-50">
        <ProfileDropdown
          currentUser={currentUser}
          onOpenProfile={openProfile}
          onOpenSettings={openSettings}
          onLogout={handleLogout}
        />
      </div>

      {/*
        ── Diagnostic Modal (renders first = lower in paint order) ──
        Must render BEFORE GameDetailModal so that when a game is selected
        from within it, the GameDetailModal (rendered after) naturally sits
        on top without any z-index conflicts.
      */}
      <DiagnosticModal isOpen={showDiagnostic} onClose={closeDiagnostic} onGameClick={handleGameClick} />

      {/*
        ── Game Detail Modal (renders last = highest in paint order) ──
        Driven entirely by `selectedGame` prop.
        - When selectedGame changes while already open, content updates in-place.
        - Clicking any game (gallery, diagnostic hero, or "You Might Also Like")
          calls handleGameClick which closes DiagnosticModal and sets selectedGame,
          so this modal is always the sole visible overlay.
      */}
      <GameDetailModal
        game={selectedGame}
        onClose={closeGameDetail}
        onOpenDiagnostic={openDiagnostic}
      />

      {/* Profile Modal */}
      <ProfileModal
        isOpen={showProfileModal}
        onClose={closeProfile}
        currentUser={currentUser}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettingsModal}
        onClose={closeSettings}
      />
    </main>
  );
}
