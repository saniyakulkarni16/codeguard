"""Settings, read from environment variables (see .env.example)."""
import logging
import os
import secrets

log = logging.getLogger("codeguard")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./codeguard.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
USE_CELERY = os.getenv("USE_CELERY", "0") == "1"  # 0 = FastAPI BackgroundTasks, 1 = Celery + Redis
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
JWT_ALGORITHM = "HS256"

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    # Never ship a hard-coded default secret. A random one works for local dev,
    # but tokens stop working on restart and across multiple processes.
    SECRET_KEY = secrets.token_urlsafe(32)
    log.warning("SECRET_KEY is not set; using a random key for this process only.")
