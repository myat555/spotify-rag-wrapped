"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  getIngestStatus,
  getTraitSummary,
  startIngest,
  type IngestStatus,
  type TraitSummary,
} from "@/lib/api";
import { StatTile } from "./StatTile";
import { VibeMeter } from "./VibeMeter";
import { GenreBarChart } from "./GenreBarChart";
import { TopArtistsList } from "./TopArtistsList";
import { ListeningHeatmap } from "./ListeningHeatmap";
import { TimelineChart } from "./TimelineChart";
import { WrappedShareCard } from "./WrappedShareCard";
import { GlassCard } from "./ui/GlassCard";
import { minutesToHours } from "@/lib/format";

type Phase = "checking" | "empty" | "starting" | "ingesting" | "ready" | "error";

export function Dashboard() {
  const [phase, setPhase] = useState<Phase>("checking");
  const [traits, setTraits] = useState<TraitSummary | null>(null);
  const [ingest, setIngest] = useState<IngestStatus | null>(null);
  const [error, setError] = useState<string>("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getTraitSummary()
      .then((data) => {
        setTraits(data);
        setPhase("ready");
      })
      .catch(() => setPhase("empty"));
  }, []);

  useEffect(() => {
    if (phase !== "ingesting" || !ingest) return;
    pollRef.current = setInterval(async () => {
      try {
        const status = await getIngestStatus(ingest.job_id);
        setIngest(status);
        if (status.status === "done") {
          clearInterval(pollRef.current!);
          const data = await getTraitSummary(status.job_id);
          setTraits(data);
          setPhase("ready");
        } else if (status.status === "failed") {
          clearInterval(pollRef.current!);
          setError(status.error || "Ingestion failed.");
          setPhase("error");
        }
      } catch (e) {
        clearInterval(pollRef.current!);
        setError((e as Error).message);
        setPhase("error");
      }
    }, 1200);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [phase, ingest?.job_id]);

  async function handleStart() {
    setPhase("starting");
    try {
      const res = await startIngest();
      setIngest({ job_id: res.job_id, status: "running", batches_total: res.batches_total, batches_done: 0, error: null });
      setPhase("ingesting");
    } catch (e) {
      setError((e as Error).message);
      setPhase("error");
    }
  }

  if (phase === "checking") {
    return <CenteredMessage>Checking your listening history...</CenteredMessage>;
  }

  if (phase === "empty" || phase === "starting") {
    return (
      <CenteredMessage>
        <div className="flex flex-col items-center gap-4 text-center">
          <h1 className="text-3xl font-semibold">No vibe data yet</h1>
          <p className="max-w-md text-[var(--text-secondary)]">
            Run <code className="rounded bg-white/10 px-1.5 py-0.5">make synth</code> once to
            generate a sample export, then kick off ingestion below -- it fans out across the
            distributed Celery workers and Qdrant cluster.
          </p>
          <button
            onClick={handleStart}
            disabled={phase === "starting"}
            className="mt-2 rounded-full px-6 py-3 font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            style={{ background: "var(--accent-gradient)" }}
          >
            {phase === "starting" ? "Starting..." : "Analyze my listening history"}
          </button>
        </div>
      </CenteredMessage>
    );
  }

  if (phase === "ingesting" && ingest) {
    const pct = ingest.batches_total > 0 ? (ingest.batches_done / ingest.batches_total) * 100 : 0;
    return (
      <CenteredMessage>
        <div className="flex w-full max-w-md flex-col items-center gap-4 text-center">
          <h1 className="text-2xl font-semibold">Analyzing your vibe...</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            {ingest.batches_done} / {ingest.batches_total} batches processed across the worker
            cluster
          </p>
          <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
            <motion.div
              className="h-full rounded-full"
              style={{ background: "var(--accent-gradient)" }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
        </div>
      </CenteredMessage>
    );
  }

  if (phase === "error") {
    return (
      <CenteredMessage>
        <p className="text-red-400">{error}</p>
      </CenteredMessage>
    );
  }

  if (!traits) return null;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">your listening, decoded</h1>
        <Link
          href="/chat"
          className="rounded-full border border-[var(--border-glass)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:text-white"
        >
          Ask your Wrapped &rarr;
        </Link>
      </header>

      <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <VibeMeter score={traits.vibe_score} />
        <StatTile label="Hours listened" value={minutesToHours(traits.total_minutes)} delay={0.05} />
        <StatTile label="Longest streak" value={String(traits.longest_streak_days)} suffix="days" delay={0.1} />
        <StatTile label="Genre diversity" value={traits.genre_diversity_score.toFixed(0)} suffix="/ 100" delay={0.15} />

        <GenreBarChart genres={traits.top_genres} />
        <TopArtistsList artists={traits.top_artists} />

        <GlassCard delay={0.2} className="sm:col-span-2">
          <h3 className="mb-4 text-sm text-[var(--text-muted)]">When you listen</h3>
          <ListeningHeatmap clock={traits.listening_clock} />
        </GlassCard>

        <GlassCard delay={0.25} className="sm:col-span-2">
          <h3 className="mb-4 text-sm text-[var(--text-muted)]">Plays per month</h3>
          <TimelineChart monthly={traits.monthly_trend} />
        </GlassCard>

        <GlassCard delay={0.3} className="sm:col-span-2 lg:col-span-4">
          <h3 className="mb-4 text-center text-sm text-[var(--text-muted)]">Share your wrapped</h3>
          <WrappedShareCard traits={traits} />
        </GlassCard>
      </div>
    </div>
  );
}

function CenteredMessage({ children }: { children: ReactNode }) {
  return <div className="flex min-h-screen items-center justify-center px-6">{children}</div>;
}
