"""Worker main loop — pop cell, run fit, append result."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Mapping

import pandas as pd

from pi_atlas.queue import Queue
from pi_atlas.seeds import derive_seed_hex, seed_to_rng
from pi_atlas.storage import ResultStore


def run_one_cell(
    claimed_row: Mapping,
    cell_config: Mapping,
    *,
    store: ResultStore,
    fit_fn: Callable,
) -> None:
    """Execute a single cell: derive seed, run fit, append result."""
    replicate_id = cell_config.get("replicate_id", 0)
    seed_hex = derive_seed_hex(cell_config, replicate_id)
    rng = seed_to_rng(seed_hex)

    result = fit_fn(cell_config, rng)

    # Annotate with bookkeeping columns
    result = dict(result)
    result["cell_id"] = claimed_row["cell_id"]
    result["seed_hex"] = seed_hex
    result["phase"] = claimed_row["phase"]
    result["method"] = claimed_row["method"]

    df = pd.DataFrame([result])

    partition = dict(
        phase=claimed_row["phase"],
        method=claimed_row["method"],
        tau2_level=str(cell_config.get("tau2", "NA")),
        dgp_family=cell_config.get("dgp", "NA"),
    )
    store.flush(df, partition=partition)


def worker_loop(
    queue_path: Path,
    results_root: Path,
    fit_fn: Callable,
    *,
    max_cells: int = None,
    poll_sleep_s: float = 5.0,
) -> int:
    """Run a worker loop. Returns number of cells processed."""
    q = Queue(queue_path)
    q.init_schema()
    store = ResultStore(results_root)

    n_done = 0
    while True:
        if max_cells is not None and n_done >= max_cells:
            break
        claimed = q.claim_one()
        if claimed is None:
            if max_cells is not None:
                break
            time.sleep(poll_sleep_s)
            continue
        cfg = json.loads(claimed["factor_json"])
        try:
            run_one_cell(claimed, cfg, store=store, fit_fn=fit_fn)
            q.mark_done(claimed["cell_id"])
            n_done += 1
        except Exception as e:
            # Leave in 'running' — watchdog will reset after threshold.
            # Log then re-raise so systemd can restart on real bugs.
            print(f"[worker] cell {claimed['cell_id']} failed: {e!r}")
            raise

    q.close()
    return n_done
