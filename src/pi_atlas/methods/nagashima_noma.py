"""Nagashima-Noma prediction interval.

Uses R `pimeta::pima()` which implements the exact Higgins-Thompson-Spiegelhalter
intervals as well as Nagashima et al. (2019) exact prediction intervals.
Protocol asks for "Nagashima-Noma (R pimeta via subprocess)".
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Sequence


R_SCRIPT_NAGASHIMA = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(pimeta))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
se <- sqrt(v)
alpha <- payload$alpha

# method="boot" gives Nagashima-Noma-Furukawa
res <- pima(y, se, method = "boot", alpha = alpha)

suppressPackageStartupMessages(library(metafor))
res_m <- rma(yi = y, vi = v, method = "REML")

out <- list(
  mu_hat = as.numeric(res$muhat),
  mu_ci_lower = as.numeric(res$lci),
  mu_ci_upper = as.numeric(res$uci),
  tau2 = as.numeric(res$tau2h),
  pi_lower = as.numeric(res$lpi),
  pi_upper = as.numeric(res$upi),
  k = as.integer(res$K),
  Q = as.numeric(res_m$QE) # pima doesn't return Q directly
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def fit_nagashima_noma(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    """Fit Nagashima-Noma prediction interval via R pimeta."""
    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        script_path = dpath / "script.R"
        input_path = dpath / "input.json"
        output_path = dpath / "output.json"

        script_path.write_text(R_SCRIPT_NAGASHIMA, encoding="utf-8")
        input_path.write_text(
            json.dumps({"y": list(map(float, y)), "v": list(map(float, v)), "alpha": alpha})
        )

        rscript_exe = r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe"

        proc = subprocess.run(
            [rscript_exe, "--vanilla", str(script_path), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=120, # NN can be slightly slower due to integration
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Rscript failed (code {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        out = json.loads(output_path.read_text())

    for k_ in list(out):
        if isinstance(out[k_], list) and len(out[k_]) == 1:
            out[k_] = out[k_][0]

    return out
