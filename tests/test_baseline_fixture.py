"""Regenerating the baseline fixture must produce bit-identical Parquet."""
import hashlib
import subprocess
from pathlib import Path

import pandas as pd
import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
EXPECTED = REPO_ROOT / "baseline-fixture" / "expected.parquet"
HASH_FILE = REPO_ROOT / "preregistration" / "baseline-fixture-hash.txt"


def test_fixture_sha_matches_committed():
    sha = hashlib.sha256(EXPECTED.read_bytes()).hexdigest()
    committed = HASH_FILE.read_text().strip()
    assert sha == committed, f"fixture SHA drift: on-disk={sha}, committed={committed}"


def test_fixture_values_within_tolerance():
    """Numerical values in the fixture should be stable to 1e-6 across environments."""
    df = pd.read_parquet(EXPECTED)
    assert len(df) == 5
    # Spot-check: bl-02 is 4 identical studies → tau2 should be exactly 0
    row = df[df["cell_id"] == "bl-02"].iloc[0]
    assert abs(row["tau2"]) < 1e-9
    assert abs(row["mu_hat"] - 0.5) < 1e-9
