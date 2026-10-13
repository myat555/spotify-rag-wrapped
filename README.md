# wrapped.rag

Your Spotify listening history, decoded: a RAG chat assistant + a styled
"Wrapped" dashboard, backed by a genuinely distributed ingestion pipeline
(Celery workers + a real 3-node Qdrant cluster) instead of a single script.

## Why it's real distributed systems, not simulated

- **Ingestion fan-out**: the export is split into batches, each an independent
  Celery task pulled off a shared Redis queue by `docker compose up --scale
  worker=3` -- genuinely parallel workers, not async tasks in one process.
- **Qdrant runs as an actual 3-node cluster** (Raft consensus, sharded +
  replicated vector collection), not a single instance.
- **Trait aggregation is map-reduce**: each batch task writes a partial
  aggregate; a Celery `chord` callback fires once every batch for a job is
  done and reduces them into the final trait summary.
- **Flower** (`localhost:5555`) makes the distribution visible while it runs.

## Stack

- **Data**: a synthetic generator matching Spotify's real "Extended Streaming
  History" export schema, so you can try the whole thing immediately. Your
  real export is a drop-in replacement -- same schema, zero code changes.
- **Backend**: FastAPI + Celery/Redis, Postgres for structured plays/trait
  summaries, Qdrant for the RAG vector store.
- **RAG**: local embeddings (`sentence-transformers`, no API key needed),
  OpenAI for chat generation (needs an API key).
- **Frontend**: Next.js + Tailwind + Framer Motion, dark glassmorphism
  dashboard with hand-built charts (bar, heatmap, timeline) following an
  accessible, colorblind-safe palette.

## Prerequisites

- **Docker Desktop**, running (not just installed) -- `docker info` should
  succeed. Everything runs in containers; you don't need Python or Node
  installed locally unless you want to run the data scripts outside Docker.
- **~6 GB free disk space** for images on first build (Postgres, Redis, 3x
  Qdrant, and a Python image carrying PyTorch for local embeddings).
- **An OpenAI API key**, only if you want the `/chat` RAG feature to actually
  answer questions. Everything else (ingestion, the dashboard, retrieval)
  works without one.

## Quickstart (synthetic data)

The fastest way to see it working, no real Spotify data required:

```bash
git clone <this-repo-url> && cd spotify-rag-wrapped
cp .env.example .env            # optionally fill in OPENAI_API_KEY now
make synth                      # writes data/sample_export/endsong_0.json
make up                         # docker compose up --build -d, 3 worker replicas
```

The first `make up` takes a few minutes -- it's pulling 6 images and building
the backend image, which installs PyTorch for local embeddings. Subsequent
runs are fast.

Once it's up:

1. Open **http://localhost:3000** and click **"Analyze my listening
   history"**. This calls `POST /ingest/start`, which fans the export out
   across the 3 Celery workers.
2. Watch it happen at **http://localhost:5555** (Flower) or `make logs`.
3. When it finishes, the dashboard renders automatically, and `/chat` is
   ready for questions (once you've added a real `OPENAI_API_KEY`, see
   below).

## Using your real Spotify export

