from __future__ import annotations

import json

from .job_queue import worker_readiness


def main() -> None:
    status = worker_readiness()
    print(json.dumps(status, indent=2))
    if not status.get("available"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

