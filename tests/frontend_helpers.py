from __future__ import annotations

from pathlib import Path


def read_frontend_source(root: Path) -> str:
    src = root / "frontend" / "src"
    paths = [*sorted(src.rglob("*.jsx")), *sorted(src.rglob("*.js"))]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def read_frontend_styles(root: Path) -> str:
    src = root / "frontend" / "src"
    paths = [src / "styles.css", *sorted((src / "styles").glob("*.css"))]
    return "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists())
