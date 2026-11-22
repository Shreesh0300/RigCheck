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
import MyGamesPage from "./MyGamesPage.jsx";
import ForYouPage from "./ForYouPage.jsx";
import { LibraryProvider } from "./context/LibraryContext.jsx";
import { Gamepad2, User, X } from "lucide-react";

function getInitialView() {
  if (typeof window !== "undefined") {
    const path = window.location.pathname;
    if (path === "/for-you" || path.startsWith("/for-you")) return "for-you";
    if (path === "/my-games" || path.startsWith("/my-games")) return "my-games";
  }
  return "home";
}

/**
 * App — Root application component.
 *
 * Page Flow:
 *   0. BackgroundVideoLayer — fullscreen cinematic video behind all content
 *   1. HeroSection          — full-viewport RigCheck branding + "Browse Genres" CTA
 *   2. GenreDiscovery       — 6 cinematic genre tiles (hover → video, click → filter + scroll)
 *   3. GameGallery          — filterable game grid
 *   4. FloatingCTA          — "Ask RigCheck AI" & "For You" buttons
 *   5. DiagnosticModal      — system diagnostic overlay
 *   6. GameDetailModal      — cinematic game detail overlay
 *   7. MyGamesPage          — dedicated personal library page (Phase 2)
 *   8. ForYouPage           — personalized recommendation feed (Phase 5 & 6)
 *
 * State:
 *  - isLoggedIn: authenticated session status
 *  - currentUser: verified MongoDB user record
 *  - guestMode: allows unauthenticated visitors to browse games
 *  - currentView: "home" | "my-games" | "for-you"
 *  - showDiagnostic: controls the diagnostic modal visibility
 *  - activeGenre: tracks hovered genre → drives background video crossfade
 *  - selectedGenre: the genre filter applied to the game gallery
 *  - selectedGame: tracks the clicked game to show details
 */

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [guestMode, setGuestMode] = useState(false);
  const [currentView, setCurrentView] = useState(getInitialView);
  const [authPromptOpen, setAuthPromptOpen] = useState(false);

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

  // Navigation helper ensuring SPA URL sync without reload
  const navigateTo = useCallback((view) => {
    setCurrentView(view);
    if (typeof window !== "undefined") {
      const path = view === "home" ? "/" : `/${view}`;
      if (window.location.pathname !== path) {
        window.history.pushState({ view }, "", path);
      }
    }
  }, []);

  // Browser back/forward button synchronization
  useEffect(() => {
    const onPopState = () => {
      const path = window.location.pathname;
      if (path === "/for-you" || path.startsWith("/for-you")) {
        setCurrentView("for-you");
      } else if (path === "/my-games" || path.startsWith("/my-games")) {
        setCurrentView("my-games");
      } else {
        setCurrentView("home");
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const handleLogin = useCallback((userData) => {
    setCurrentUser(userData);
    setIsLoggedIn(true);
    setGuestMode(false);
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } catch (e) {
      // Ignore network errors on logout
    }
    setCurrentUser(null);
    setIsLoggedIn(false);
    setGuestMode(false);
    navigateTo("home");
    setShowProfileModal(false);
    setShowSettingsModal(false);
  }, [navigateTo]);

  const openProfile = useCallback(() => setShowProfileModal(true), []);
  const closeProfile = useCallback(() => setShowProfileModal(false), []);
  const openSettings = useCallback(() => setShowSettingsModal(true), []);
  const closeSettings = useCallback(() => setShowSettingsModal(false), []);

  const openDiagnostic = useCallback(() => setShowDiagnostic(true), []);
  const closeDiagnostic = useCallback(() => setShowDiagnostic(false), []);
  const handleGenreHover = useCallback((genre) => setActiveGenre(genre), []);
  const handleGenreSelect = useCallback((genre) => {
    navigateTo("home");
    setSelectedGenre(genre);
  }, [navigateTo]);
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

  if (!isLoggedIn && !guestMode) {
    return (
      <LandingPage
        onLogin={handleLogin}
        onBrowseGuest={() => setGuestMode(true)}
      />
    );
  }

  return (
    <LibraryProvider isLoggedIn={isLoggedIn} onRequireLogin={() => setAuthPromptOpen(true)}>
      <main className="min-h-screen font-['Inter',ui-sans-serif,system-ui,sans-serif] text-slate-100">
        {/* ── Background Video Layer ── */}
        <BackgroundVideoLayer activeGenre={activeGenre} />

        {currentView === "for-you" ? (
          <ForYouPage
            onBack={() => navigateTo("home")}
            onGameClick={handleGameClick}
            isLoggedIn={isLoggedIn}
            onRequireLogin={() => setAuthPromptOpen(true)}
            currentUser={currentUser}
          />
        ) : currentView === "my-games" ? (
          <MyGamesPage
            onBack={() => navigateTo("home")}
            onGameClick={handleGameClick}
          />
        ) : (
          <>
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
          </>
        )}

        {/* Floating "Ask RigCheck AI" & "For You" Buttons */}
        <FloatingCTA
          onOpenDiagnostic={openDiagnostic}
          onOpenForYou={() => navigateTo("for-you")}
          currentView={currentView}
        />

        {/* Search Bar — top right next to user profile (only in home view) */}
        {currentView === "home" && (
          <SearchBar searchQuery={searchQuery} setSearchQuery={setSearchQuery} totalGames={totalGames} />
        )}

        {/* "My Games" Navigation Button */}
        <div className="fixed right-28 top-6 z-50">
          <button
            type="button"
            onClick={() => {
              if (!isLoggedIn) {
                setAuthPromptOpen(true);
              } else {
                navigateTo(currentView === "my-games" ? "home" : "my-games");
              }
            }}
            className={`group flex h-10 items-center gap-2 rounded-2xl border px-3 text-xs font-bold backdrop-blur-xl transition-all duration-300 ${
              currentView === "my-games"
                ? "border-cyan-400 bg-cyan-950/80 text-cyan-300 shadow-[0_0_20px_rgba(34,211,238,0.3)]"
                : "border-slate-600/35 bg-slate-950/75 text-slate-200 hover:border-cyan-400/50 hover:bg-slate-900/90 hover:text-cyan-200 shadow-[0_0_20px_rgba(34,211,238,0.08)]"
            }`}
          >
            <Gamepad2 className="h-4 w-4 text-cyan-400" />
            <span className="hidden sm:inline">My Games</span>
          </button>
        </div>

        {/* Account Profile Dropdown or Guest Sign In button */}
        <div className="fixed right-6 top-6 z-50">
          {isLoggedIn ? (
            <ProfileDropdown
              currentUser={currentUser}
              onOpenProfile={openProfile}
              onOpenSettings={openSettings}
              onLogout={handleLogout}
              onOpenMyGames={() => navigateTo("my-games")}
              onOpenForYou={() => navigateTo("for-you")}
            />
          ) : (
            <button
              type="button"
              onClick={() => setGuestMode(false)}
              className="flex h-10 items-center gap-1.5 rounded-2xl border border-cyan-400/40 bg-slate-950/80 px-3.5 text-xs font-bold text-cyan-300 shadow-[0_0_15px_rgba(34,211,238,0.15)] hover:bg-cyan-950/70 hover:border-cyan-400 backdrop-blur-xl transition-all duration-300"
            >
              <User className="h-3.5 w-3.5" />
              <span>Sign In</span>
            </button>
          )}
        </div>

        {/* Unauthenticated User Library Interaction Prompt */}
        {authPromptOpen && (
          <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/75 px-4 backdrop-blur-md">
            <div className="relative w-full max-w-sm rounded-2xl border border-cyan-400/30 bg-slate-950 p-6 shadow-[0_0_50px_rgba(34,211,238,0.15)] text-center animate-fadeIn">
              <button
                type="button"
                onClick={() => setAuthPromptOpen(false)}
                className="absolute right-3.5 top-3.5 text-slate-400 hover:text-white"
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
              <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
                <Gamepad2 className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-bold text-white mb-1.5">Sign In to Save Games</h3>
              <p className="text-xs text-slate-300 mb-5 leading-relaxed">
                Create an account or sign in to save favourites, organize your backlog, and rate games in your personal library.
              </p>
              <div className="flex gap-2.5">
                <button
                  type="button"
                  onClick={() => {
                    setAuthPromptOpen(false);
                    setGuestMode(false);
                  }}
                  className="flex-1 rounded-xl bg-cyan-400 py-2.5 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition-colors shadow-[0_0_15px_rgba(34,211,238,0.3)]"
                >
                  Sign In Now
                </button>
                <button
                  type="button"
                  onClick={() => setAuthPromptOpen(false)}
                  className="rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Diagnostic Modal */}
        <DiagnosticModal isOpen={showDiagnostic} onClose={closeDiagnostic} onGameClick={handleGameClick} />

        {/* Game Detail Modal */}
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
    </LibraryProvider>
  );
}
