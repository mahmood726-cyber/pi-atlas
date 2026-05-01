import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pi_atlas.storage import ResultStore


@pytest.fixture
def tmp_store():
    with tempfile.TemporaryDirectory() as d:
        yield ResultStore(Path(d))


def test_flush_writes_parquet(tmp_store):
    df = pd.DataFrame({"cell_id": ["c1", "c2"], "coverage": [1, 0]})
    path = tmp_store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.0", dgp_family="normal"))
    assert path.exists()
    assert path.suffix == ".parquet"
    loaded = pd.read_parquet(path)
    assert len(loaded) == 2


def test_flush_atomic_rename(tmp_store):
    """No .tmp file should exist after a successful flush."""
    df = pd.DataFrame({"cell_id": ["c1"], "coverage": [1]})
    path = tmp_store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.0", dgp_family="normal"))
    tmp_file = path.with_suffix(".parquet.tmp")
    assert not tmp_file.exists()


def test_manifest_records_sha256(tmp_store):
    df = pd.DataFrame({"cell_id": ["c1"], "coverage": [1]})
    tmp_store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.0", dgp_family="normal"))
    manifest = tmp_store.read_manifest()
    assert len(manifest) == 1
    assert len(manifest.iloc[0]["sha256"]) == 64  # hex digest length


def test_verify_manifest_detects_corruption(tmp_store):
    df = pd.DataFrame({"cell_id": ["c1"], "coverage": [1]})
    path = tmp_store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.0", dgp_family="normal"))
    # Corrupt the file
    with open(path, "ab") as f:
        f.write(b"CORRUPTED")
    ok, bad_files = tmp_store.verify_manifest()
    assert not ok
    assert path.name in [p.name for p in bad_files]


def test_flush_creates_partition_dirs(tmp_store):
    df = pd.DataFrame({"cell_id": ["c1"], "coverage": [1]})
    path = tmp_store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.05", dgp_family="t3"))
    # Expect path like: <root>/phase=smoke/method=hts_dl/tau2_level=0.05/dgp_family=t3/<hash>.parquet
    assert "phase=smoke" in str(path)
    assert "method=hts_dl" in str(path)
    assert "tau2_level=0.05" in str(path)
    assert "dgp_family=t3" in str(path)
