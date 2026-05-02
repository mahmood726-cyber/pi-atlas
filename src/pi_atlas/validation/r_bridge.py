"""Subprocess bridge to Rscript for metafor cross-validation.

Design choice: subprocess (not rpy2) for reliability under systemd sandboxing
and to keep R optional in production workers (methods are Python-native; R is
only needed at preregistration/validation time).
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Sequence

R_SCRIPT = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha

res <- rma(yi = y, vi = v, method = "DL")

# HTS PI: mu +/- t_{k-2} * sqrt(tau2 + se_mu^2)
k <- res$k
t_crit <- qt(1 - alpha/2, df = k - 2)
pi_half <- t_crit * sqrt(res$tau2 + res$vb)
pi_lower <- as.numeric(res$b - pi_half)
pi_upper <- as.numeric(res$b + pi_half)

out <- list(
  mu_hat = as.numeric(res$b),
  mu_ci_lower = as.numeric(res$ci.lb),
  mu_ci_upper = as.numeric(res$ci.ub),
  tau2 = as.numeric(res$tau2),
  pi_lower = pi_lower,
  pi_upper = pi_upper,
  k = as.integer(res$k),
  Q = as.numeric(res$QE)
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""


R_SCRIPT_PM = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha

res <- rma(yi = y, vi = v, method = "PM")

k <- res$k
t_crit <- qt(1 - alpha/2, df = k - 2)
pi_half <- t_crit * sqrt(res$tau2 + res$vb)
pi_lower <- as.numeric(res$b - pi_half)
pi_upper <- as.numeric(res$b + pi_half)

out <- list(
  mu_hat = as.numeric(res$b),
  mu_ci_lower = as.numeric(res$ci.lb),
  mu_ci_upper = as.numeric(res$ci.ub),
  tau2 = as.numeric(res$tau2),
  pi_lower = pi_lower,
  pi_upper = pi_upper,
  k = as.integer(res$k),
  Q = as.numeric(res$QE)
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def _metafor_generic(y: Sequence[float], v: Sequence[float], alpha: float, r_script: str) -> Dict:
    import tempfile
    import json
    import subprocess
    import numpy as np

    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        script_path = dpath / "script.R"
        input_path = dpath / "input.json"
        output_path = dpath / "output.json"

        script_path.write_text(r_script, encoding="utf-8")
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

R_SCRIPT_REML = r"""
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

k <- res$k
t_crit <- qt(1 - alpha/2, df = k - 2)
pi_half <- t_crit * sqrt(res$tau2 + res$vb)
pi_lower <- as.numeric(res$b - pi_half)
pi_upper <- as.numeric(res$b + pi_half)

out <- list(
  mu_hat = as.numeric(res$b),
  mu_ci_lower = as.numeric(res$ci.lb),
  mu_ci_upper = as.numeric(res$ci.ub),
  tau2 = as.numeric(res$tau2),
  pi_lower = pi_lower,
  pi_upper = pi_upper,
  k = as.integer(res$k),
  Q = as.numeric(res$QE)
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def metafor_hts_dl(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    return _metafor_generic(y, v, alpha, R_SCRIPT)

R_SCRIPT_SJ = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha

res <- rma(yi = y, vi = v, method = "SJ")

k <- res$k
t_crit <- qt(1 - alpha/2, df = k - 2)
pi_half <- t_crit * sqrt(res$tau2 + res$vb)
pi_lower <- as.numeric(res$b - pi_half)
pi_upper <- as.numeric(res$b + pi_half)

out <- list(
  mu_hat = as.numeric(res$b),
  mu_ci_lower = as.numeric(res$ci.lb),
  mu_ci_upper = as.numeric(res$ci.ub),
  tau2 = as.numeric(res$tau2),
  pi_lower = pi_lower,
  pi_upper = pi_upper,
  k = as.integer(res$k),
  Q = as.numeric(res$QE)
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def metafor_hts_sj(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    return _metafor_generic(y, v, alpha, R_SCRIPT_SJ)

R_SCRIPT_HKSJ = r"""
.libPaths(c("C:/Users/mahmo/Documents/R/win-library/4.6", .libPaths()))
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha

res <- rma(yi = y, vi = v, method = "DL", test = "knha")

k <- res$k
t_crit <- qt(1 - alpha/2, df = k - 2)
pi_half <- t_crit * sqrt(res$tau2 + res$vb)
pi_lower <- as.numeric(res$b - pi_half)
pi_upper <- as.numeric(res$b + pi_half)

out <- list(
  mu_hat = as.numeric(res$b),
  mu_ci_lower = as.numeric(res$ci.lb),
  mu_ci_upper = as.numeric(res$ci.ub),
  tau2 = as.numeric(res$tau2),
  pi_lower = pi_lower,
  pi_upper = pi_upper,
  k = as.integer(res$k),
  Q = as.numeric(res$QE)
)
jsonlite::write_json(out, output_path, auto_unbox = TRUE, digits = 15)
"""

def metafor_hksj(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    return _metafor_generic(y, v, alpha, R_SCRIPT_HKSJ)
