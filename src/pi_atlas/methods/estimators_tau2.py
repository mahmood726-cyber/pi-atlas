"""Paule-Mandel (PM) tau^2 estimator.

Iterative solution to finding tau^2 such that Q_generalized(tau^2) = k - 1.
Formulas:
    w_i(tau2) = 1 / (v_i + tau2)
    y_bar(tau2) = sum(w_i * y_i) / sum(w_i)
    Q(tau2) = sum(w_i * (y_i - y_bar)**2)
    Solve Q(tau^2) - (k - 1) = 0 for tau^2 >= 0.

If Q(0) <= k - 1, then tau^2 = 0.
"""
from __future__ import annotations

import numpy as np
from scipy import optimize


def estimate_tau2_pm(y: np.ndarray, v: np.ndarray) -> float:
    """Estimate tau^2 using the Paule-Mandel method.
    
    Parameters
    ----------
    y : array-like, shape (k,)
    v : array-like, shape (k,)
        Sampling variances (SE^2).

    Returns
    -------
    float
        The PM estimate of tau^2.
    """
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    k = len(y)

    def q_func(tau2):
        w = 1.0 / (v + tau2)
        y_bar = np.sum(w * y) / np.sum(w)
        return np.sum(w * (y - y_bar)**2)

    # If heterogeneity is small, PM estimate is 0
    if q_func(0.0) <= k - 1:
        return 0.0

    # Objective function to find root: Q(tau2) - (k-1) = 0
    def objective(tau2):
        return q_func(tau2) - (k - 1)

    # Upper bound for search: empirical variance of y could be a loose upper bound
    # A conservative upper bound:
    upper_bound = np.var(y, ddof=1) * 10 
    
    # We know objective(0) > 0 and objective(inf) -> -(k-1) < 0.
    # We must find the root.
    try:
        res = optimize.root_scalar(objective, bracket=[0.0, max(100.0, upper_bound)], method='brentq')
        return float(res.root)
    except ValueError:
        # Fallback if bracketing fails, though Q(tau) is monotonically decreasing
        res = optimize.root_scalar(objective, x0=0.1, fprime=False, method='secant')
        return float(max(0.0, res.root))

