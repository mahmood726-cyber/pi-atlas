"""Non-parametric cluster bootstrap prediction interval.

Protocol method 9: "Non-parametric cluster bootstrap"
This method resamples the *studies* (clusters) with replacement, fits a meta-analysis model 
(e.g., standard FE or RE), and generates a new prediction from the distribution.
Wait, typically a non-parametric cluster bootstrap for a prediction interval in meta-analysis 
involves:
1. Sample k studies with replacement.
2. For each bootstrap sample, compute mu_hat and tau^2 (e.g. DL).
3. Sample a new 'study effect' theta_new ~ N(mu_hat_boot, tau2_boot).
4. The 2.5% and 97.5% quantiles of the resulting distribution of theta_new form the PI.
Or, purely non-parametric:
1. Sample k studies with replacement, compute mu_hat.
2. Draw one study from the *original* set (or bootstrap set) to represent the 'future' study.
Actually, Higgins et al. or standard literature defines the non-parametric bootstrap PI 
by drawing the future study's effect from the empirical distribution of the estimated study effects 
(shrunken or raw), or by using the parametric assumption at the bottom level.
Let's implement a standard semi-parametric cluster bootstrap for the PI:
For B iterations:
  a. Draw k studies with replacement.
  b. Estimate mu_hat^{(b)}, tau2^{(b)} using standard DL method.
  c. Draw theta_{new}^{(b)} ~ N(mu_hat^{(b)}, tau2^{(b)} + var_mu_hat).
Wait, if it's "non-parametric", the whole point is avoiding the Normal assumption for the random effects!
If we avoid the normal assumption, we resample a study effect directly.
Let's use the standard method:
For B = 2000 iterations:
  a. Sample k indices with replacement.
  b. Compute mu_hat^{(b)} using FE or RE weights from the bootstrap sample.
  c. The "prediction" is just mu_hat^{(b)} + e_new, where e_new is sampled from the empirical residuals.
Let's use a simpler robust approach:
Just use `pimeta` with method="boot" but wait, method="boot" in `pimeta` is a *parametric* bootstrap 
(Nagashima et al 2018).
Protocol says "Non-parametric cluster bootstrap". We will write this in Python.

Algorithm:
1. For b = 1 to B (e.g., B=2000):
2.   Sample k indices with replacement from {0, ..., k-1}.
3.   Calculate mu_hat_b using DL weights on the bootstrap sample.
4.   To form a prediction, we need to add the between-study heterogeneity. We can randomly draw one of the 
     original (or bootstrapped) y_i values, but recentered around mu_hat_b.
     theta_new_b = mu_hat_b + (y_i* - mu_hat)
     where y_i* is a randomly selected study from the sample, and mu_hat is the overall mean.
5. PI is the empirical alpha/2 and 1-alpha/2 quantiles of theta_new_b.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

from pi_atlas.methods.hts_dl import fit_hts_dl


def fit_np_bootstrap(y: np.ndarray, v: np.ndarray, *, alpha: float = 0.05, B: int = 2000) -> Dict[str, float]:
    """Fit Non-parametric cluster bootstrap prediction interval.
    
    1. Base fit to get overall mu_hat.
    2. B bootstrap iterations:
       - Resample studies (y, v) with replacement.
       - Fit DL on resample to get mu_hat_boot.
       - Pick a random study y_rand from the resample.
       - Theta_pred = mu_hat_boot + (y_rand - mu_hat_boot) = y_rand.
       Wait, if we just use y_rand, the PI is just the quantiles of y!
       To account for estimation error, we should do:
       Theta_pred = mu_hat_boot + (y_rand - mean(y_rand_sample))
    Let's refine:
    Theta_pred_b = y_rand_b
    Actually, the empirical distribution of y is wider than the distribution of true effects theta,
    because y includes sampling error (v_i).
    If we just take quantiles of y, we get a PI for the *observed* effect of a new study, 
    which is exactly what we want! 
    The protocol evaluates coverage on the *observed* left-out study `y_new`.
    So drawing from the empirical distribution of `y` (smoothed by the bootstrap of the mean) 
    is a valid non-parametric approach for predicting a new *observed* study.
    
    Let's do:
    Theta_pred_b = mu_hat_boot + (y_rand - mu_hat)
    where y_rand is drawn uniformly from the original y.
    """
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    k = len(y)
    if k < 3:
        raise ValueError("Bootstrap PI requires k >= 3")

    # Base fit for metadata and centering
    base_res = fit_hts_dl(y, v, alpha=alpha)
    base_mu = base_res["mu_hat"]

    rng = np.random.default_rng(seed=int(abs(base_mu * 1e6) + k) % 1000000) # pseudo-deterministic

    preds = np.zeros(B)
    mu_boots = np.zeros(B)

    for b in range(B):
        idx = rng.choice(k, size=k, replace=True)
        y_b = y[idx]
        v_b = v[idx]
        
        # Fit DL on bootstrap sample
        # (Could fail if k<3 unique studies but k>=3 total, DL handles it)
        try:
            res_b = fit_hts_dl(y_b, v_b)
            mu_b = res_b["mu_hat"]
        except Exception:
            mu_b = base_mu
            
        mu_boots[b] = mu_b
        
        # Draw a random residual from the original sample to represent empirical heterogeneity + sampling error
        y_rand = rng.choice(y)
        preds[b] = mu_b + (y_rand - base_mu)

    pi_lower = float(np.quantile(preds, alpha / 2.0))
    pi_upper = float(np.quantile(preds, 1.0 - alpha / 2.0))
    
    ci_lower = float(np.quantile(mu_boots, alpha / 2.0))
    ci_upper = float(np.quantile(mu_boots, 1.0 - alpha / 2.0))

    return {
        "mu_hat": base_res["mu_hat"],
        "mu_ci_lower": ci_lower,
        "mu_ci_upper": ci_upper,
        "tau2": base_res["tau2"],
        "pi_lower": pi_lower,
        "pi_upper": pi_upper,
        "k": k,
        "Q": base_res["Q"],
    }
