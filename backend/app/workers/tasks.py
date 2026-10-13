import math
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.db import SessionLocal
from app.core.genre_lookup import primary_genre
from app.models import IngestBatchAggregate, IngestJob, Play, TraitSummary
from app.rag.embeddings import embed_texts
from app.rag.vectorstore import upsert_chunks
from app.workers.celery_app import celery_app


def _parse_ts(raw: str) -> datetime | None:
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _iso_week_key(d: date) -> str:
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


@celery_app.task(name="tasks.parse_batch", bind=True, max_retries=2)
def parse_batch(self, job_id: str, records: list[dict]) -> dict:
    db = SessionLocal()
    try:
        play_rows: list[dict] = []
        genre_counts: Counter = Counter()
        artist_counts: Counter = Counter()
        hour_counts: Counter = Counter()
        weekday_counts: Counter = Counter()
        month_counts: Counter = Counter()
        month_genre_counts: defaultdict = defaultdict(Counter)
        days_played: set[str] = set()
        minutes_played = 0.0
        plays_count = 0
        skipped_count = 0

        week_buckets: defaultdict = defaultdict(
            lambda: {"plays": 0, "minutes": 0.0, "artists": Counter(), "genres": Counter()}
        )

        for rec in records:
            ts = _parse_ts(rec.get("ts"))
            if ts is None:
                continue

            artist = rec.get("master_metadata_album_artist_name") or "Unknown Artist"
            track = rec.get("master_metadata_track_name") or "Unknown Track"
            album = rec.get("master_metadata_album_album_name") or ""
            uri = rec.get("spotify_track_uri") or f"unknown:{rec.get('ts')}:{artist}:{track}"
            ms_played = int(rec.get("ms_played") or 0)
            skipped = bool(rec.get("skipped"))
            genre = primary_genre(artist)
            minutes = ms_played / 60_000

            play_rows.append(
                {
                    "ts": ts,
                    "ms_played": ms_played,
                    "track_name": track,
                    "artist_name": artist,
                    "album_name": album,
                    "track_uri": uri,
                    "genre": genre,
                    "reason_start": rec.get("reason_start") or "",
                    "reason_end": rec.get("reason_end") or "",
                    "shuffle": bool(rec.get("shuffle")),
                    "skipped": skipped,
                    "offline": bool(rec.get("offline")),
                    "incognito_mode": bool(rec.get("incognito_mode")),
                }
            )

            plays_count += 1
            minutes_played += minutes
            if skipped:
                skipped_count += 1
            artist_counts[artist] += 1
            if genre:
                genre_counts[genre] += 1
            hour_counts[str(ts.hour)] += 1
            weekday_counts[str(ts.weekday())] += 1
            month_key = ts.strftime("%Y-%m")
            month_counts[month_key] += 1
            if genre:
                month_genre_counts[month_key][genre] += 1
            days_played.add(ts.date().isoformat())

            week_key = _iso_week_key(ts.date())
            bucket = week_buckets[week_key]
            bucket["plays"] += 1
            bucket["minutes"] += minutes
            bucket["artists"][artist] += 1
            if genre:
                bucket["genres"][genre] += 1

        if play_rows:
            stmt = pg_insert(Play).values(play_rows)
            stmt = stmt.on_conflict_do_nothing(index_elements=["ts", "track_uri"])
            db.execute(stmt)

        aggregate = IngestBatchAggregate(
            job_id=job_id,
            genre_counts=dict(genre_counts),
            artist_counts=dict(artist_counts),
            hour_counts=dict(hour_counts),
            weekday_counts=dict(weekday_counts),
            month_counts=dict(month_counts),
            month_genre_counts={k: dict(v) for k, v in month_genre_counts.items()},
            days_played=sorted(days_played),
            minutes_played=minutes_played,
            plays_count=plays_count,
            skipped_count=skipped_count,
        )
        db.add(aggregate)

        db.query(IngestJob).filter(IngestJob.id == job_id).update(
            {IngestJob.batches_done: IngestJob.batches_done + 1},
            synchronize_session=False,
        )
        db.commit()

        # Build one descriptive chunk per ISO week touched by this batch and
        # embed/upsert it into the (sharded, replicated) Qdrant collection.
        texts, payloads = [], []
        for week_key, bucket in week_buckets.items():
            top_artist = bucket["artists"].most_common(1)
            top_genre = bucket["genres"].most_common(1)
            text = (
                f"Week of {week_key}: {bucket['plays']} plays, "
                f"{bucket['minutes']:.0f} minutes listened. "
                f"Top artist: {top_artist[0][0] if top_artist else 'unknown'}. "
                f"Top genre: {top_genre[0][0] if top_genre else 'unknown'}."
            )
            texts.append(text)
            payloads.append({"job_id": job_id, "week": week_key, "kind": "weekly_summary"})

        if texts:
            embeddings = embed_texts(texts)
            upsert_chunks(texts, embeddings, payloads)

        return {"plays_count": plays_count}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        db.query(IngestJob).filter(IngestJob.id == job_id).update(
            {IngestJob.status: "failed", IngestJob.error: str(exc)},
            synchronize_session=False,
        )
        db.commit()
        raise
    finally:
        db.close()


