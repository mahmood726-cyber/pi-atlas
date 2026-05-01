"""systemd entry point: python -m pi_atlas.worker_main --worker-id N"""
from __future__ import annotations

import argparse
from pathlib import Path

from pi_atlas.worker import worker_loop
from pi_atlas.loo_fit import fit_loo_hts_dl


def fit_dispatcher(cell_config, rng):
    """Route to the correct fit function based on config."""
    # This dispatcher can be expanded as we add more methods/phases
    # For now, it handles LOO and the smoke placeholder
    if "ma_id" in cell_config and "held_out_index" in cell_config:
        return fit_loo_hts_dl(cell_config, rng)
    
    # Smoke/Placeholder
    return {"mu_hat": 0.0, "pi_lower": -1.0, "pi_upper": 1.0, "coverage": 1, "schema_version": "1.0"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--worker-id", required=True)
    p.add_argument("--queue", default=str(Path.home() / "pi-atlas" / "pi-atlas-queue.duckdb"))
    p.add_argument("--results", default=str(Path.home() / "pi-atlas" / "results"))
    p.add_argument("--max-cells", type=int, default=None)
    args = p.parse_args()
    print(f"[worker-{args.worker_id}] starting")
    n = worker_loop(
        queue_path=Path(args.queue),
        results_root=Path(args.results),
        fit_fn=fit_dispatcher,
        max_cells=args.max_cells,
    )
    print(f"[worker-{args.worker_id}] processed {n} cells")


if __name__ == "__main__":
    main()
