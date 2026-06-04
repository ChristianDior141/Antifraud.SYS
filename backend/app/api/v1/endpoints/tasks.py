from fastapi import APIRouter, Depends
from app.core.deps import require_analyst
from app.models.user import User

router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.get("/{task_id}")
async def task_status(task_id: str, current_user: User = Depends(require_analyst)):
    """Poll the state/result of a queued Celery task."""
    from app.core.celery_app import celery_app
    res = celery_app.AsyncResult(task_id)
    result = None
    if res.successful():
        result = res.result
    elif res.failed():
        result = {"error": str(res.result)}
    return {"task_id": task_id, "state": res.state, "result": result}
