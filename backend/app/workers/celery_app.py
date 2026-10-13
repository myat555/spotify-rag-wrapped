from celery import Celery
from celery.signals import worker_process_init

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "spotify_wrapped",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)


@worker_process_init.connect
def _bootstrap_qdrant_collection(**kwargs):
    from app.rag.vectorstore import ensure_collection

    ensure_collection()
