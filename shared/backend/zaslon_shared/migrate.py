from __future__ import annotations

import json

from .migrations import run_migrations


def main() -> None:
    print(json.dumps({"migrations": run_migrations()}, indent=2))


if __name__ == "__main__":
    main()

