"""Step 5: REST API.  Run: uvicorn codeguard.api:app --reload"""
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from .compare import compare_files
from .loader import MAX_FILE_BYTES, load_zip

app = FastAPI(title="CodeGuard", version="1.0.0")
STATIC = Path(__file__).parent / "static"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/compare")
def compare(
    files: list[UploadFile] = File(...),
    template: UploadFile | None = File(None),
    min_score: float = Form(0.2),
) -> dict:
    """Upload several .py files and/or one .zip; returns scores, matrix and highlighted regions."""
    sources: dict[str, str] = {}
    for f in files:
        data = f.file.read(MAX_FILE_BYTES * 50 + 1)
        name = f.filename or "unnamed.py"
        if name.endswith(".zip"):
            sources.update(load_zip(data))
        elif name.endswith(".py"):
            if len(data) > MAX_FILE_BYTES:
                raise HTTPException(413, f"{name} is too large")
            sources[name] = data.decode(errors="replace")
    if len(sources) < 2:
        raise HTTPException(400, "Upload at least two .py files (or a .zip containing them).")

    tmpl = template.file.read(MAX_FILE_BYTES).decode(errors="replace") if template else None
    report = compare_files(sources, template=tmpl, min_score=min_score).to_dict()
    report["sources"] = sources  # the UI needs the code for the side-by-side view
    return report


# must be registered last so it doesn't shadow the /api routes
app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
