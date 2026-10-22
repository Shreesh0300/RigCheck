import React from "react";
import { Search, X } from "lucide-react";

export default function SearchBar({ searchQuery, setSearchQuery, totalGames }) {
  const handleSearch = () => {
    if (searchQuery.trim()) {
      // Small timeout ensures the DOM has updated with any results before scrolling
      setTimeout(() => {
        const gallery = document.getElementById("game-gallery");
        if (gallery) {
          gallery.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 50);
    }
  };

  return (
    <div className="fixed right-52 top-6 z-40 flex items-center">
      <div className="relative group">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              handleSearch();
            }
          }}
          placeholder={`Search ${totalGames || ''} games...`}
          className="w-64 rounded-2xl border border-slate-600/30 bg-slate-950/70 py-2.5 pl-4 pr-11 text-sm text-slate-200 shadow-[0_0_20px_rgba(34,211,238,0.05)] backdrop-blur-xl transition-all duration-300 placeholder:text-slate-500 focus:w-72 focus:border-cyan-400/50 focus:bg-slate-900/90 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
        />

        {/* Action icons inside the search box */}
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center gap-1.5">
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
              title="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Search trigger button inside the box */}
          <button
            type="button"
            onClick={handleSearch}
            title="Search"
            className="p-1 text-slate-400 hover:text-cyan-400 transition-colors focus:outline-none group-focus-within:text-cyan-400"
          >
            <Search className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
