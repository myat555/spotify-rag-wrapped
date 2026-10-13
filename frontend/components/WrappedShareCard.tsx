"use client";

import { useRef, useState } from "react";
import { toPng } from "html-to-image";
import type { TraitSummary } from "@/lib/api";
import { minutesToHours } from "@/lib/format";

export function WrappedShareCard({ traits }: { traits: TraitSummary }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [downloading, setDownloading] = useState(false);

  const topGenre = traits.top_genres[0]?.name ?? "eclectic";
  const topArtist = traits.top_artists[0]?.name ?? "a mystery artist";

  async function handleDownload() {
    if (!cardRef.current) return;
    setDownloading(true);
    try {
      const dataUrl = await toPng(cardRef.current, { pixelRatio: 2 });
      const link = document.createElement("a");
      link.download = "my-listening-wrapped.png";
      link.href = dataUrl;
      link.click();
    } finally {
      setDownloading(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-4">
      <div
        ref={cardRef}
        className="relative flex aspect-[9/16] w-full max-w-xs flex-col justify-between overflow-hidden rounded-[2rem] p-8"
        style={{ background: "linear-gradient(160deg, #1a0b2e 0%, #3b0764 45%, #831843 100%)" }}
      >
        <div
          className="pointer-events-none absolute -top-16 -right-16 h-56 w-56 rounded-full opacity-60 blur-3xl"
          style={{ background: "var(--glow-pink)" }}
        />
        <div
          className="pointer-events-none absolute -bottom-20 -left-16 h-56 w-56 rounded-full opacity-50 blur-3xl"
          style={{ background: "var(--glow-blue)" }}
        />

        <div className="relative z-10">
          <p className="text-xs uppercase tracking-[0.2em] text-white/60">Your listening, wrapped</p>
          <p className="mt-6 text-sm text-white/70">Vibe score</p>
          <p className="text-6xl font-semibold text-white">{traits.vibe_score.toFixed(0)}</p>
        </div>

        <div className="relative z-10 flex flex-col gap-4">
          <div>
            <p className="text-xs text-white/60">Top genre</p>
            <p className="text-xl font-semibold text-white">{topGenre}</p>
          </div>
          <div>
            <p className="text-xs text-white/60">Top artist</p>
            <p className="text-xl font-semibold text-white">{topArtist}</p>
          </div>
          <div className="flex justify-between border-t border-white/15 pt-4 text-white">
            <div>
              <p className="text-xs text-white/60">Hours listened</p>
              <p className="text-lg font-semibold">{minutesToHours(traits.total_minutes)}</p>
            </div>
            <div>
              <p className="text-xs text-white/60">Longest streak</p>
              <p className="text-lg font-semibold">{traits.longest_streak_days}d</p>
            </div>
          </div>
        </div>
      </div>

      <button
        onClick={handleDownload}
        disabled={downloading}
        className="rounded-full px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        style={{ background: "var(--accent-gradient)" }}
      >
        {downloading ? "Generating..." : "Download to share"}
      </button>
    </div>
  );
}
