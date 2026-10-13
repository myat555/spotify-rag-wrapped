from collections.abc import Iterator

from openai import APIError, OpenAI

from app.core.config import get_settings
from app.rag.embeddings import embed_text
from app.rag.vectorstore import search

SYSTEM_PROMPT = (
    "You are a witty music-taste analyst answering questions about the user's "
    "own Spotify listening history. Only use the CONTEXT chunks below to "
    "ground factual claims (counts, genres, dates, artists). If the context "
    "doesn't cover the question, say so plainly instead of guessing. Keep "
    "answers short, casual, and specific -- cite numbers when you have them."
)


def retrieve_context(question: str, top_k: int = 6) -> list[dict]:
    query_vector = embed_text(question)
    return search(query_vector, top_k=top_k)


def build_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n".join(f"- {c['text']}" for c in chunks) or "(no matching history found)"
    return f"CONTEXT:\n{context}\n\nQUESTION: {question}"


def stream_answer(question: str) -> Iterator[str]:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    chunks = retrieve_context(question)
    prompt = build_prompt(question, chunks)

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
