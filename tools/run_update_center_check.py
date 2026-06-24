from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.db import init_db
from backend.update_center import run_update_center_check


def main() -> int:
    parser = argparse.ArgumentParser(description="AKYS Güncelleme Merkezi kontrolünü çalıştırır.")
    parser.add_argument("--username", default="admin", help="Kontrolü çalıştıracak yönetici kullanıcı adı")
    parser.add_argument("--scope", default="all", choices=["all", "template", "academic"], help="Kontrol kapsamı")
    parser.add_argument("--online", action="store_true", help="Resmi web/YÖK Atlas canlı kontrolünü çalıştır")
    args = parser.parse_args()
    init_db()
    result = run_update_center_check(args.username, scope=args.scope, online=args.online)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
