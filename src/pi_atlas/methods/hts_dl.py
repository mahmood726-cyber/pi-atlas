"""Higgins-Thompson-Spiegelhalter prediction interval with DL tau² estimator.

Formulas:
    w_i      = 1 / v_i
    Q        = Σ w_i (y_i - y_bar_FE)²,  y_bar_FE = Σ w_i y_i / Σ w_i
    tau²_DL  = max(0, (Q - (k-1)) / (Σ w_i - Σ w_i² / Σ w_i))
    w*_i     = 1 / (v_i + tau²)
    μ̂        = Σ w*_i y_i / Σ w*_i
    Var(μ̂)   = 1 / Σ w*_i
    CI(μ̂)    = μ̂ ± z_{α/2} × √Var(μ̂)    (z, RE Wald — NOT HKSJ — for the DL baseline)
    PI       = μ̂ ± t_{k-2, α/2} × √(tau² + Var(μ̂))   (HTS 2009)

NB: Per ~/.claude/rules/advanced-stats.md — PI uses t_{k-2} and is undefined
for k<3. This is the **canonical HTS PI**, the most commonly reported PI in
Cochrane reviews.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from scipy import stats


def fit_hts_dl(y: np.ndarray, v: np.ndarray, *, alpha: float = 0.05) -> Dict[str, float]:
    """Fit HTS-DL prediction interval.

    Parameters
    ----------
    y : array-like, shape (k,)
        Study effect estimates (log-scale for ratios).
    v : array-like, shape (k,)
        Study sampling variances (SE²).
    alpha : float
        Two-sided significance level (default 0.05 for 95% PI).

    Returns
    -------
    dict with keys: mu_hat, mu_ci_lower, mu_ci_upper, tau2, pi_lower, pi_upper, k, Q.

    Raises
    ------
    ValueError if k < 3 (PI undefined per HTS 2009).
    """
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    k = len(y)
    if k < 3:
        raise ValueError(f"HTS PI requires k >= 3; got k={k}")
    if len(v) != k:
        raise ValueError("y and v must have the same length")

    # Fixed-effect weights
    w = 1.0 / v
    sum_w = w.sum()
    y_bar_fe = (w * y).sum() / sum_w

    # Cochran's Q
    Q = float((w * (y - y_bar_fe) ** 2).sum())

    # DerSimonian-Laird tau²
    denom = sum_w - (w * w).sum() / sum_w
    tau2_dl = max(0.0, (Q - (k - 1)) / denom) if denom > 0 else 0.0

    # Random-effect weights
    w_star = 1.0 / (v + tau2_dl)
    sum_w_star = w_star.sum()
    mu_hat = float((w_star * y).sum() / sum_w_star)
    var_mu = float(1.0 / sum_w_star)

    # CI for mu_hat (Wald, z-based — the standard DL reporting)
    z = stats.norm.ppf(1 - alpha / 2.0)
    mu_ci_lower = mu_hat - z * np.sqrt(var_mu)
    mu_ci_upper = mu_hat + z * np.sqrt(var_mu)

    # HTS PI: t_{k-2}
    t_crit = stats.t.ppf(1 - alpha / 2.0, df=k - 2)
    pi_half_width = t_crit * np.sqrt(tau2_dl + var_mu)
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
