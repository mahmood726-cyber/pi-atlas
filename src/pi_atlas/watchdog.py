"""Watchdog: reset stuck cells + verify manifest SHA-256s."""
from __future__ import annotations

from typing import Dict

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore


def run_watchdog(queue: Queue, store: ResultStore, *, stuck_threshold_minutes: int = 60) -> Dict:
    """Run one watchdog pass; return a structured report."""
    stuck_reset = queue.reset_stuck(stuck_threshold_minutes=stuck_threshold_minutes)
    ok, bad = store.verify_manifest()
    return {
        "stuck_reset": stuck_reset,
        "manifest_ok": ok,
        "bad_files": [str(p) for p in bad],
    }
