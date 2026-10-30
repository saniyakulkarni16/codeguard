"""Celery worker.  Run:  celery -A codeguard.worker.celery_app worker --loglevel=info"""
from celery import Celery

from . import config
from .jobs import run_job

celery_app = Celery("codeguard", broker=config.REDIS_URL)
celery_app.conf.broker_connection_retry_on_startup = True


@celery_app.task(name="codeguard.run_job")
def run_job_task(job_id: int) -> None:
    run_job(job_id)
