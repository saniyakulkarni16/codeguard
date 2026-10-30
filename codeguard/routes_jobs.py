from datetime import datetime, timezone

from fastapi import (APIRouter, BackgroundTasks, Depends, File, Form,
                     HTTPException, Response, UploadFile)
from sqlalchemy import select
from sqlalchemy.orm import Session, defer

from . import config
from .db import get_db
from .jobs import run_job
from .loader import MAX_FILE_BYTES, load_zip
from .models import Job, User
from .security import get_current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
MAX_ZIP_BYTES = MAX_FILE_BYTES * 50


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:  # SQLite returns naive datetimes; they are UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _summary(j: Job) -> dict:
    return {
        "id": j.id, "status": j.status, "created_at": _iso(j.created_at),
        "finished_at": _iso(j.finished_at), "file_count": j.file_count,
        "max_score": j.max_score, "error": j.error,
    }


def _own_job(db: Session, user: User, job_id: int, light: bool = False) -> Job:
    stmt = select(Job).where(Job.id == job_id, Job.user_id == user.id)
    if light:
        stmt = stmt.options(defer(Job.sources), defer(Job.report), defer(Job.template))
    job = db.scalar(stmt)
    if job is None:  # 404 (not 403) so other users' job ids are not revealed
        raise HTTPException(404, "Job not found")
    return job


@router.post("", status_code=202)
def create_job(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    template: UploadFile | None = File(None),
    min_score: float = Form(0.2),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Store the upload and queue the analysis. Poll GET /api/jobs/{id} for the result."""
    if not 0.0 <= min_score <= 1.0:
        raise HTTPException(400, "min_score must be between 0 and 1")

    sources: dict[str, str] = {}
    for f in files:
        name = f.filename or "unnamed.py"
        data = f.file.read(MAX_ZIP_BYTES + 1)
        if len(data) > MAX_ZIP_BYTES:
            raise HTTPException(413, f"{name} is too large")
        if name.endswith(".zip"):
            try:
                sources.update(load_zip(data))
            except Exception:
                raise HTTPException(400, f"{name} is not a valid zip file")
        elif name.endswith(".py"):
            if len(data) > MAX_FILE_BYTES:
                raise HTTPException(413, f"{name} is too large")
            sources[name] = data.decode(errors="replace")
    if len(sources) < 2:
        raise HTTPException(400, "Upload at least two .py files (or a .zip containing them).")

    tmpl = template.file.read(MAX_FILE_BYTES).decode(errors="replace") if template else None
    job = Job(user_id=user.id, status="pending", file_count=len(sources),
              min_score=min_score, template=tmpl, sources=sources)
    db.add(job)
    db.commit()  # commit BEFORE queueing, so the worker can always find the row

    if config.USE_CELERY:
        try:
            from .worker import run_job_task
            run_job_task.delay(job.id)
        except Exception:
            job.status, job.error = "failed", "Job queue unavailable. Try again later."
            db.commit()
            raise HTTPException(503, "Job queue unavailable")
    else:
        background_tasks.add_task(run_job, job.id)
    return {"id": job.id, "status": job.status}


@router.get("")
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    stmt = (select(Job).where(Job.user_id == user.id)
            .options(defer(Job.sources), defer(Job.report), defer(Job.template))
            .order_by(Job.id.desc()).limit(50))
    return [_summary(j) for j in db.scalars(stmt)]


@router.get("/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    job = _own_job(db, user, job_id)
    out = _summary(job)
    if job.status == "done":
        out["report"] = job.report
        out["sources"] = job.sources
    return out


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    db.delete(_own_job(db, user, job_id, light=True))
    db.commit()
    return Response(status_code=204)
