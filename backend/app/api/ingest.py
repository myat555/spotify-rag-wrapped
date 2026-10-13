import json
from pathlib import Path

from celery import chord
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import IngestJob
from app.workers.tasks import finalize_traits, parse_batch

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestStartRequest(BaseModel):
    export_path: str = "/data/sample_export/endsong_0.json"


class IngestStartResponse(BaseModel):
    job_id: str
    batches_total: int


class IngestStatusResponse(BaseModel):
    job_id: str
    status: str
    batches_total: int
    batches_done: int
    error: str | None = None


@router.post("/start", response_model=IngestStartResponse)
def start_ingest(payload: IngestStartRequest) -> IngestStartResponse:
    path = Path(payload.export_path)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{payload.export_path} not found. Run `make synth` first.",
        )

    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="Export file must be a non-empty JSON array.")

    settings = get_settings()
    batch_size = settings.ingest_batch_size
    batches = [records[i : i + batch_size] for i in range(0, len(records), batch_size)]

    db: Session = SessionLocal()
    try:
        job = IngestJob(status="running", batches_total=len(batches), batches_done=0)
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id
    finally:
        db.close()

    chord(parse_batch.s(job_id, batch) for batch in batches)(finalize_traits.s(job_id))

    return IngestStartResponse(job_id=job_id, batches_total=len(batches))


@router.get("/status/{job_id}", response_model=IngestStatusResponse)
def ingest_status(job_id: str) -> IngestStatusResponse:
    db: Session = SessionLocal()
    try:
        job = db.get(IngestJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return IngestStatusResponse(
            job_id=job.id,
            status=job.status,
            batches_total=job.batches_total,
            batches_done=job.batches_done,
            error=job.error,
        )
    finally:
        db.close()
