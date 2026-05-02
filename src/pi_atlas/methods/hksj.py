"""Hartung-Knapp-Sidik-Jonkman (HKSJ) variance adjustment.

Uses DL tau^2 by default (as is standard in many Cochrane applications),
but inflates the variance of mu_hat.
Formulas:
    tau2 = tau2_DL
    w_star = 1 / (v_i + tau2)
    mu_hat = sum(w_star * y_i) / sum(w_star)
    q_re = sum(w_star * (y_i - mu_hat)^2)
    var_mu_hksj = q_re / ((k - 1) * sum(w_star))
    var_mu_adj = max(var_mu_hksj, 1 / sum(w_star))  # The modified HKSJ (Knapp & Hartung 2003) prevents var from shrinking below standard RE
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from scipy import stats

from pi_atlas.methods.hts_dl import fit_hts_dl


def fit_hksj(y: np.ndarray, v: np.ndarray, *, alpha: float = 0.05) -> Dict[str, float]:
    """Fit HKSJ prediction interval.
    
    This is standard HTS PI but using the HKSJ-adjusted variance for the mean
    (var_mu_adj) when computing both the CI and the PI.
    """
    k = len(y)
    if k < 3:
        raise ValueError("HKSJ PI requires k >= 3")
        
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)

    # 1. Get tau2_dl and standard FE Q from existing function
    # (We re-use the standard logic to ensure tau2 matches exactly)
    # Cochran's Q and tau2_dl
    w_fe = 1.0 / v
    y_bar_fe = (w_fe * y).sum() / w_fe.sum()
    Q = float((w_fe * (y - y_bar_fe) ** 2).sum())
    denom = w_fe.sum() - (w_fe * w_fe).sum() / w_fe.sum()
    tau2_dl = max(0.0, (Q - (k - 1)) / denom) if denom > 0 else 0.0

    # 2. HKSJ adjustment
    w_star = 1.0 / (v + tau2_dl)
    sum_w_star = w_star.sum()
    mu_hat = float((w_star * y).sum() / sum_w_star)
    
    # Standard RE variance
    var_mu_standard = 1.0 / sum_w_star
    
    # HKSJ variance multiplier (q_re / (k - 1))
    q_re = np.sum(w_star * (y - mu_hat)**2)
    hksj_factor = q_re / (k - 1)
    
    # Standard HKSJ (metafor 'knha' default allows shrinking)
    var_mu_adj = var_mu_standard * hksj_factor
    
    # Metafor does not allow the variance to be exactly zero to prevent division by zero in tests.
    # If y_i are exactly identical, q_re = 0.
    # In practice, if var_mu_adj is extremely small, it effectively means CI width 0.
    if var_mu_adj < 0.0:
        var_mu_adj = 0.0

    # 3. CI and PI using t-distribution and adjusted variance
    t_crit = stats.t.ppf(1 - alpha / 2.0, df=k - 1) # HKSJ CI uses t_{k-1}
    mu_ci_lower = mu_hat - t_crit * np.sqrt(var_mu_adj)
    mu_ci_upper = mu_hat + t_crit * np.sqrt(var_mu_adj)

    # For the PI, predict.rma with test="knha" uses t_{k-2} by default in metafor
    t_crit_pi = stats.t.ppf(1 - alpha / 2.0, df=k - 2)
    pi_half_width = t_crit_pi * np.sqrt(tau2_dl + var_mu_adj)
    pi_lower = mu_hat - pi_half_width
    pi_upper = mu_hat + pi_half_width

    return {
        "mu_hat": mu_hat,
        "mu_ci_lower": float(mu_ci_lower),
        "mu_ci_upper": float(mu_ci_upper),
        "tau2": float(tau2_dl),
        "pi_lower": float(pi_lower),
        "pi_upper": float(pi_upper),
        "k": k,
        "Q": Q,
    }
