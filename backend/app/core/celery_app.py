"""Celery application — Redis as broker and result backend.

Enables offloading heavy/slow work (risk re-scoring, screening, notifications,
exports, webhooks) from request handlers to background workers, which is
essential for enterprise throughput and horizontal scaling.
"""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "antifraud",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    result_expires=3600,
    timezone="UTC",
)
