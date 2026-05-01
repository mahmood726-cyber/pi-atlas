"""Generate the canonical 5-cell baseline fixture Parquet + SHA-256."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from pi_atlas.methods.hts_dl import fit_hts_dl
from pi_atlas.validation.r_bridge import metafor_hts_dl


REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT = REPO_ROOT / "baseline-fixture" / "input.json"
EXPECTED = REPO_ROOT / "baseline-fixture" / "expected.parquet"
HASH_FILE = REPO_ROOT / "preregistration" / "baseline-fixture-hash.txt"


def main() -> None:
    payload = json.loads(INPUT.read_text())
    rows = []
    for cell in payload["cells"]:
        y = np.array(cell["y"], dtype=np.float64)
        v = np.array(cell["v"], dtype=np.float64)
        py = fit_hts_dl(y, v)
        r = metafor_hts_dl(y, v)
        # Sanity: Python and metafor must agree to 1e-6
        for key in ("mu_hat", "tau2", "pi_lower", "pi_upper"):
            assert abs(py[key] - r[key]) < 1e-6, f"{cell['cell_id']}: {key} diverges py={py[key]} r={r[key]}"
        rows.append({"cell_id": cell["cell_id"], **py})
    df = pd.DataFrame(rows)
    df.to_parquet(EXPECTED, index=False)
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(EXPECTED.read_bytes()).hexdigest()
    HASH_FILE.write_text(sha + "\n")
    print(f"baseline fixture written: {EXPECTED}")
    print(f"SHA-256: {sha}")


if __name__ == "__main__":
    main()