Spotify's **Extended Streaming History** export (different from the smaller
default "Account data" export -- you specifically need the "Extended
streaming history" option) can take several days to a few weeks to arrive by
email after you request it from your [Spotify privacy
settings](https://www.spotify.com/account/privacy/). That's exactly why the
synthetic generator exists -- build and demo against it in the meantime.

When it arrives, you'll get a `.zip` that unzips to a folder like `Spotify
Extended Streaming History/` containing several files named
`Streaming_History_Audio_<year>[_N].json` (one or more per year, split when a
year has a lot of data) plus some `Streaming_History_Video_*.json` files
(ignored -- this app is about music).

Combine them into one file the pipeline can ingest:

```bash
make combine-real EXPORT_DIR="/path/to/Spotify Extended Streaming History"
# equivalent to:
#   python3 data/combine_real_export.py "/path/to/Spotify Extended Streaming History"
```

This writes `data/sample_export/real_history.json`, sorted chronologically.
Overlapping/duplicate records across files are harmless -- ingestion dedupes
on `(timestamp, track_uri)` when it writes to Postgres.

Then ingest it:

```bash
make seed-real
# or, to watch it from the browser instead:
#   point POST /ingest/start at {"export_path": "/data/sample_export/real_history.json"}
```

For a large history (tens of thousands of plays across many years), expect
hundreds of batches -- check progress with `make status JOB_ID=<id>` (the
`job_id` is printed by `make seed-real`) or watch Flower.

## Enabling the chat feature

The dashboard and ingestion work with no external API key. To get real
answers from `/chat` (the "Ask your Wrapped" page), add your key to `.env`:

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_CHAT_MODEL=gpt-4o-mini   # or any chat-completions-capable model
```

Then restart the backend so it picks up the new env var:

```bash
docker compose up -d backend
```

Without a valid key, `/chat` still retrieves the right context from Qdrant
and streams back a clear "couldn't reach OpenAI, check your key" message
instead of failing silently.

## Services

| Service | Port | Purpose |
|---|---|---|
| frontend | 3000 | Next.js dashboard + chat |
| backend | 8000 | FastAPI (`/ingest`, `/traits`, `/chat`) |
| flower | 5555 | Celery task monitoring |
| qdrant-node1 | 6333 | Vector store (cluster entrypoint; nodes 2 and 3 are internal-only) |
| postgres | 5432 | Structured plays + trait summaries |
| redis | 6379 | Celery broker/result backend |

## Make targets

| Target | What it does |
|---|---|
| `make up` | Build and start everything (3 worker replicas, detached) |
| `make down` | Stop everything |
| `make logs` | Tail backend + worker logs |
| `make synth` | Generate a synthetic export at `data/sample_export/endsong_0.json` |
| `make seed` | Trigger ingestion of the synthetic export |
| `make combine-real EXPORT_DIR=...` | Combine a real Spotify export folder into one file |
| `make seed-real` | Trigger ingestion of the combined real export |
| `make status JOB_ID=...` | Check an ingestion job's progress |
| `make traits` | Fetch the latest computed trait summary as JSON |

## Verifying it's working end to end

```bash
curl http://localhost:8000/health                         # {"status": "ok"}
curl http://localhost:6333/cluster | python3 -m json.tool  # Qdrant Raft status, should show a Leader
curl http://localhost:6333/collections/listening_chunks | python3 -m json.tool  # points_count > 0 after ingesting
make traits                                                # top artists/genres, vibe score, etc.
```

## Repo layout

```
spotify-rag-wrapped/
  docker-compose.yml
  Makefile
  .env.example
  data/
    generate_synthetic_history.py   # synthetic export matching Spotify's schema
    combine_real_export.py          # combines a real multi-file export into one
    genre_catalog.csv               # offline artist -> genre lookup (no Spotify API needed)
  backend/
    app/
      main.py                 # FastAPI app
      api/                    # ingest.py, traits.py, chat.py routers
      core/                   # config, db session, genre lookup
      models.py                # SQLAlchemy models
      workers/                # Celery app + parse_batch/finalize_traits tasks
      rag/                     # embeddings, Qdrant client, OpenAI chat
  frontend/
    app/                      # dashboard (/) and chat (/chat) pages
    components/                # bento cards, charts, chat window
    lib/                       # API client, formatting helpers
```

## Troubleshooting

- **`failed to connect to the docker API` / everything fails immediately**:
  Docker Desktop isn't running. Start it (`open -a Docker` on macOS) and wait
  for `docker info` to succeed before retrying.
- **First `make up` seems to hang**: it's building the backend image, which
  installs PyTorch (~700 MB+) for local embeddings. This only happens once;
  check `docker compose logs backend` if it's been more than ~10 minutes.
- **An ingestion job stays at `"status": "running"` with no progress**: check
  `docker compose logs worker` -- the most common cause the first time is all
  3 workers simultaneously downloading the embedding model over a slow
  connection. A shared `hf_cache` volume avoids re-downloading on restarts.
- **`/chat` returns a "couldn't reach OpenAI" message**: expected without a
  valid `OPENAI_API_KEY` in `.env` (see above) -- everything else is working.
