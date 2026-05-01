"""LOO fit logic for workers."""
from __future__ import annotations

import numpy as np
from pi_atlas.methods.hts_dl import fit_hts_dl
from pi_atlas.schema import SCHEMA_VERSION


def fit_loo_hts_dl(cell_config: dict, rng: np.random.Generator) -> dict:
    """Run HTS-DL on k-1 studies and check coverage of the held-out study."""
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
    res = fit_hts_dl(y_train, v_train)
    
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
