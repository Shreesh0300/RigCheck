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
    <div className="fixed right-36 top-6 z-50 flex items-center gap-2">
      <div className="relative group">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-4 w-4 text-slate-400 group-focus-within:text-cyan-400 transition-colors" />
        </div>
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
          className="w-64 rounded-2xl border border-slate-600/30 bg-slate-950/70 py-2.5 pl-10 pr-10 text-sm text-slate-200 shadow-[0_0_20px_rgba(34,211,238,0.05)] backdrop-blur-xl transition-all duration-300 placeholder:text-slate-500 focus:w-72 focus:border-cyan-400/50 focus:bg-slate-900/90 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
      
      {/* Search trigger button */}
      <button
        onClick={handleSearch}
        title="Scroll to Results"
        className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-slate-600/30 bg-slate-950/70 text-slate-400 shadow-[0_0_20px_rgba(34,211,238,0.05)] backdrop-blur-xl transition-all duration-300 hover:border-cyan-400/50 hover:bg-slate-900/90 hover:text-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
      >
        <Search className="h-4 w-4" />
      </button>
    </div>
  );
}
