"""Background Celery tasks.

Tasks run in a separate worker process, so they use their own DB engine:
- synchronous (psycopg2) for simple inserts,
- a short-lived async engine (asyncpg) when reusing existing async services.
Fresh engines per task avoid event-loop/pool binding issues across runs.
"""
import asyncio
from app.core.celery_app import celery_app


@celery_app.task(name="send_notification")
def send_notification(user_id: int, title: str, message: str, notification_type: str = "info") -> dict:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.core.config import settings
    from app.models.audit import Notification

    engine = create_engine(settings.SYNC_DATABASE_URL)
    try:
        with Session(engine) as s:
            s.add(Notification(
                user_id=user_id, title=title, message=message,
                notification_type=notification_type,
            ))
            s.commit()
    finally:
        engine.dispose()
    return {"status": "sent", "user_id": user_id}


@celery_app.task(name="recalculate_risk_score")
def recalculate_risk_score(client_id: int) -> dict:
    return asyncio.run(_recalc(client_id))


async def _recalc(client_id: int) -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.client import ClientProfile
    from app.services.risk_engine import calculate_risk_score

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with SessionLocal() as db:
            profile = (
                await db.execute(select(ClientProfile).where(ClientProfile.id == client_id))
            ).scalar_one_or_none()
            if not profile:
                return {"status": "not_found", "client_id": client_id}
            risk = await calculate_risk_score(profile, db)
            await db.commit()
            return {
                "status": "done", "client_id": client_id,
                "score": risk.total_score, "level": str(risk.risk_level),
            }
    finally:
        await engine.dispose()
