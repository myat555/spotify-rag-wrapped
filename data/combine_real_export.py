"""Combines Spotify's real 'Extended Streaming History' export (which ships as
multiple Streaming_History_Audio_*.json files, split by year/size) into one
sorted file the ingestion pipeline can read.

Usage:
    python3 data/combine_real_export.py \
        "/path/to/Spotify Extended Streaming History" \
        --out data/sample_export/real_history.json

Only Streaming_History_Audio_*.json files are used (not the Video_* ones --
this app is about music, and video plays don't carry track/artist/genre
metadata anyway). Duplicate plays across files are harmless: the ingestion
pipeline dedupes on (ts, track_uri) when it writes to Postgres.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_dir", type=Path, help="Path to the unzipped export folder")
    parser.add_argument(
        "--out", type=Path, default=Path("data/sample_export/real_history.json")
    )
    args = parser.parse_args()

    files = sorted(args.export_dir.glob("Streaming_History_Audio_*.json"))
    if not files:
        raise SystemExit(f"No Streaming_History_Audio_*.json files found in {args.export_dir}")

    records = []
    for fp in files:
        batch = json.loads(fp.read_text(encoding="utf-8"))
        records.extend(batch)
        print(f"{fp.name}: {len(batch)} records")

    records.sort(key=lambda r: r["ts"])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(records), encoding="utf-8")

    print(f"\n{len(records)} total records, {records[0]['ts']} to {records[-1]['ts']}")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
