import os
import tempfile
from pathlib import Path

# Must be set BEFORE any codeguard module is imported (the DB engine reads them at import time).
_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'test.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key-for-unit-tests-only-1234567890"
os.environ["USE_CELERY"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    from codeguard.db import Base, engine, init_db
    init_db()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    from codeguard.api import app
    return TestClient(app)
