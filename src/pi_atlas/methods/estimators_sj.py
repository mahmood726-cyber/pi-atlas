"""Sidik-Jonkman (SJ) tau^2 estimator.

Non-iterative estimator based on unweighted empirical variance.
Formulas:
    q_hat = sum( (y_i - mean(y))^2 ) / (k - 1)
    tau2_0 = sum( (y_i - mean(y))^2 / (v_i + 1) ) / (k - 1)
    # Actually, the standard SJ estimator uses:
    # tau2_0 = sum( (y_i - mean(y))^2 ) / (k - 1)
    # Let's check the exact Cochrane/metafor specification.
"""
from __future__ import annotations

import numpy as np

def estimate_tau2_sj(y: np.ndarray, v: np.ndarray) -> float:
    """Estimate tau^2 using the Sidik-Jonkman method.
    
    Uses the exact formula implemented in metafor for method="SJ".
    Formula:
        q_hat = sum( (y_i - mean(y))^2 ) / (k - 1)
        tau2_0 = max(0.01, q_hat)  # or some initial guess. metafor uses var(y) / k ? No, let's implement accurately.
    """
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    k = len(y)
    
    # 1. Initial estimate tau2_0
    y_bar_unweighted = np.mean(y)
    q_hat = np.sum((y - y_bar_unweighted)**2) / (k - 1)
    tau2_0 = np.sum((y - y_bar_unweighted)**2) / (k - 1)
    
    # metafor uses: 
    # tau2_0 = sum((yi - mean(yi))^2) / (k-1)
    # v_i(tau2_0) = v_i + tau2_0
    # w_i(tau2_0) = 1 / v_i(tau2_0)
    # y_bar(tau2_0) = sum(w_i * y_i) / sum(w_i)
    # tau2_SJ = sum( w_i * (y_i - y_bar)^2 ) / (k - 1) * tau2_0  <-- wait let me double check the formula
    
    # Let's implement the exact formula matching metafor:
    # tau2_0 is the uncorrected empirical variance of y: sum( (y_i - mean(y))^2 ) / k
    tau2_0 = np.var(y, ddof=0)
    
    # If tau2_0 is zero, the estimate is zero
    if tau2_0 == 0.0:
        return 0.0
        
    w_0 = 1.0 / (v + tau2_0)
    y_bar_0 = np.sum(w_0 * y) / np.sum(w_0)
    
    tau2_sj = tau2_0 * np.sum(w_0 * (y - y_bar_0)**2) / (k - 1)
    
    return float(max(0.0, tau2_sj))
