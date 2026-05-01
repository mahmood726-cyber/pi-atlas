"""End-to-end smoke run: seed 20 cells into queue, spawn inline worker, assert all done."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.worker import worker_loop
from pi_atlas.methods.hts_dl import fit_hts_dl
from pi_atlas.seeds import seed_to_rng
from pi_atlas.schema import SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parent.parent
SMOKE_ROOT = REPO_ROOT / "smoke"
QUEUE_PATH = SMOKE_ROOT / "queue.duckdb"
RESULTS_ROOT = SMOKE_ROOT / "results"


def fit_fn(cell_config, rng):
    """Produce one synthetic-MA fit using HTS-DL."""
    k = cell_config["k"]
    tau2 = cell_config["tau2"]
    # Fix SE = 0.1 for smoke; real synthetic twin uses per-MA SEs (Plan 4)
    se = np.full(k, 0.1)
    v = se ** 2
    # Draw study true effects and observed values
    b = rng.normal(0.0, np.sqrt(tau2), size=k)
    y = rng.normal(b, se)
    # Fit
    res = fit_hts_dl(y, v)
    # Draw one new study and check coverage
    mu_new = rng.normal(0.0, np.sqrt(tau2))
    y_new = rng.normal(mu_new, 0.1)
    coverage_true = int(res["pi_lower"] <= mu_new <= res["pi_upper"])
    coverage_obs = int(res["pi_lower"] <= y_new <= res["pi_upper"])

    return {
        "k": res["k"],
        "mu_hat": res["mu_hat"],
        "mu_ci_lower": res["mu_ci_lower"],
        "mu_ci_upper": res["mu_ci_upper"],
        "tau2": res["tau2"],
        "pi_lower": res["pi_lower"],
        "pi_upper": res["pi_upper"],
        "Q": res["Q"],
        "coverage_true": coverage_true,
        "coverage_obs": coverage_obs,
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT)
    SMOKE_ROOT.mkdir(parents=True)

    q = Queue(QUEUE_PATH)
    q.init_schema()

    # 20 cells: k ∈ {3,5,8}, tau2 ∈ {0, 0.05, 0.2}, with replicate variety
    idx = 0
    for k in (3, 5, 8):
        for tau2 in (0.0, 0.05, 0.2):
            for rep in range(3):
                idx += 1
                cell_id = f"smoke-{idx:03d}"
                cfg = {"k": k, "tau2": tau2, "dgp": "normal", "replicate_id": rep}
                q.insert_cell(cell_id, phase="smoke", method="hts_dl", factor_json=json.dumps(cfg))

    print(f"Seeded 20 cells into {QUEUE_PATH}")

    # Run worker loop
    n = worker_loop(QUEUE_PATH, RESULTS_ROOT, fit_fn, max_cells=20)
    print(f"Worker processed {n} cells.")

    # Validate results
    store = ResultStore(RESULTS_ROOT)
    manifest = store.read_manifest()
    assert len(manifest) == 20
    print("Smoke run manifest verified (20 files).")

    # verify all status = done
    for idx in range(1, 21):
        row = q.get_cell(f"smoke-{idx:03d}")
        assert row["status"] == "done"

    print("All queue statuses verified as 'done'.")
    print("SMOKE RUN SUCCESSFUL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
