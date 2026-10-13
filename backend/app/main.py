from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, ingest, traits
from app.core.db import Base, engine
from app.rag.vectorstore import ensure_collection

app = FastAPI(title="Spotify Wrapped RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(traits.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_collection()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
