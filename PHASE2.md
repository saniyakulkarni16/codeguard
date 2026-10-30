# Phase 2: Accounts, History and Background Jobs

CodeGuard now has user accounts (JWT), saved history (SQL database), and background processing (Celery + Redis).

```
Browser ──► FastAPI ──► DB (jobs saved as "pending")
                │              ▲
                │ queue        │ result saved
                ▼              │
              Redis ──► Celery worker ──► run_job() ──► CodeGuard engine
Browser polls GET /api/jobs/{id} until status is "done"
```

## Two ways to run it

| Mode | Database | Jobs | Needs Docker? |
|---|---|---|---|
| **Local** (default) | SQLite file `codeguard.db` | FastAPI BackgroundTasks | No |
| **Full stack** | PostgreSQL | Celery + Redis worker | Yes |

### Local mode
```powershell
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
uvicorn codeguard.api:app --reload
```
Open http://localhost:8000, click **Create account**, then upload files.

Tip: set a fixed secret so logins survive restarts:
```powershell
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Full stack (PostgreSQL + Redis + worker)
```powershell
copy .env.example .env
```
Edit `.env` and fill in `SECRET_KEY` (generate with the command above) and `POSTGRES_PASSWORD`. Then:
```powershell
docker compose up --build
```
Open http://localhost:8000. Four containers start: `db`, `redis`, `api`, `worker`.
Watch the `worker` logs while you analyze a batch: you'll see the job picked up there, not in `api`.

## API

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | no | `{email, password}` (min 8 chars) |
| POST | `/api/auth/login` | no | form fields `username` (email) + `password` → `access_token` |
| GET | `/api/auth/me` | yes | current user |
| POST | `/api/jobs` | yes | upload files → **202** `{id, status:"pending"}` |
| GET | `/api/jobs` | yes | your 50 latest jobs (light: no code or reports) |
| GET | `/api/jobs/{id}` | yes | status; plus report and sources when `done` |
| DELETE | `/api/jobs/{id}` | yes | delete a job |

Interactive docs are at http://localhost:8000/docs (click **Authorize** and log in).

## Design decisions (interview material)

- **bcrypt with a SHA-256 pre-hash.** bcrypt silently truncates at 72 bytes; pre-hashing makes long passwords count in full.
- **Same error for unknown email and wrong password,** plus a dummy hash check for unknown users, so response timing doesn't reveal which emails exist.
- **JWT `algorithms=[...]` is pinned** when decoding. Omitting it enables the "alg: none" forgery attack.
- **No hard-coded secret.** `SECRET_KEY` comes from the environment; without it a random one is generated and a warning is logged.
- **Other users' jobs return 404, not 403,** so job ids aren't revealed. Every query filters by `user_id`.
- **Commit before queueing.** The job row is committed before `.delay()`, so the worker can never look for a row that doesn't exist yet.
- **`run_job` is idempotent.** It skips jobs that aren't pending/running, so a duplicate queue delivery can't redo work.
- **History list uses `defer()`** so it never loads the big `sources`/`report` JSON columns.
- **Why a queue at all?** Comparing N files is O(N²) work. Running it inside the request would block the web server and time out on large batches.

## Known limitations (say these in interviews)

- Tables are created with `create_all`. A real deployment would use **Alembic** migrations.
- Sources and reports are stored as JSON in the `jobs` table. At scale you'd move code to object storage (S3) and store references.
- No rate limiting or email verification yet. Natural next steps: `slowapi`, and refresh tokens instead of a single 60-minute access token.
- The access token is kept in `localStorage`. That's simple but exposed to XSS; the UI only inserts text via `textContent` for this reason. An httpOnly cookie is the stricter alternative.

## Resume bullets (no numbers to fill in; these are factual)

- Added JWT authentication (bcrypt-hashed passwords, per-user data isolation) and persistent analysis history on PostgreSQL via SQLAlchemy 2.0.
- Moved O(N²) comparison jobs to a Celery + Redis worker with idempotent task execution and status polling, keeping API responses non-blocking.
- Orchestrated API, worker, PostgreSQL and Redis with Docker Compose; covered auth, job lifecycle and cross-user access control with automated tests.
