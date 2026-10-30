"""REST API.  Run: uvicorn codeguard.api:app --reload"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routes_auth import router as auth_router
from .routes_jobs import router as jobs_router

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables if they don't exist (use Alembic for real migrations)
    yield


app = FastAPI(title="CodeGuard", version="2.0.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(jobs_router)

# must be registered last so it doesn't shadow the /api routes
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
