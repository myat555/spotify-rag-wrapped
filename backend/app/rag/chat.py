from collections.abc import Iterator

from openai import APIError, OpenAI

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import TraitSummary
from app.rag.embeddings import embed_text
from app.rag.vectorstore import search

SYSTEM_PROMPT = (
    "You are a witty music-taste analyst answering questions about the user's "
    "own Spotify listening history. You're given two kinds of grounding: "
    "ALL-TIME STATS (authoritative aggregate numbers -- use these for 'most/"
    "favorite/overall' style questions) and WEEKLY SNIPPETS (semantic-search "
    "matches on specific weeks -- use these for time-specific questions, not "
    "as a stand-in for the overall stats). Only use these two sections to "
    "ground factual claims (counts, genres, dates, artists); if neither "
    "covers the question, say so plainly instead of guessing. Keep answers "
    "short, casual, and specific -- cite numbers when you have them."
)


def retrieve_context(question: str, top_k: int = 6) -> list[dict]:
    query_vector = embed_text(question)
    return search(query_vector, top_k=top_k)


def get_latest_traits() -> TraitSummary | None:
    db = SessionLocal()
    try:
        return db.query(TraitSummary).order_by(TraitSummary.created_at.desc()).first()
    finally:
        db.close()


def format_traits_block(traits: TraitSummary | None) -> str:
    if traits is None:
        return "(no aggregate stats available yet -- ingestion may not have run)"
    top_artists = ", ".join(f"{a['name']} ({a['count']})" for a in traits.top_artists[:5])
    top_genres = ", ".join(f"{g['name']} ({g['count']})" for g in traits.top_genres[:5])
    return (
        f"Total plays: {traits.total_plays}, total hours: {traits.total_minutes / 60:.0f}\n"
        f"Top artists (all-time): {top_artists or 'none'}\n"
        f"Top genres (all-time): {top_genres or 'none'}\n"
        f"Vibe score: {traits.vibe_score}/100, genre diversity: "
        f"{traits.genre_diversity_score}/100\n"
        f"Longest listening streak: {traits.longest_streak_days} days, "
        f"skip rate: {traits.skip_rate * 100:.0f}%"
    )


def build_prompt(question: str, chunks: list[dict], traits_block: str) -> str:
    context = "\n".join(f"- {c['text']}" for c in chunks) or "(no matching weekly snippets found)"
    return (
        f"ALL-TIME STATS:\n{traits_block}\n\n"
        f"WEEKLY SNIPPETS:\n{context}\n\n"
        f"QUESTION: {question}"
    )


def stream_answer(question: str) -> Iterator[str]:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    chunks = retrieve_context(question)
    traits_block = format_traits_block(get_latest_traits())
    prompt = build_prompt(question, chunks, traits_block)

    try:
        stream = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except APIError as exc:
        yield f"\n\n[Couldn't reach OpenAI: {exc.message}. Check OPENAI_API_KEY in .env.]"
