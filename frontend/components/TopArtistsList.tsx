"use client";

import { motion } from "framer-motion";
import { GlassCard } from "./ui/GlassCard";

export function TopArtistsList({ artists }: { artists: { name: string; count: number }[] }) {
  const top = artists.slice(0, 10);
  const max = Math.max(...top.map((a) => a.count), 1);

  return (
    <GlassCard delay={0.15}>
      <h3 className="mb-4 text-sm text-[var(--text-muted)]">Top artists</h3>
      <div
        className="flex flex-col gap-2.5"
        style={{ background: "var(--chart-surface)", borderRadius: 12, padding: 16 }}
      >
        {top.map((a, i) => (
          <div key={a.name} title={`#${i + 1} ${a.name}: ${a.count} plays`} className="group">
            <div className="mb-1 flex items-baseline gap-2 text-sm">
              <span className="w-5 text-right tabular-nums" style={{ color: "var(--chart-text-muted)" }}>
                {i + 1}
              </span>
              <span className="truncate" style={{ color: "var(--chart-text-primary)" }}>
                {a.name}
              </span>
              <span className="ml-auto tabular-nums" style={{ color: "var(--chart-text-secondary)" }}>
                {a.count}
              </span>
            </div>
            <div className="ml-7 h-[6px] overflow-hidden rounded-full bg-white/[0.04]">
              <motion.div
                className="h-full rounded-full transition-[filter] group-hover:brightness-125"
                style={{ background: "var(--series-1)" }}
                initial={{ width: 0 }}
                animate={{ width: `${(a.count / max) * 100}%` }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
