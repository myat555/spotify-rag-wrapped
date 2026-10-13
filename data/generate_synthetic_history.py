"""Generates a synthetic Spotify 'Extended Streaming History' export.

Output matches the exact schema Spotify ships in the real export
(endsong_N.json), so this file is a drop-in stand-in until the user's real
export arrives -- the ingestion pipeline never needs to know which one it's
reading.

Usage:
    python3 data/generate_synthetic_history.py [--months 9] [--seed 42] \
        [--out data/sample_export/endsong_0.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
CATALOG_PATH = HERE / "genre_catalog.csv"

REASON_START = ["trackdone", "clickrow", "fwdbtn", "backbtn", "playbtn", "appload"]
REASON_END = ["trackdone", "fwdbtn", "backbtn", "endplay", "logout"]
PLATFORMS = ["android", "ios", "OS X", "Windows 11"]


def load_catalog() -> list[dict]:
    with open(CATALOG_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_taste_profile(catalog: list[dict], rng: random.Random) -> list[dict]:
    """Pick a favorites set (heavy rotation) + long tail, weighted so the
    synthetic history has a realistic top-artist skew instead of being
    uniformly random."""
    pool = [row for row in catalog if row["track_name"] and row["artist_name"]]
    rng.shuffle(pool)
    favorites = pool[:35]
    long_tail = pool[35:400]
    return favorites, long_tail


def pick_track(favorites: list[dict], long_tail: list[dict], rng: random.Random) -> dict:
    # ~70% of plays come from the favorites set -- gives top-artist/genre
    # stats something meaningful to surface.
    if rng.random() < 0.7 and favorites:
        return rng.choice(favorites)
    return rng.choice(long_tail)


def session_hour(rng: random.Random) -> int:
    # Weighted toward evenings (18-23) and lunch (12-13), light overnight tail.
    buckets = (
        [7, 8, 9] * 2
        + [12, 13] * 3
        + [15, 16, 17] * 2
        + [18, 19, 20, 21, 22, 23] * 5
        + [0, 1, 2] * 1
    )
    return rng.choice(buckets)


def make_event(track: dict, ts: datetime, rng: random.Random) -> dict:
    try:
        duration_ms = int(float(track.get("track_duration_min", "3")) * 60 * 1000)
    except ValueError:
        duration_ms = 180_000
    duration_ms = max(duration_ms, 30_000)

    skipped = rng.random() < 0.15
    ms_played = rng.randint(3_000, 20_000) if skipped else rng.randint(
        int(duration_ms * 0.85), duration_ms
    )

    track_id = track.get("track_id") or f"synthetic{rng.randint(10**9, 10**10)}"

    return {
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platform": rng.choice(PLATFORMS),
        "ms_played": ms_played,
        "conn_country": "US",
        "ip_addr_decrypted": "0.0.0.0",
        "user_agent_decrypted": None,
        "master_metadata_track_name": track["track_name"],
        "master_metadata_album_artist_name": track["artist_name"],
        "master_metadata_album_album_name": track.get("album_name") or track["track_name"],
        "spotify_track_uri": f"spotify:track:{track_id}",
        "episode_name": None,
        "episode_show_name": None,
        "spotify_episode_uri": None,
        "reason_start": rng.choice(REASON_START),
        "reason_end": "fwdbtn" if skipped else rng.choice(REASON_END),
        "shuffle": rng.random() < 0.6,
        "skipped": skipped,
        "offline": rng.random() < 0.05,
        "offline_timestamp": 0,
        "incognito_mode": rng.random() < 0.02,
    }


def generate(months: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    catalog = load_catalog()
    favorites, long_tail = build_taste_profile(catalog, rng)

    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = end - timedelta(days=30 * months)

    events: list[dict] = []
    day = start
    while day < end:
        # Skip some days entirely (nobody listens every single day).
        if rng.random() < 0.12:
            day += timedelta(days=1)
            continue

        is_weekend = day.weekday() >= 5
        plays_today = rng.randint(8, 28) if is_weekend else rng.randint(3, 18)

        for _ in range(plays_today):
            hour = session_hour(rng)
            minute = rng.randint(0, 59)
            second = rng.randint(0, 59)
            ts = day.replace(hour=hour, minute=minute, second=second)
            track = pick_track(favorites, long_tail, rng)
            events.append(make_event(track, ts, rng))

        day += timedelta(days=1)

    events.sort(key=lambda e: e["ts"])
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", type=int, default=9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out", type=Path, default=HERE / "sample_export" / "endsong_0.json"
    )
    args = parser.parse_args()

    events = generate(args.months, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    print(f"Wrote {len(events)} synthetic play events to {args.out}")


if __name__ == "__main__":
    main()
