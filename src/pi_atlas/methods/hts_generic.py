"""Higgins-Thompson-Spiegelhalter prediction interval with generic tau2.

Allows substituting different tau^2 estimators (DL, REML, PM, SJ).
"""
from __future__ import annotations

from typing import Dict, Callable

import numpy as np
from scipy import stats

from pi_atlas.methods.hts_dl import fit_hts_dl


def _compute_hts_pi(y: np.ndarray, v: np.ndarray, tau2_est: float, alpha: float) -> Dict[str, float]:
    """Helper to compute HTS PI given a pre-calculated tau2."""
    k = len(y)
    
    # Random-effect weights
    w_star = 1.0 / (v + tau2_est)
    sum_w_star = w_star.sum()
    mu_hat = float((w_star * y).sum() / sum_w_star)
    var_mu = float(1.0 / sum_w_star)

    # CI for mu_hat (Wald, z-based)
    z = stats.norm.ppf(1 - alpha / 2.0)
    mu_ci_lower = mu_hat - z * np.sqrt(var_mu)
    mu_ci_upper = mu_hat + z * np.sqrt(var_mu)

    # HTS PI: t_{k-2}
    t_crit = stats.t.ppf(1 - alpha / 2.0, df=k - 2)
    pi_half_width = t_crit * np.sqrt(tau2_est + var_mu)
    pi_lower = mu_hat - pi_half_width
    pi_upper = mu_hat + pi_half_width

    # Cochran's Q (standard fixed-effect weights)
    w_fe = 1.0 / v
    y_bar_fe = (w_fe * y).sum() / w_fe.sum()
    Q = float((w_fe * (y - y_bar_fe) ** 2).sum())

    return {
        "mu_hat": mu_hat,
        "mu_ci_lower": float(mu_ci_lower),
        "mu_ci_upper": float(mu_ci_upper),
        "tau2": float(tau2_est),
        "pi_lower": float(pi_lower),
        "pi_upper": float(pi_upper),
        "k": k,
        "Q": Q,
    }


def fit_hts_pm(y: np.ndarray, v: np.ndarray, *, alpha: float = 0.05) -> Dict[str, float]:
    """Fit HTS prediction interval using Paule-Mandel tau^2 estimator."""
    from pi_atlas.methods.estimators_tau2 import estimate_tau2_pm

    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    if len(y) < 3:
        raise ValueError("HTS PI requires k >= 3")

    tau2_pm = estimate_tau2_pm(y, v)
    return _compute_hts_pi(y, v, tau2_pm, alpha)


def fit_hts_sj(y: np.ndarray, v: np.ndarray, *, alpha: float = 0.05) -> Dict[str, float]:
    """Fit HTS prediction interval using Sidik-Jonkman tau^2 estimator."""
    from pi_atlas.methods.estimators_sj import estimate_tau2_sj

    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    if len(y) < 3:
        raise ValueError("HTS PI requires k >= 3")

    tau2_sj = estimate_tau2_sj(y, v)
    return _compute_hts_pi(y, v, tau2_sj, alpha)

