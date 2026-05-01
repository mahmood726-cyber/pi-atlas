"""Gate check: verify all P0 preflights before preregistration."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from pi_atlas.methods.hts_dl import fit_hts_dl
from pi_atlas.validation.r_bridge import metafor_hts_dl


def check_python_version():
    print(f"[check] python version: {sys.version}")
    return True


def check_r_version():
    import subprocess
    rscript_exe = r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe"
    res = subprocess.run([rscript_exe, "--version"], capture_output=True, text=True)
    print(f"[check] R version: {res.stdout.strip()}")
    return res.returncode == 0


def check_baseline_fixture():
    root = Path(__file__).resolve().parent.parent
    expected = root / "baseline-fixture" / "expected.parquet"
    hash_file = root / "preregistration" / "baseline-fixture-hash.txt"
    if not expected.exists():
        print("[error] baseline fixture missing")
        return False
    import hashlib
    sha = hashlib.sha256(expected.read_bytes()).hexdigest()
    committed = hash_file.read_text().strip()
    if sha != committed:
        print(f"[error] baseline fixture hash mismatch: {sha} vs {committed}")
        return False
    print(f"[check] baseline fixture ok (SHA {sha[:8]})")
    return True


def check_r_bridge():
    import numpy as np
    y = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    v = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
    py = fit_hts_dl(y, v)
    r = metafor_hts_dl(y, v)
    for key in ("mu_hat", "tau2", "pi_lower", "pi_upper"):
        if abs(py[key] - r[key]) > 1e-6:
            print(f"[error] R bridge divergence on {key}: py={py[key]}, r={r[key]}")
            return False
    print("[check] R bridge cross-validation ok")
    return True


def main():
    checks = [
        ("Python version", check_python_version),
        ("R version", check_r_version),
        ("Baseline fixture", check_baseline_fixture),
        ("R bridge validation", check_r_bridge),
    ]
    all_ok = True
    for name, fn in checks:
        try:
            if not fn():
                print(f"FAILED: {name}")
                all_ok = False
            else:
                print(f"PASSED: {name}")
        except Exception as e:
            print(f"ERROR in {name}: {e}")
            all_ok = False

    if not all_ok:
        print("\nGATE CHECK FAILED")
        sys.exit(1)
    print("\nGATE CHECK PASSED")


if __name__ == "__main__":
    main()
