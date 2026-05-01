import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.watchdog import run_watchdog


def test_watchdog_resets_stuck_cells(tmp_path):
    q = Queue(tmp_path / "q.duckdb")
    q.init_schema()
    q.insert_cell("c1", phase="smoke", method="hts_dl", factor_json="{}")
    q.claim_one()
    q._execute_with_retry(
        "UPDATE cells SET claimed_at = claimed_at - INTERVAL '2 hours' WHERE cell_id='c1'"
    )

    store = ResultStore(tmp_path / "results")
    report = run_watchdog(q, store, stuck_threshold_minutes=60)

    assert report["stuck_reset"] == 1
    assert report["manifest_ok"] is True


def test_watchdog_flags_manifest_corruption(tmp_path):
    q = Queue(tmp_path / "q.duckdb")
    q.init_schema()
    store = ResultStore(tmp_path / "results")

    df = pd.DataFrame({"cell_id": ["c1"], "coverage": [1]})
    path = store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.0", dgp_family="normal"))
    with open(path, "ab") as f:
        f.write(b"CORRUPTED")

    report = run_watchdog(q, store, stuck_threshold_minutes=60)
    assert report["manifest_ok"] is False
    assert report["bad_files"]