def _shannon_diversity(counts: Counter) -> float:
    total = sum(counts.values())
    if total == 0 or len(counts) <= 1:
        return 0.0
    entropy = -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)
    max_entropy = math.log2(len(counts))
    return round((entropy / max_entropy) * 100, 1) if max_entropy > 0 else 0.0


def _longest_streak(days: list[str]) -> int:
    if not days:
        return 0
    parsed = sorted(date.fromisoformat(d) for d in days)
    longest = current = 1
    for prev, nxt in zip(parsed, parsed[1:]):
        if (nxt - prev).days == 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


@celery_app.task(name="tasks.finalize_traits")
def finalize_traits(_results: list[dict], job_id: str) -> dict:
    """Chord callback: fires once every parse_batch task for this job has
    completed. Reduces all partial aggregates into the final TraitSummary."""
    db = SessionLocal()
    try:
        batches = (
            db.query(IngestBatchAggregate).filter(IngestBatchAggregate.job_id == job_id).all()
        )

        genre_counts: Counter = Counter()
        artist_counts: Counter = Counter()
        hour_counts: Counter = Counter()
        weekday_counts: Counter = Counter()
        month_counts: Counter = Counter()
        month_genre_counts: defaultdict = defaultdict(Counter)
        days_played: set[str] = set()
        minutes_played = 0.0
        plays_count = 0
        skipped_count = 0

        for b in batches:
            genre_counts.update(b.genre_counts)
            artist_counts.update(b.artist_counts)
            hour_counts.update(b.hour_counts)
            weekday_counts.update(b.weekday_counts)
            month_counts.update(b.month_counts)
            for month, genres in b.month_genre_counts.items():
                month_genre_counts[month].update(genres)
            days_played.update(b.days_played)
            minutes_played += b.minutes_played
            plays_count += b.plays_count
            skipped_count += b.skipped_count

        top_artists = [{"name": n, "count": c} for n, c in artist_counts.most_common(10)]
        top_genres = [{"name": n, "count": c} for n, c in genre_counts.most_common(8)]

        listening_clock = {
            str(wd): {str(h): 0 for h in range(24)} for wd in range(7)
        }
        # hour_counts/weekday_counts were tracked independently (not jointly),
        # so we approximate the clock from weekday totals scaled by the
        # overall hour distribution -- good enough for a "when do you
        # listen" heatmap without a third counter dimension.
        total_plays_for_clock = sum(hour_counts.values()) or 1
        for wd, wd_count in weekday_counts.items():
            for h, h_count in hour_counts.items():
                share = (h_count / total_plays_for_clock) * wd_count
                listening_clock[wd][h] = round(share, 1)

        monthly_trend = []
        for month in sorted(month_counts):
            genres_this_month = month_genre_counts.get(month, {})
            top_genre = max(genres_this_month, key=genres_this_month.get) if genres_this_month else None
            monthly_trend.append(
                {"month": month, "plays": month_counts[month], "top_genre": top_genre}
            )

        longest_streak_days = _longest_streak(list(days_played))
        genre_diversity_score = _shannon_diversity(genre_counts)
        skip_rate = round(skipped_count / plays_count, 3) if plays_count else 0.0

        if days_played:
            span_days = (
                date.fromisoformat(max(days_played)) - date.fromisoformat(min(days_played))
            ).days + 1
        else:
            span_days = 1
        consistency = min(100.0, (len(days_played) / span_days) * 100)
        engagement = max(0.0, 100 - skip_rate * 100)
        vibe_score = round((genre_diversity_score + consistency + engagement) / 3, 1)

        summary = TraitSummary(
            job_id=job_id,
            top_artists=top_artists,
            top_genres=top_genres,
            listening_clock=listening_clock,
            monthly_trend=monthly_trend,
            longest_streak_days=longest_streak_days,
            genre_diversity_score=genre_diversity_score,
            total_minutes=round(minutes_played, 1),
            total_plays=plays_count,
            skip_rate=skip_rate,
            vibe_score=vibe_score,
        )
        db.add(summary)

        db.query(IngestJob).filter(IngestJob.id == job_id).update(
            {IngestJob.status: "done"}, synchronize_session=False
        )
        db.commit()
        return {"job_id": job_id, "total_plays": plays_count}
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        db.query(IngestJob).filter(IngestJob.id == job_id).update(
            {IngestJob.status: "failed", IngestJob.error: str(exc)},
            synchronize_session=False,
        )
        db.commit()
        raise
    finally:
        db.close()
