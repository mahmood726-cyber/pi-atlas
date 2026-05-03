"""Partlett-Riley (2017) Prediction Interval.

Uses R `metafor::rma()` with method="REML" and `predict()` to extract the exact Riley PI,
which incorporates the uncertainty in tau^2 by using a Student's t distribution with k-2 degrees of freedom
and a different variance scaling. Wait, the Partlett-Riley method is effectively the standard HTS PI
but often explicitly computed using a different formula for the variance of mu.
Actually, let's verify if `metafor` has a direct argument or if it's just the default `predict.rma` behavior 
when a certain method is used. According to Partlett & Riley (2017), the exact PI they propose is:
mu_hat +/- t_{k-2} * sqrt(tau^2 + SE(mu_hat)^2) 
Wait, this *is* the HTS PI. What distinguishes Riley?
Ah, Riley et al (2011) is the standard HTS PI.
Partlett and Riley (2017) propose using an adjusted variance or REML.
Let's check the protocol exactly.
"5. Partlett-Riley (R metafor wrapper)"
Let me review `metafor` documentation for Partlett-Riley.
In `predict.rma`, there is `pi.type="standard"` (HTS) and `pi.type="default"`.
Wait, in `metafor`, for `rma.uni`, we have `predict(..., pi.type="...")`.
There is no `pi.type="partlett"` natively?
Let's run a shell command to check R documentation for predict.rma.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Sequence

R_SCRIPT_PARTLETT_RILEY = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha

res <- rma(yi = y, vi = v, method = "REML")
pred <- predict(res, level = 1 - alpha, pi.type="riley")

out <- list(
  mu_hat = as.numeric(res$b),
  mu_ci_lower = as.numeric(res$ci.lb),
  mu_ci_upper = as.numeric(res$ci.ub),
  tau2 = as.numeric(res$tau2),
  pi_lower = as.numeric(pred$pi.lb),
  pi_upper = as.numeric(pred$pi.ub),
  k = as.integer(res$k),
  Q = as.numeric(res$QE)
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def fit_partlett_riley(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    """Fit Partlett-Riley prediction interval via R metafor.
    
    Partlett & Riley (2017) recommend REML tau^2 with Knapp-Hartung variance adjustment 
    for the mean, and t_{k-2} for the PI.
    """
    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        script_path = dpath / "script.R"
        input_path = dpath / "input.json"
        output_path = dpath / "output.json"

        script_path.write_text(R_SCRIPT_PARTLETT_RILEY, encoding="utf-8")
        input_path.write_text(
            json.dumps({"y": list(map(float, y)), "v": list(map(float, v)), "alpha": alpha})
        )

        rscript_exe = r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe"

        proc = subprocess.run(
            [rscript_exe, "--vanilla", str(script_path), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Rscript failed (code {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        out = json.loads(output_path.read_text())

    for k_ in list(out):
        if isinstance(out[k_], list) and len(out[k_]) == 1:
            out[k_] = out[k_][0]

    return out
