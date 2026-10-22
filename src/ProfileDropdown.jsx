import React, { useState, useRef, useEffect, useCallback } from "react";
import { User, Settings, LogOut, ChevronDown, ShieldCheck } from "lucide-react";

/**
 * ProfileDropdown — Cyberpunk-styled account avatar and dropdown menu.
 *
 * Options:
 *  1. Profile  -> Opens ProfileModal
 *  2. Settings -> Opens SettingsModal
 *  3. Logout   -> Ends session and redirects to Sign In
 */
export default function ProfileDropdown({ currentUser, onOpenProfile, onOpenSettings, onLogout }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const triggerRef = useRef(null);

  const toggleDropdown = () => setIsOpen((prev) => !prev);
  const closeDropdown = useCallback(() => setIsOpen(false), []);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        closeDropdown();
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("touchstart", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [isOpen, closeDropdown]);

  // Close on Escape key & keyboard trap
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape" && isOpen) {
        closeDropdown();
        if (triggerRef.current) triggerRef.current.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, closeDropdown]);

  const handleProfileClick = () => {
    closeDropdown();
    onOpenProfile();
  };

  const handleSettingsClick = () => {
    closeDropdown();
    onOpenSettings();
  };

  const handleLogoutClick = () => {
    closeDropdown();
    onLogout();
  };

  // Determine provider badge icon and label
  const provider = currentUser?.auth_provider || "email";
  const initial = (currentUser?.display_name || currentUser?.email || "U")[0].toUpperCase();

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      {/* Profile Trigger Button */}
      <button
        ref={triggerRef}
        type="button"
        onClick={toggleDropdown}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label="Account menu"
        className="group flex h-10 items-center gap-2 rounded-2xl border border-slate-600/35 bg-slate-950/75 px-2.5 text-xs text-slate-200 shadow-[0_0_20px_rgba(34,211,238,0.08)] backdrop-blur-xl transition-all duration-300 hover:border-cyan-400/50 hover:bg-slate-900/90 hover:shadow-[0_0_25px_rgba(34,211,238,0.2)] focus:outline-none focus:ring-2 focus:ring-cyan-400/30"
      >
        {/* Avatar Image or Styled Initial */}
        {currentUser?.avatar_url || currentUser?.avatar ? (
          <img
            src={currentUser.avatar_url || currentUser.avatar}
            alt={currentUser.display_name || "Profile"}
            className="h-6 w-6 rounded-full border border-cyan-400/40 object-cover shadow-[0_0_8px_rgba(34,211,238,0.3)]"
          />
        ) : (
          <div className="grid h-6 w-6 place-items-center rounded-full border border-cyan-400/40 bg-cyan-400/10 text-[11px] font-bold text-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.2)]">
            {initial}
          </div>
        )}

        <span className="hidden max-w-[110px] truncate font-medium text-slate-200 group-hover:text-cyan-200 sm:inline">
          {currentUser?.display_name || "Account"}
        </span>

        <ChevronDown
          className={`h-3.5 w-3.5 text-slate-400 transition-transform duration-200 group-hover:text-cyan-300 ${
            isOpen ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        />
      </button>

      {/* Glassmorphic Dropdown Menu */}
      {isOpen && (
        <div
          role="menu"
          aria-orientation="vertical"
          aria-labelledby="account-menu"
          className="absolute right-0 top-12 z-50 w-64 origin-top-right rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-slate-900/95 via-slate-950/95 to-slate-900/95 p-2 shadow-[0_12px_40px_rgba(0,0,0,0.7),0_0_30px_rgba(34,211,238,0.1)] backdrop-blur-2xl ring-1 ring-white/10 animate-fadeIn"
        >
          {/* User Identity Header */}
          <div className="px-3 py-2.5 border-b border-white/10 mb-1">
            <div className="flex items-center gap-2.5">
              {currentUser?.avatar_url || currentUser?.avatar ? (
                <img
                  src={currentUser.avatar_url || currentUser.avatar}
                  alt={currentUser.display_name}
                  className="h-8 w-8 rounded-full border border-cyan-400/50 object-cover shrink-0"
                />
              ) : (
                <div className="grid h-8 w-8 place-items-center rounded-full border border-cyan-400/40 bg-cyan-400/15 text-xs font-bold text-cyan-300 shrink-0">
                  {initial}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-white">
                  {currentUser?.display_name || "Gamer"}
                </p>
                <p className="truncate text-[11px] text-slate-400">
                  {currentUser?.email || (provider === "steam" ? "Steam Linked" : "Verified User")}
                </p>
              </div>
            </div>

            {/* Provider Pill */}
            <div className="mt-2 inline-flex items-center gap-1 rounded-full border border-cyan-400/20 bg-cyan-400/[0.08] px-2 py-0.5 text-[10px] font-medium text-cyan-300">
              <ShieldCheck className="h-3 w-3" />
              <span className="capitalize">{provider} Account</span>
            </div>
          </div>

          {/* Primary Option 1: Profile */}
          <button
            type="button"
            role="menuitem"
            onClick={handleProfileClick}
            className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-medium text-slate-200 transition-colors hover:bg-cyan-500/15 hover:text-cyan-200 focus:bg-cyan-500/15 focus:text-cyan-200 focus:outline-none"
          >
            <User className="h-4 w-4 text-cyan-400" />
            <span>Profile</span>
          </button>

          {/* Primary Option 2: Settings */}
          <button
            type="button"
            role="menuitem"
            onClick={handleSettingsClick}
            className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-medium text-slate-200 transition-colors hover:bg-cyan-500/15 hover:text-cyan-200 focus:bg-cyan-500/15 focus:text-cyan-200 focus:outline-none"
          >
            <Settings className="h-4 w-4 text-cyan-400" />
            <span>Settings</span>
          </button>

          {/* Divider */}
          <div className="my-1 border-t border-white/10" />

          {/* Primary Option 3: Logout */}
          <button
            type="button"
            role="menuitem"
            onClick={handleLogoutClick}
            className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-xs font-medium text-rose-300 transition-colors hover:bg-rose-500/15 hover:text-rose-200 focus:bg-rose-500/15 focus:text-rose-200 focus:outline-none"
          >
            <LogOut className="h-4 w-4 text-rose-400" />
            <span>Logout</span>
          </button>
        </div>
      )}
    </div>
  );
}
