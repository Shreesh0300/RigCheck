import React, { useRef, useEffect, useMemo, memo } from "react";

/**
 * BackgroundVideoLayer — Cinematic fullscreen video background.
 *
 * Renders all 6 genre videos simultaneously as stacked <video> elements.
 * Only the active genre's video is visible (opacity crossfade).
 * Videos play continuously to avoid buffering on hover.
 *
 * Props:
 *   - activeGenre (string | null): the currently hovered genre key
 *
 * Technique:
 *   All videos are always mounted and playing (muted, looped).
 *   CSS opacity transitions handle the crossfade (800ms ease).
 *   No destruction/recreation = zero buffering, zero flicker.
 *
 * Default state (no hover):
 *   The Action/RPG video is shown at very low opacity (0.10)
 *   for subtle ambient background motion.
 */

const VIDEO_MAP = {
  "action-rpg": "/bgv/RPGOPW.mp4",
  simulation: "/bgv/SS.mp4",
  competitive: "/bgv/Comp.mp4",
  indie: "/bgv/indie.mp4",
  strategy: "/bgv/str.mp4",
  roguelike: "/bgv/loop.mp4",
};

const VIDEO_KEYS = Object.keys(VIDEO_MAP);

// Default genre shown at low opacity when nothing is hovered
const DEFAULT_GENRE = "action-rpg";
const ACTIVE_OPACITY = 0.3;
const DEFAULT_OPACITY = 0.12;

function BackgroundVideoLayer({ activeGenre }) {
  const videoRefs = useRef({});

  // Ensure all videos are playing (browsers may pause offscreen videos)
  useEffect(() => {
    Object.values(videoRefs.current).forEach((video) => {
      if (video && video.paused) {
        video.play().catch(() => {
          // Autoplay may be blocked — silently ignore
        });
      }
    });
  }, [activeGenre]);

  const videoEntries = useMemo(
    () => VIDEO_KEYS.map((key) => ({ key, src: VIDEO_MAP[key] })),
    []
  );

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
      aria-hidden="true"
    >
      {/* Video stack — all 6 videos rendered, only active one visible */}
      {videoEntries.map(({ key, src }) => {
        const isActive = activeGenre === key;
        const isDefault = !activeGenre && key === DEFAULT_GENRE;
        const opacity = isActive
          ? ACTIVE_OPACITY
          : isDefault
          ? DEFAULT_OPACITY
          : 0;

        return (
          <video
            key={key}
            ref={(el) => {
              videoRefs.current[key] = el;
            }}
            src={src}
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            className="absolute inset-0 h-full w-full object-cover"
            style={{
              opacity,
              transition: "opacity 800ms ease",
              willChange: "opacity",
            }}
          />
        );
      })}

      {/* Dark cinematic overlay — ensures text readability */}
      <div
        className="absolute inset-0"
        style={{
          background: `
            linear-gradient(
              180deg,
              rgba(2, 4, 10, 0.6) 0%,
              rgba(2, 4, 10, 0.4) 30%,
              rgba(2, 4, 10, 0.35) 50%,
              rgba(2, 4, 10, 0.5) 80%,
              rgba(2, 4, 10, 0.8) 100%
            )
          `,
        }}
      />

      {/* Vignette overlay — cinematic edge darkening */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 40%, rgba(2, 4, 10, 0.5) 100%)",
        }}
      />
    </div>
  );
}

export default memo(BackgroundVideoLayer);
