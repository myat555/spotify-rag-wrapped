import { GlassCard } from "./ui/GlassCard";

export function StatTile({
  label,
  value,
  suffix,
  accent = "var(--text-primary)",
  delay = 0,
}: {
  label: string;
  value: string;
  suffix?: string;
  accent?: string;
  delay?: number;
}) {
  return (
    <GlassCard delay={delay} className="flex flex-col justify-between gap-3">
      <span className="text-sm text-[var(--text-muted)]">{label}</span>
      <span className="text-4xl font-semibold tracking-tight" style={{ color: accent }}>
        {value}
        {suffix && (
          <span className="ml-1 text-lg font-medium text-[var(--text-secondary)]">{suffix}</span>
        )}
      </span>
    </GlassCard>
  );
}
