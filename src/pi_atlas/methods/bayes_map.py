"""Method 8: Bayesian + MAP prior.

Uses `bayesmeta` but overrides the default Half-Normal(0, 0.5) prior on tau 
with a standard empirical prior based on the corpus or domain.
The protocol explicitly mentions: "Bayesian + MAP prior (Leveraging MAPriors)".
We can implement this by passing a customized prior to `bayesmeta(..., tau.prior=...)`.

For the sake of this framework, we'll use a weakly informative prior or a specific MAP 
prior formulation. The MAP (Maximum A Posteriori) prior approach typically involves
putting a strongly peaked prior derived from external data. 
If no specific MAP prior distribution is provided yet, we'll use an Inverse-Gamma or Log-Normal.
Wait, the protocol specifically says "Leveraging MAPriors". MAPriors (Meta-Analysis Priors) 
is an R package or framework, but often refers to Turner et al. priors or specific predictive priors.

Let's use the Turner prior for tau (which is a log-normal prior based on the outcome type).
Since we don't know the exact outcome type generically, we'll use a generic empirical prior 
from Turner et al. for 'any' setting.
`bayesmeta` supports Turner priors directly via `turner.prior("signs / symptoms")` etc.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Sequence


R_SCRIPT_MAP_PRIOR = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(bayesmeta))
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha
se <- sqrt(v)

# We use the generic Turner prior for heterogeneity (log-normal)
# This acts as an empirical 'MAP' (Maximum A Posteriori derived) prior.
tp <- TurnerEtAlPrior("signs / symptoms reflecting continuation / end of condition", "pharmacological", "placebo / control")

res <- bayesmeta(y = y, sigma = se, tau.prior = tp$dprior)

mu_hat <- as.numeric(res$summary["median", "mu"])
ci_lower <- as.numeric(res$summary["95% lower", "mu"])
ci_upper <- as.numeric(res$summary["95% upper", "mu"])
tau2 <- as.numeric(res$summary["median", "tau"])^2
pi_lower <- as.numeric(res$summary["95% lower", "theta"])
pi_upper <- as.numeric(res$summary["95% upper", "theta"])

res_m <- rma(yi = y, vi = v, method = "REML")

out <- list(
  mu_hat = mu_hat,
  mu_ci_lower = ci_lower,
  mu_ci_upper = ci_upper,
  tau2 = tau2,
  pi_lower = pi_lower,
  pi_upper = pi_upper,
  k = as.integer(length(y)),
  Q = as.numeric(res_m$QE)
)

jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def fit_bayes_map(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    """Fit Bayesian PI with an empirical MAP-style prior via bayesmeta."""
    if alpha != 0.05:
        raise NotImplementedError("bayesmeta wrapper currently only supports alpha=0.05 via the default summary table")

    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        script_path = dpath / "script.R"
        input_path = dpath / "input.json"
        output_path = dpath / "output.json"

        script_path.write_text(R_SCRIPT_MAP_PRIOR, encoding="utf-8")
        input_path.write_text(
            json.dumps({"y": list(map(float, y)), "v": list(map(float, v)), "alpha": alpha})
        )

        rscript_exe = r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe"

        proc = subprocess.run(
            [rscript_exe, "--vanilla", str(script_path), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Rscript failed (code {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        out = json.loads(output_path.read_text())

    for k_ in list(out):
        if isinstance(out[k_], list) and len(out[k_]) == 1:
            out[k_] = out[k_][0]

    return out
