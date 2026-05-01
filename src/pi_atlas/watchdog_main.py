"""systemd entry point for the watchdog."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.watchdog import run_watchdog


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", default=str(Path.home() / "pi-atlas" / "pi-atlas-queue.duckdb"))
    p.add_argument("--results", default=str(Path.home() / "pi-atlas" / "results"))
    args = p.parse_args()

    q = Queue(Path(args.queue))
    q.init_schema()
    store = ResultStore(Path(args.results))
    report = run_watchdog(q, store)
    print(json.dumps(report, indent=2))
    q.close()
    return 0 if report["manifest_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
