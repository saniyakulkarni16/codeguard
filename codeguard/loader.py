"""Load .py files from a directory or a zip archive (with basic safety limits)."""
import io
import zipfile
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 50_000_000
MAX_FILES = 2_000


def load_dir(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    root = Path(path)
    for p in sorted(root.rglob("*.py")):
        if p.stat().st_size <= MAX_FILE_BYTES:
            out[str(p.relative_to(root))] = p.read_text(errors="replace")
    return out


def load_zip(data: bytes) -> dict[str, str]:
    out: dict[str, str] = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            name = info.filename
            if info.is_dir() or not name.endswith(".py") or name.startswith("__MACOSX"):
                continue
            if ".." in Path(name).parts or info.file_size > MAX_FILE_BYTES:
                continue
            total += info.file_size  # declared size: guards against zip bombs
            if total > MAX_TOTAL_BYTES or len(out) >= MAX_FILES:
                break
            out[name] = zf.read(info).decode(errors="replace")
    return out
