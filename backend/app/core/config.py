from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://wrapped:wrapped@localhost:5432/wrapped"
    redis_url: str = "redis://localhost:6379/0"
    qdrant_url: str = "http://localhost:6333"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"

    embedding_model_name: str = "all-MiniLM-L6-v2"
    qdrant_collection: str = "listening_chunks"
    qdrant_shard_number: int = 3
    qdrant_replication_factor: int = 2

    ingest_batch_size: int = 500
    genre_catalog_path: str = "/data/genre_catalog.csv"


@lru_cache
def get_settings() -> Settings:
    return Settings()
