from __future__ import annotations

import sys

from redis import Redis
from rq import Worker

from .config import MEDEK_REDIS_URL, MEDEK_RQ_QUEUE
from .db import get_conn, init_db


def healthcheck() -> int:
    """Validate worker runtime dependencies for Docker healthchecks."""
    try:
        init_db()
        with get_conn() as conn:
            conn.execute("SELECT 1")
        redis_conn = Redis.from_url(MEDEK_REDIS_URL)
        redis_conn.ping()
        return 0
    except Exception as exc:  # noqa: BLE001 - healthcheck prints a concise failure for Docker logs
        print(f"worker healthcheck failed: {exc}", file=sys.stderr)
        return 1


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--healthcheck":
        return healthcheck()
    init_db()
    redis_conn = Redis.from_url(MEDEK_REDIS_URL)
    worker = Worker([MEDEK_RQ_QUEUE], connection=redis_conn)
    worker.work(with_scheduler=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
