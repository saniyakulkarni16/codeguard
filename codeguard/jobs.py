"""The actual work of a job. Called by Celery (worker container) or FastAPI BackgroundTasks."""
import logging

from .compare import compare_files
from .db import SessionLocal
from .models import Job, utcnow

log = logging.getLogger("codeguard")


def run_job(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        if job is None or job.status not in ("pending", "running"):
            return  # deleted meanwhile, or already processed (e.g. duplicate delivery)
        job.status = "running"
        db.commit()
        try:
            report = compare_files(job.sources, template=job.template, min_score=job.min_score)
            data = report.to_dict()
            job.report = data
            job.max_score = max((p["score"] for p in data["pairs"]), default=0.0)
            job.status = "done"
        except Exception:
            log.exception("job %s failed", job_id)
            job.status = "failed"
            job.error = "Analysis failed. Check that the files are valid Python."
        job.finished_at = utcnow()
        db.commit()
