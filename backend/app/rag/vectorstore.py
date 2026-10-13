import hashlib
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.core.config import get_settings

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2


@lru_cache
def get_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection() -> None:
    settings = get_settings()
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        return
    try:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            shard_number=settings.qdrant_shard_number,
            replication_factor=settings.qdrant_replication_factor,
        )
    except UnexpectedResponse as exc:
        # The backend and every worker process call this at startup, so two
        # processes can both see "missing" before either creates it -- the
        # loser of that race just finds the collection already there.
        if exc.status_code != 409:
            raise


def _point_id(text: str) -> str:
    # Deterministic id so re-ingesting the same chunk upserts instead of
    # duplicating.
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def upsert_chunks(texts: list[str], embeddings: list[list[float]], payloads: list[dict]) -> None:
    settings = get_settings()
    client = get_client()
    points = [
        PointStruct(id=_point_id(text), vector=vector, payload={**payload, "text": text})
        for text, vector, payload in zip(texts, embeddings, payloads)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)


def search(query_vector: list[float], top_k: int = 5) -> list[dict]:
    settings = get_settings()
    client = get_client()
    hits = client.query_points(
        collection_name=settings.qdrant_collection,
        query=query_vector,
        limit=top_k,
    ).points
    return [{"text": h.payload.get("text", ""), "score": h.score, **h.payload} for h in hits]
