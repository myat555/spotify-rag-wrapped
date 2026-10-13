import csv
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def load_genre_lookup() -> dict[str, list[str]]:
    settings = get_settings()
    lookup: dict[str, list[str]] = {}
    try:
        with open(settings.genre_catalog_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                artist = (row.get("artist_name") or "").strip()
                genres_raw = (row.get("artist_genres") or "").strip()
                if not artist or artist in lookup:
                    continue
                genres = [
                    g.strip()
                    for g in genres_raw.split(",")
                    if g.strip() and g.strip().upper() != "N/A"
                ]
                # Only lock in this artist once we have real genre data -- the
                # catalog uses the literal string "N/A" for missing genres,
                # and a later row for the same artist may have real ones.
                if genres:
                    lookup[artist] = genres
    except FileNotFoundError:
        pass
    return lookup


def primary_genre(artist_name: str) -> str | None:
    genres = load_genre_lookup().get(artist_name)
    return genres[0] if genres else None
