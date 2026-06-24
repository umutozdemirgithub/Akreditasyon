from __future__ import annotations

import argparse
from pathlib import Path

from make_release_zip import verify_archive


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that an AKYS release zip does not contain dirty or secret files.")
    parser.add_argument("archive", help="Release zip path to inspect.")
    args = parser.parse_args()
    verify_archive(Path(args.archive))
    print(f"OK: {args.archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
