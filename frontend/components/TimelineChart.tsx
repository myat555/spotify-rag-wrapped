"use client";

import { monthLabel } from "@/lib/format";

export function TimelineChart({
  monthly,
}: {
  monthly: { month: string; plays: number; top_genre: string | null }[];
}) {
  if (monthly.length === 0) {
    return null;
  }

  const width = 640;
  const height = 200;
  const padX = 24;
  const padY = 20;
  const max = Math.max(...monthly.map((m) => m.plays), 1);
  const step = monthly.length > 1 ? (width - padX * 2) / (monthly.length - 1) : 0;

  const points = monthly.map((m, i) => {
    const x = padX + i * step;
    const y = height - padY - (m.plays / max) * (height - padY * 2);
    return { ...m, x, y };
  });

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`).join(" ");
  const areaPath = `${path} L ${points[points.length - 1].x} ${height - padY} L ${points[0].x} ${height - padY} Z`;
  const last = points[points.length - 1];

  return (
    <div style={{ background: "var(--chart-surface)", borderRadius: 12, padding: 16 }}>
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Monthly plays over time">
        <line
          x1={padX}
          y1={height - padY}
          x2={width - padX}
          y2={height - padY}
          stroke="var(--chart-baseline)"
          strokeWidth={1}
        />
        <path d={areaPath} fill="var(--series-1)" opacity={0.1} />
        <path d={path} fill="none" stroke="var(--series-1)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p) => (
          <circle key={p.month} cx={p.x} cy={p.y} r={4} fill="var(--series-1)" stroke="var(--chart-surface)" strokeWidth={2}>
            <title>{`${monthLabel(p.month)}: ${p.plays} plays, top genre ${p.top_genre ?? "unknown"}`}</title>
          </circle>
        ))}
        <text x={last.x} y={last.y - 12} textAnchor="end" fontSize={11} fill="var(--chart-text-primary)" fontWeight={600}>
          {last.plays}
        </text>
        {points
          .filter((_, i) => i % Math.ceil(points.length / 6 || 1) === 0)
          .map((p) => (
            <text key={`lbl-${p.month}`} x={p.x} y={height - 4} textAnchor="middle" fontSize={9} fill="var(--chart-text-muted)">
              {monthLabel(p.month)}
            </text>
          ))}
      </svg>
    </div>
  );
}
