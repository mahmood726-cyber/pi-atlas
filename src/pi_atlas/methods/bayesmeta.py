"""Bayesian posterior predictive intervals via R `bayesmeta`.

Protocol specifies Method 7: Bayesian posterior predictive (R bayesmeta wrapper)
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Sequence


R_SCRIPT_BAYESMETA = r"""
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

# Standard non-informative priors are used by default in bayesmeta (uniform on mu, half-normal on tau)
# We stick to the package defaults for a standard Bayesian random effects MA unless specified otherwise
res <- bayesmeta(y = y, sigma = se)

# Extract prediction interval
# bayesmeta returns a summary matrix, we can extract the prediction interval 
# corresponding to alpha (which gives a 1-alpha interval).
# Specifically, we want the (alpha/2) and (1-alpha/2) quantiles for the 'theta' (effect) and the 'predictive' distribution.

# For standard 95% (alpha=0.05), we can just use the summary table.
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

def fit_bayesmeta(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    """Fit Bayesian posterior predictive interval via R bayesmeta.
    
    Currently hardcoded to 95% intervals (alpha=0.05) as we rely on the default summary.
    """
    if alpha != 0.05:
        raise NotImplementedError("bayesmeta wrapper currently only supports alpha=0.05 via the default summary table")

    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        script_path = dpath / "script.R"
        input_path = dpath / "input.json"
        output_path = dpath / "output.json"

        script_path.write_text(R_SCRIPT_BAYESMETA, encoding="utf-8")
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
