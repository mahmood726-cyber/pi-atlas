import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.worker import run_one_cell


def noop_fit(cell_config, rng):
    """Trivial fit function for testing: returns a single-row result."""
    return {"mu_hat": 0.0, "pi_lower": -1.0, "pi_upper": 1.0, "coverage": 1}


def test_run_one_cell_writes_to_parquet_and_marks_done():
    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        q = Queue(dpath / "q.duckdb")
        q.init_schema()
        store = ResultStore(dpath / "results")

        cfg = {"k": 3, "tau2": 0.0, "dgp": "normal", "method": "hts_dl", "replicate_id": 0}
        q.insert_cell("c1", phase="smoke", method="hts_dl", factor_json=json.dumps(cfg))

        claimed = q.claim_one()
        assert claimed is not None

        run_one_cell(claimed, cfg, store=store, fit_fn=noop_fit)
        q.mark_done(claimed["cell_id"])

        # Status should be done
        row = q.get_cell("c1")
        assert row["status"] == "done"

        # Parquet should exist with 1 row
        manifest = store.read_manifest()
        assert len(manifest) == 1
        assert manifest.iloc[0]["rows"] == 1
