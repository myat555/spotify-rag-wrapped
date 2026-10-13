"use client";

import { motion } from "framer-motion";
import { GlassCard } from "./ui/GlassCard";

const SERIES_COLORS = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
];

export function GenreBarChart({ genres }: { genres: { name: string; count: number }[] }) {
  const top = genres.slice(0, 8);
  const max = Math.max(...top.map((g) => g.count), 1);

  return (
    <GlassCard delay={0.1} className="sm:col-span-2">
      <h3 className="mb-4 text-sm text-[var(--text-muted)]">Top genres</h3>
      <div
        className="flex flex-col gap-3"
        style={{ background: "var(--chart-surface)", borderRadius: 12, padding: 16 }}
      >
        {top.map((g, i) => {
          const widthPct = (g.count / max) * 100;
          const color = SERIES_COLORS[i % SERIES_COLORS.length];
          return (
            <div key={g.name} title={`${g.name}: ${g.count} plays`} className="group">
              <div className="mb-1 flex items-center justify-between text-sm">
                <span style={{ color: "var(--chart-text-secondary)" }}>{g.name}</span>
                <span
                  className="font-medium tabular-nums"
                  style={{ color: "var(--chart-text-primary)" }}
                >
                  {g.count}
                </span>
              </div>
              <div className="h-[18px] w-full overflow-hidden rounded-full bg-white/[0.04]">
                <motion.div
                  className="h-full rounded-full transition-[filter] group-hover:brightness-125"
                  style={{ background: color }}
                  initial={{ width: 0 }}
                  animate={{ width: `${widthPct}%` }}
                  transition={{ duration: 0.6, ease: "easeOut" }}
                />
              </div>
            </div>
          );
        })}
        {top.length === 0 && (
          <p className="text-sm" style={{ color: "var(--chart-text-muted)" }}>
            No genre matches yet -- your artists may not be in the genre catalog.
          </p>
        )}
      </div>
    </GlassCard>
  );
}
