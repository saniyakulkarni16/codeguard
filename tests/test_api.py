import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from codeguard.api import app

client = TestClient(app)
S = Path(__file__).resolve().parent.parent / "samples"


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_compare_files():
    files = [("files", (n, (S / n).read_bytes(), "text/x-python"))
             for n in ("student_a.py", "student_b_renamed.py", "student_d_original.py")]
    r = client.post("/api/compare", files=files, data={"min_score": "0.2"})
    assert r.status_code == 200
    body = r.json()
    assert body["pairs"][0]["score"] > 0.9
    assert "student_a.py" in body["sources"]


def test_compare_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in S.glob("*.py"):
            z.writestr(p.name, p.read_text())
    r = client.post("/api/compare", files=[("files", ("subs.zip", buf.getvalue(), "application/zip"))])
    assert r.status_code == 200 and r.json()["pairs"]


def test_needs_two_files():
    r = client.post("/api/compare", files=[("files", ("a.py", b"x = 1", "text/x-python"))])
    assert r.status_code == 400
