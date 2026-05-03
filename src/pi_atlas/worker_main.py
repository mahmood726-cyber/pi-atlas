"""systemd entry point: python -m pi_atlas.worker_main --worker-id N"""
from __future__ import annotations

import argparse
from pathlib import Path

from pi_atlas.worker import worker_loop
from pi_atlas.loo_fit import fit_loo_hts_dl
from pi_atlas.methods.hts_generic import fit_hts_pm, fit_hts_reml, fit_hts_sj
from pi_atlas.methods.hksj import fit_hksj
from pi_atlas.methods.partlett_riley import fit_partlett_riley
from pi_atlas.methods.nagashima_noma import fit_nagashima_noma
from pi_atlas.methods.bayesmeta import fit_bayesmeta
from pi_atlas.methods.bayes_map import fit_bayes_map
from pi_atlas.methods.np_bootstrap import fit_np_bootstrap


# Map string method names to their python functions
METHOD_MAP = {
    "hts_dl": None,  # Handled inside fit_loo_hts_dl directly for now, we should genericize it
    "hts_pm": fit_hts_pm,
    "hts_reml": fit_hts_reml,
    "hts_sj": fit_hts_sj,
    "hksj": fit_hksj,
    "partlett_riley": fit_partlett_riley,
    "nagashima_noma": fit_nagashima_noma,
    "bayesmeta": fit_bayesmeta,
    "bayes_map": fit_bayes_map,
    "np_bootstrap": fit_np_bootstrap
}

def _generic_loo_fit(cell_config, rng, method_fn):
    import numpy as np
    from pi_atlas.schema import SCHEMA_VERSION
    
    y_full = np.array(cell_config["y"], dtype=np.float64)
    v_full = np.array(cell_config["v"], dtype=np.float64)
    idx = cell_config["held_out_index"]
    
    # Held out
    y_target = y_full[idx]
    v_target = v_full[idx]
    
    # Train set
    y_train = np.delete(y_full, idx)
    v_train = np.delete(v_full, idx)
    
    # Fit
    res = method_fn(y_train, v_train)
    
    # Check coverage (observed-effect estimand)
    coverage_obs = int(res["pi_lower"] <= y_target <= res["pi_upper"])
    
    return {
        "k": int(res["k"]),
        "mu_hat": res["mu_hat"],
        "mu_ci_lower": res["mu_ci_lower"],
        "mu_ci_upper": res["mu_ci_upper"],
        "tau2": res["tau2"],
        "pi_lower": res["pi_lower"],
        "pi_upper": res["pi_upper"],
        "Q": res["Q"],
        "coverage_true": None,  # unobservable for real-data LOO
        "coverage_obs": coverage_obs,
        "schema_version": SCHEMA_VERSION,
        # metadata
        "ma_id": cell_config["ma_id"],
        "analysis_id": cell_config["analysis_id"],
        "held_out_index": idx
    }

def fit_dispatcher(cell_config, rng):
    """Route to the correct fit function based on config."""
    method = cell_config.get("method", "hts_dl")
    
    if method == "hts_dl" and "held_out_index" in cell_config:
        return fit_loo_hts_dl(cell_config, rng)
        
    if "held_out_index" in cell_config and method in METHOD_MAP:
        return _generic_loo_fit(cell_config, rng, METHOD_MAP[method])
    
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
