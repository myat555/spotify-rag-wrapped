const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface TraitSummary {
  job_id: string;
  top_artists: { name: string; count: number }[];
  top_genres: { name: string; count: number }[];
  listening_clock: Record<string, Record<string, number>>;
  monthly_trend: { month: string; plays: number; top_genre: string | null }[];
  longest_streak_days: number;
  genre_diversity_score: number;
  total_minutes: number;
  total_plays: number;
  skip_rate: number;
  vibe_score: number;
  created_at: string;
}

export interface IngestStatus {
  job_id: string;
  status: "pending" | "running" | "done" | "failed";
  batches_total: number;
  batches_done: number;
  error: string | null;
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function getTraitSummary(jobId?: string): Promise<TraitSummary> {
  const qs = jobId ? `?job_id=${encodeURIComponent(jobId)}` : "";
  return fetch(`${API_URL}/traits/summary${qs}`).then((res) => json<TraitSummary>(res));
}

export function startIngest(exportPath?: string): Promise<{ job_id: string; batches_total: number }> {
  return fetch(`${API_URL}/ingest/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(exportPath ? { export_path: exportPath } : {}),
  }).then((res) => json<{ job_id: string; batches_total: number }>(res));
}

export function getIngestStatus(jobId: string): Promise<IngestStatus> {
  return fetch(`${API_URL}/ingest/status/${jobId}`).then((res) => json<IngestStatus>(res));
}

export async function* streamChat(question: string): AsyncGenerator<string> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`Chat request failed: ${res.status} ${res.statusText}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    yield decoder.decode(value, { stream: true });
  }
}
