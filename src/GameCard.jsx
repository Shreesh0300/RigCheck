import React, { useState, useEffect, useRef, memo } from "react";
import { motion } from "framer-motion";
import { Heart, Bookmark, CheckCircle2, Star, Sparkles, VolumeX } from "lucide-react";
import { useLibrary } from "./context/LibraryContext.jsx";
import Hls from "hls.js";

/**
 * GameCard — A single game tile for the gallery & personalized recommendation grid.
 *
 * Features:
 * - Lazy-loaded artwork with aspect-ratio container
 * - Desktop hover autoplay trailer (muted, inline, Netflix-style) via HLS.js
 * - Hover delay debounce (400ms) to avoid unnecessary bandwidth and resource spikes
 * - Safe resource cleanup on pointer leave or unmount
 * - Fallback to static artwork when trailer is unavailable or on mobile devices
 * - Recommendation explanation badge ("Because you enjoyed...")
 * - Genre badge (top-left) & Price badge (top-right)
 * - Favourite, Want to Play, Already Played action buttons with real-time sync
 * - Rating badge when game has been reviewed
 * - Title overlay with gradient fade
 * - Scale + glow on hover
 */

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] },
  },
};

function GameCard({ game, onGenreHover, onClick }) {
  let library = null;
  try {
    library = useLibrary();
  } catch (e) {
    // Graceful fallback if rendered outside LibraryProvider
  }

  const appid = game.appid || game.id || game.steamAppId;
  const title = game.title || game.name || "Game";
  const image = game.image || game.header_image;
  const genre = game.genre || (Array.isArray(game.genres) && game.genres.length > 0 ? game.genres[0] : "Game");
  const tags = (game.tags && game.tags.length > 0) ? game.tags : (Array.isArray(game.genres) ? game.genres : []);

  const status = library
    ? library.getGameStatus(appid)
    : {
        appid,
        is_favourite: game.is_favourite || false,
        want_to_play: game.want_to_play || false,
        already_played: game.already_played || false,
        rating: game.rating || null,
      };

  let priceLabel = "Price Unavailable";
  if (game.is_free || game.price === 0) {
    priceLabel = "FREE";
  } else if (typeof game.price === "number" && !Number.isNaN(game.price)) {
    priceLabel = `₹${game.price.toLocaleString("en-IN")}`;
  } else if (game.price && typeof game.price.final === "number") {
    if (game.price.final === 0) {
      priceLabel = "FREE";
    } else {
      priceLabel = `₹${(game.price.final / 100).toLocaleString("en-IN")}`;
    }
  }

  // --- Hover Trailer Autoplay Logic (Phase 6) ---
  const [isPlayingVideo, setIsPlayingVideo] = useState(false);
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const hoverTimerRef = useRef(null);

  const trailer = game.trailer || (Array.isArray(game.trailers) && game.trailers.length > 0 ? game.trailers[0] : null);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) {
        clearTimeout(hoverTimerRef.current);
      }
    };
  }, []);

  const handleMouseEnter = () => {
    onGenreHover?.(genre);

    // Desktop hover detection check
    const canHover = typeof window !== "undefined" && window.matchMedia("(hover: hover) and (pointer: fine)").matches;
    if (!canHover || !trailer) return;

    // Short hover delay (400ms) prevents buffering during fast pointer scrubbing
    hoverTimerRef.current = setTimeout(() => {
      setIsPlayingVideo(true);
    }, 400);
  };

  const handleMouseLeave = () => {
    onGenreHover?.(null);
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
    if (isPlayingVideo) {
      setIsPlayingVideo(false);
    }
  };

  // Video and HLS lifecycle management
  useEffect(() => {
    const video = videoRef.current;
    if (!isPlayingVideo || !video || !trailer) return;

    const hlsUrl = trailer.hls_h264;
    const directUrl = trailer.mp4_max || trailer.webm_max || trailer.mp4_480 || trailer.webm_480;

    let localHls = null;
    if (hlsUrl && Hls.isSupported()) {
      localHls = new Hls({
        maxBufferLength: 15,
        maxMaxBufferLength: 30,
        enableWorker: true,
      });
      hlsRef.current = localHls;
      localHls.loadSource(hlsUrl);
      localHls.attachMedia(video);
      localHls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
    } else if (hlsUrl && video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
      video.play().catch(() => {});
    } else if (directUrl) {
      video.src = directUrl;
      video.play().catch(() => {});
    }

    return () => {
      if (localHls) {
        localHls.destroy();
        localHls = null;
      }
      if (hlsRef.current) {
        hlsRef.current = null;
      }
      if (video) {
        video.pause();
        video.removeAttribute("src");
        video.load();
      }
    };
  }, [isPlayingVideo, trailer]);

  return (
    <motion.div
      variants={cardVariants}
      className="game-card group relative overflow-hidden rounded-2xl border border-slate-800/60 bg-slate-950/80 shadow-lg shadow-black/30 cursor-pointer hover:z-20 transition-all duration-300"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={() => onClick?.(game)}
    >
      {/* Artwork container */}
      <div className="relative aspect-[3/4] w-full overflow-hidden bg-slate-900">
        <img
          src={image}
          alt={title}
          loading="lazy"
          decoding="async"
          className={`h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-110 ${
            isPlayingVideo ? "opacity-0" : "opacity-100"
          }`}
        />

        {/* Hover Trailer Video Overlay */}
        {isPlayingVideo && trailer && (
          <div className="absolute inset-0 z-[5] overflow-hidden bg-black transition-opacity duration-300 animate-fadeIn">
            <video
              ref={videoRef}
              muted
              loop
              playsInline
              autoPlay
              className="h-full w-full object-cover"
            />
            {/* Subtle inline muted indicator */}
            <div className="absolute left-3 bottom-14 z-10 flex items-center gap-1 rounded-md bg-black/75 px-1.5 py-0.5 text-[9px] font-semibold text-slate-300 backdrop-blur-sm border border-cyan-400/20">
              <VolumeX className="h-3 w-3 text-cyan-400" />
              <span>Preview</span>
            </div>
          </div>
        )}

        {/* Gradient overlays */}
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#02040a] via-[#02040a]/20 to-transparent opacity-85 z-[6]" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[#02040a]/40 z-[6]" />

        {/* Genre badge — top left */}
        <span className="absolute left-3 top-3 z-10 rounded-full border border-cyan-400/20 bg-black/60 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-cyan-300 backdrop-blur-md">
          {genre}
        </span>

        {/* Price badge — top right */}
        <span className="absolute right-3 top-3 z-10 rounded-lg bg-black/60 px-2 py-1 text-[11px] font-extrabold text-white backdrop-blur-md">
          {priceLabel}
        </span>

        {/* Recommendation explanation pill (Phase 5) */}
        {game.explanation && (
          <div className="absolute left-3 top-10 z-10 max-w-[80%] rounded-lg border border-cyan-400/35 bg-slate-950/85 px-2 py-1 text-[10px] font-semibold text-cyan-200 backdrop-blur-md shadow-[0_0_12px_rgba(34,211,238,0.2)]">
            <span className="flex items-center gap-1">
              <Sparkles className="h-2.5 w-2.5 text-cyan-400 shrink-0 animate-pulse-glow" />
              <span className="truncate">{game.explanation}</span>
            </span>
          </div>
        )}

        {/* Library Actions Bar — top right, below price tag */}
        <div
          className="absolute right-3 top-11 z-20 flex items-center gap-1 rounded-full border border-slate-700/60 bg-black/70 p-1 backdrop-blur-md shadow-md transition-opacity duration-200"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Favourite Button */}
          <button
            type="button"
            title={status.is_favourite ? "Remove from Favourites" : "Add to Favourites"}
            aria-label={status.is_favourite ? "Remove from Favourites" : "Add to Favourites"}
            onClick={(e) => {
              e.stopPropagation();
              library?.toggleStatus(appid, "is_favourite", game);
            }}
            className={`grid h-6 w-6 place-items-center rounded-full transition-all duration-200 ${
              status.is_favourite
                ? "bg-rose-500/20 text-rose-400 shadow-[0_0_8px_rgba(244,63,94,0.4)]"
                : "text-slate-400 hover:bg-white/10 hover:text-rose-400"
            }`}
          >
            <Heart className={`h-3.5 w-3.5 ${status.is_favourite ? "fill-rose-500" : ""}`} />
          </button>

          {/* Want to Play Button */}
          <button
            type="button"
            title={status.want_to_play ? "Remove from Want to Play" : "Add to Want to Play"}
            aria-label={status.want_to_play ? "Remove from Want to Play" : "Add to Want to Play"}
            onClick={(e) => {
              e.stopPropagation();
              library?.toggleStatus(appid, "want_to_play", game);
            }}
            className={`grid h-6 w-6 place-items-center rounded-full transition-all duration-200 ${
              status.want_to_play
                ? "bg-cyan-500/20 text-cyan-300 shadow-[0_0_8px_rgba(34,211,238,0.4)]"
                : "text-slate-400 hover:bg-white/10 hover:text-cyan-300"
            }`}
          >
            <Bookmark className={`h-3.5 w-3.5 ${status.want_to_play ? "fill-cyan-400" : ""}`} />
          </button>

          {/* Already Played Button */}
          <button
            type="button"
            title={status.already_played ? "Marked as Played" : "Mark as Played"}
            aria-label={status.already_played ? "Marked as Played" : "Mark as Played"}
            onClick={(e) => {
              e.stopPropagation();
              library?.toggleStatus(appid, "already_played", game);
            }}
            className={`grid h-6 w-6 place-items-center rounded-full transition-all duration-200 ${
              status.already_played
                ? "bg-emerald-500/20 text-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.4)]"
                : "text-slate-400 hover:bg-white/10 hover:text-emerald-400"
            }`}
          >
            <CheckCircle2 className={`h-3.5 w-3.5 ${status.already_played ? "text-emerald-400 fill-emerald-500/20" : ""}`} />
          </button>
        </div>

        {/* Title overlay — bottom */}
        <div className="absolute inset-x-0 bottom-0 z-10 px-4 pb-4 pt-10">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-black leading-tight tracking-tight text-white drop-shadow-lg sm:text-base line-clamp-1">
              {title}
            </h3>
            {status.already_played && status.rating && (
              <span className="flex shrink-0 items-center gap-1 rounded-full border border-amber-400/30 bg-amber-500/15 px-1.5 py-0.5 text-[10px] font-bold text-amber-300 shadow-[0_0_8px_rgba(251,191,36,0.2)]">
                <Star className="h-2.5 w-2.5 fill-amber-400 text-amber-400" />
                {status.rating}/10
              </span>
            )}
          </div>
          {/* Tag row */}
          <div className="mt-2 flex flex-wrap gap-1">
            {tags.slice(0, 3).map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-slate-600/30 bg-slate-800/50 px-2 py-0.5 text-[9px] font-medium text-slate-400 backdrop-blur-sm"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Hover glow overlay */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl border-2 border-transparent transition-all duration-300 group-hover:border-cyan-400/35 group-hover:shadow-[inset_0_0_30px_rgba(34,211,238,0.08),0_0_40px_rgba(34,211,238,0.15)]" />
    </motion.div>
  );
}

export default memo(GameCard);
