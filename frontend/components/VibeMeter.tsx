"use client";

import { motion } from "framer-motion";
import { GlassCard } from "./ui/GlassCard";

export function VibeMeter({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  return (
    <GlassCard glow className="flex flex-col gap-4 sm:col-span-2">
      <span className="text-sm text-[var(--text-muted)]">Your vibe score</span>
      <span
        className="bg-clip-text text-7xl font-semibold leading-none tracking-tight text-transparent sm:text-8xl"
        style={{ backgroundImage: "var(--accent-gradient)" }}
      >
        {pct.toFixed(0)}
      </span>
      <div
        className="h-2.5 w-full overflow-hidden rounded-full"
        style={{ background: "rgba(57, 135, 229, 0.15)" }}
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: "var(--accent-gradient)" }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: "easeOut", delay: 0.2 }}
        />
      </div>
      <p className="text-sm text-[var(--text-secondary)]">
        A mashup of genre diversity, listening consistency, and how often you actually
        finish a track.
      </p>
    </GlassCard>
  );
}
