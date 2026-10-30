import io
import time
import zipfile
from pathlib import Path

S = Path(__file__).resolve().parent.parent / "samples"
PW = "correct horse battery"


def sample_files(*names):
    return [("files", (n, (S / n).read_bytes(), "text/x-python")) for n in names]


def login(client, email="a@example.com", password=PW):
    client.post("/api/auth/register", json={"email": email, "password": password})
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def wait_done(client, headers, job_id, tries=50):
    for _ in range(tries):
        job = client.get(f"/api/jobs/{job_id}", headers=headers).json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_register_duplicate_and_validation(client):
    ok = client.post("/api/auth/register", json={"email": "a@example.com", "password": PW})
    assert ok.status_code == 201
    dup = client.post("/api/auth/register", json={"email": "A@Example.com", "password": PW})
    assert dup.status_code == 409  # emails are case-insensitive
    assert client.post("/api/auth/register", json={"email": "nope", "password": PW}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 422


def test_login_wrong_password_and_unknown_user(client):
    login(client)
    bad = client.post("/api/auth/login", data={"username": "a@example.com", "password": "wrong-password"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", data={"username": "x@example.com", "password": PW})
    assert unknown.status_code == 401
    assert bad.json() == unknown.json()  # same message: no user enumeration


def test_protected_routes_need_a_valid_token(client):
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_me(client):
    h = login(client)
    assert client.get("/api/auth/me", headers=h).json()["email"] == "a@example.com"


def test_create_job_and_get_report(client):
    h = login(client)
    r = client.post("/api/jobs", headers=h, files=sample_files(
        "student_a.py", "student_b_renamed.py", "student_d_original.py"))
    assert r.status_code == 202
    job = wait_done(client, h, r.json()["id"])
    assert job["status"] == "done"
    assert job["report"]["pairs"][0]["score"] > 0.9
    assert "student_a.py" in job["sources"]
    assert job["max_score"] > 0.9


def test_zip_upload(client):
    h = login(client)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in S.glob("*.py"):
            z.writestr(p.name, p.read_text())
    r = client.post("/api/jobs", headers=h,
                    files=[("files", ("subs.zip", buf.getvalue(), "application/zip"))])
    assert r.status_code == 202
    assert wait_done(client, h, r.json()["id"])["report"]["pairs"]


def test_needs_two_files(client):
    h = login(client)
    r = client.post("/api/jobs", headers=h, files=sample_files("student_a.py"))
    assert r.status_code == 400


def test_history_list_and_delete(client):
    h = login(client)
    jid = client.post("/api/jobs", headers=h, files=sample_files(
        "student_a.py", "student_b_renamed.py")).json()["id"]
    wait_done(client, h, jid)
    history = client.get("/api/jobs", headers=h).json()
    assert [j["id"] for j in history] == [jid]
    assert "report" not in history[0] and "sources" not in history[0]  # list stays light
    assert client.delete(f"/api/jobs/{jid}", headers=h).status_code == 204
    assert client.get(f"/api/jobs/{jid}", headers=h).status_code == 404


def test_users_cannot_see_each_others_jobs(client):
    alice = login(client, "alice@example.com")
    bob = login(client, "bob@example.com")
    jid = client.post("/api/jobs", headers=alice, files=sample_files(
        "student_a.py", "student_b_renamed.py")).json()["id"]
    assert client.get(f"/api/jobs/{jid}", headers=bob).status_code == 404
    assert client.delete(f"/api/jobs/{jid}", headers=bob).status_code == 404
    assert client.get("/api/jobs", headers=bob).json() == []
