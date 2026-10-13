"use client";

import { WEEKDAY_LABELS } from "@/lib/format";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

function cellColor(value: number, max: number): string {
  if (max <= 0) return "rgba(57, 135, 229, 0.05)";
  const alpha = 0.06 + 0.86 * (value / max);
  return `rgba(57, 135, 229, ${alpha.toFixed(3)})`;
}

export function ListeningHeatmap({
  clock,
}: {
  clock: Record<string, Record<string, number>>;
}) {
  const values: number[] = [];
  for (const wd of Object.values(clock)) {
    for (const v of Object.values(wd)) values.push(v);
  }
  const max = Math.max(...values, 0);

  return (
    <div
      className="sm:col-span-2"
      style={{ background: "var(--chart-surface)", borderRadius: 12, padding: 16 }}
    >
      <div className="flex flex-col gap-[3px]">
        <div className="ml-10 flex gap-[3px]">
          {HOURS.map((h) => (
            <div
              key={h}
              className="w-[14px] text-center text-[9px]"
              style={{ color: "var(--chart-text-muted)" }}
            >
              {h % 3 === 0 ? h : ""}
            </div>
          ))}
        </div>
        {WEEKDAY_LABELS.map((label, wdIdx) => (
          <div key={label} className="flex items-center gap-[3px]">
            <span
              className="w-9 shrink-0 text-xs"
              style={{ color: "var(--chart-text-secondary)" }}
            >
              {label}
            </span>
            {HOURS.map((h) => {
              const value = clock[String(wdIdx)]?.[String(h)] ?? 0;
              return (
                <div
                  key={h}
                  title={`${label} ${h}:00 -- ${value.toFixed(1)} plays (avg)`}
                  className="h-[14px] w-[14px] rounded-[3px] transition-transform hover:scale-125"
                  style={{
                    background: cellColor(value, max),
                    outline: "2px solid var(--chart-surface)",
                  }}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
