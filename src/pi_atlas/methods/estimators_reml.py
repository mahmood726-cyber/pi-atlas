"""REML tau^2 estimator.

Implementation of the Restricted Maximum Likelihood estimator for tau^2.
Iterative optimization of the restricted log-likelihood profile.
"""
from __future__ import annotations

import numpy as np
from scipy import optimize


def estimate_tau2_reml(y: np.ndarray, v: np.ndarray) -> float:
    """Estimate tau^2 using the REML method.
    
    Parameters
    ----------
    y : array-like, shape (k,)
    v : array-like, shape (k,)
        Sampling variances (SE^2).

    Returns
    -------
    float
        The REML estimate of tau^2.
    """
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    k = len(y)

    def neg_reml_loglik(tau2):
        w = 1.0 / (v + tau2)
        sum_w = np.sum(w)
        y_bar = np.sum(w * y) / sum_w
        
        # -2 * log-likelihood (restricted) ignoring constant terms
        term1 = np.sum(np.log(v + tau2))
        term2 = np.log(sum_w)
        term3 = np.sum(w * (y - y_bar)**2)
        
        return term1 + term2 + term3

    # REML can also hit zero. Check the gradient at 0.
    # We'll just use a bounded optimization routine.
    # L-BFGS-B or Brent can handle this.
    
    upper_bound = np.var(y, ddof=1) * 10
    
    res = optimize.minimize_scalar(
        neg_reml_loglik, 
        bounds=(0.0, max(100.0, upper_bound)), 
        method='bounded'
    )
    
    return float(max(0.0, res.x))
