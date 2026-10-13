from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models import TraitSummary

router = APIRouter(prefix="/traits", tags=["traits"])


@router.get("/summary")
def get_trait_summary(job_id: str | None = None) -> dict:
    db: Session = SessionLocal()
    try:
        query = db.query(TraitSummary)
        summary = (
            query.filter(TraitSummary.job_id == job_id).first()
            if job_id
            else query.order_by(TraitSummary.created_at.desc()).first()
        )
        if summary is None:
            raise HTTPException(
                status_code=404,
                detail="No trait summary yet. Run ingestion first via POST /ingest/start.",
            )
        return {
            "job_id": summary.job_id,
            "top_artists": summary.top_artists,
            "top_genres": summary.top_genres,
            "listening_clock": summary.listening_clock,
            "monthly_trend": summary.monthly_trend,
            "longest_streak_days": summary.longest_streak_days,
            "genre_diversity_score": summary.genre_diversity_score,
            "total_minutes": summary.total_minutes,
            "total_plays": summary.total_plays,
            "skip_rate": summary.skip_rate,
            "vibe_score": summary.vibe_score,
            "created_at": summary.created_at.isoformat(),
        }
    finally:
        db.close()
