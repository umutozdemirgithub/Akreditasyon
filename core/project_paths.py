from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    """Return the MEDEK web project root by walking upward."""
    here = (start or Path(__file__).resolve()).resolve()
    candidates = [here.parent, *here.parents]
    for candidate in candidates:
        if (
            (candidate / "backend" / "main.py").exists()
            and (candidate / "frontend" / "package.json").exists()
            and (candidate / "docker-compose.web.yml").exists()
        ):
            return candidate
    raise FileNotFoundError(f"Could not locate MEDEK web project root from {here}")


def project_path(*parts: str, start: Path | None = None) -> Path:
    """Build an absolute path under the discovered project root."""
    return find_project_root(start).joinpath(*parts)
