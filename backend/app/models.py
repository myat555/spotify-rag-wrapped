import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Play(Base):
    __tablename__ = "plays"
    __table_args__ = (UniqueConstraint("ts", "track_uri", name="uq_play_ts_uri"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ms_played: Mapped[int] = mapped_column(Integer)
    track_name: Mapped[str] = mapped_column(String)
    artist_name: Mapped[str] = mapped_column(String, index=True)
    album_name: Mapped[str] = mapped_column(String)
    track_uri: Mapped[str] = mapped_column(String)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    reason_start: Mapped[str] = mapped_column(String)
    reason_end: Mapped[str] = mapped_column(String)
    shuffle: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    offline: Mapped[bool] = mapped_column(Boolean, default=False)
    incognito_mode: Mapped[bool] = mapped_column(Boolean, default=False)


class IngestJob(Base):
    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid.uuid4().hex)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|running|done|failed
    batches_total: Mapped[int] = mapped_column(Integer, default=0)
    batches_done: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class IngestBatchAggregate(Base):
    """One row per Celery batch task -- the 'map' half of the map-reduce trait
    computation. finalize_traits reduces all rows for a job_id into a
    TraitSummary."""

    __tablename__ = "ingest_batch_aggregates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("ingest_jobs.id"), index=True)
    genre_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    artist_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    hour_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    weekday_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    month_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    month_genre_counts: Mapped[dict] = mapped_column(JSONB, default=dict)
    days_played: Mapped[list] = mapped_column(JSONB, default=list)
    minutes_played: Mapped[float] = mapped_column(Float, default=0.0)
    plays_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)


class TraitSummary(Base):
    __tablename__ = "trait_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("ingest_jobs.id"), unique=True)
    top_artists: Mapped[list] = mapped_column(JSONB, default=list)
    top_genres: Mapped[list] = mapped_column(JSONB, default=list)
    listening_clock: Mapped[dict] = mapped_column(JSONB, default=dict)
    monthly_trend: Mapped[list] = mapped_column(JSONB, default=list)
    longest_streak_days: Mapped[int] = mapped_column(Integer, default=0)
    genre_diversity_score: Mapped[float] = mapped_column(Float, default=0.0)
    total_minutes: Mapped[float] = mapped_column(Float, default=0.0)
    total_plays: Mapped[int] = mapped_column(Integer, default=0)
    skip_rate: Mapped[float] = mapped_column(Float, default=0.0)
    vibe_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
