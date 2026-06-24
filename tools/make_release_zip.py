from __future__ import annotations

import fnmatch
import zipfile
import argparse
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "ver_100_role_theme_sync.zip"
ARCHIVE_ROOT = Path("ver_100")

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "medek_data",
    "node_modules",
    "dist",
    ".venv",
    "venv",
    "outputs",
    "work",
}
EXCLUDED_PATTERNS = {
    "*.sqlite3",
    "*.db",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.zip",
}
DISALLOWED_ARCHIVE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "medek_data",
    "node_modules",
    "dist",
    ".venv",
    "venv",
    "outputs",
    "work",
}
DISALLOWED_ARCHIVE_PATTERNS = {
    "*.sqlite3",
    "*.db",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.zip",
}


def is_secret_env_name(name: str) -> bool:
    return name.startswith(".env") and not name.endswith(".example")


def is_secret_env_file(path: Path) -> bool:
    return is_secret_env_name(path.name)


def is_excluded(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return True
    if path.is_file():
        if is_secret_env_file(path):
            return True
        return any(fnmatch.fnmatch(path.name, pattern) for pattern in EXCLUDED_PATTERNS)
    return False


def is_disallowed_archive_member(name: str) -> bool:
    parts = [part for part in PurePosixPath(name).parts if part not in {"", "."}]
    if not parts:
        return False
    lowered_parts = [part.lower() for part in parts]
    if any(part in DISALLOWED_ARCHIVE_DIRS for part in lowered_parts):
        return True
    file_name = lowered_parts[-1]
    if is_secret_env_name(file_name):
        return True
    return any(fnmatch.fnmatch(file_name, pattern) for pattern in DISALLOWED_ARCHIVE_PATTERNS)


def verify_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        bad_members = [
            info.filename
            for info in archive.infolist()
            if not info.is_dir() and is_disallowed_archive_member(info.filename)
        ]
    if bad_members:
        joined = "\n  - ".join(bad_members[:50])
        extra = "" if len(bad_members) <= 50 else f"\n  ... and {len(bad_members) - 50} more"
        raise RuntimeError(f"Unsafe release archive contents:\n  - {joined}{extra}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean AKYS release zip.")
    parser.add_argument("--output", default=str(OUTPUT), help="Output zip path.")
    parser.add_argument("--archive-root", default=str(ARCHIVE_ROOT), help="Top-level directory name inside the zip.")
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir() or is_excluded(path):
                continue
            archive_name = Path(args.archive_root) / path.relative_to(ROOT)
            archive.write(path, archive_name.as_posix())
    verify_archive(output)
    print(output)


if __name__ == "__main__":
    main()
