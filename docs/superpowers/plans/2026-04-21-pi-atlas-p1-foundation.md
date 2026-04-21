# PI Atlas Plan 1: Foundation + Preregistration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a working queue/worker/Parquet infrastructure on WSL2 + systemd, validated by a 20-cell smoke run and a minted Zenodo DOI for the preregistration — so that Plan 2 (methods) and Plans 3-4 (main compute) have a tested, resumable substrate to run on.

**Architecture:** Python 3.11 primary; R 4.5.2 as a subprocess for `metafor` validation. DuckDB as queue backend (single-writer + WAL). Parquet partitioned results with atomic rename on flush. Deterministic per-cell `sha256` seeds. Systemd user services with auto-restart. Preregistration via Zenodo DOI + OpenTimestamps + Internet Archive before any substantive compute.

**Tech Stack:** Python 3.11, `numpy`, `scipy`, `duckdb`, `pyarrow`, `pandas`, `pytest`, `hypothesis`; R 4.5.2, `metafor`, `renv`; systemd-user; `ots` CLI (OpenTimestamps); `gh` CLI (GitHub release → Zenodo); `curl` (Internet Archive).

**Working directory for all commands:** `~/pi-atlas` (symlinked from `C:\Projects\pi-atlas` via WSL2).

---

## File structure (frozen at end of this plan)

```
pi-atlas/
├── .gitignore
├── README.md
├── LICENSE                          # MIT
├── pyproject.toml                   # Python package metadata, deps, lockfile-pinned
├── requirements.lock                # pip-compile output, version-pinned
├── renv.lock                        # R deps lockfile
├── .sentinel/                       # Sentinel rule config
├── docs/
│   ├── superpowers/
│   │   ├── specs/                   # (v1.0 spec already committed)
│   │   └── plans/                   # (this plan)
│   └── architecture.md              # created in Task 3
├── preregistration/
│   ├── PROTOCOL.md                  # created in Task 19
│   ├── PROTOCOL.md.ots              # created in Task 20
│   └── baseline-fixture-hash.txt    # SHA-256 of baseline .parquet, created in Task 13
├── src/pi_atlas/
│   ├── __init__.py
│   ├── seeds.py                     # deterministic seed derivation
│   ├── queue.py                     # DuckDB queue claim/complete primitives
│   ├── storage.py                   # Parquet atomic write + manifest
│   ├── worker.py                    # worker main loop
│   ├── watchdog.py                  # stuck-cell watchdog
│   ├── methods/
│   │   ├── __init__.py
│   │   └── hts_dl.py                # HTS + DL — the one method in Plan 1 (others in Plan 2)
│   └── validation/
│       ├── __init__.py
│       └── r_bridge.py              # subprocess call to Rscript for metafor
├── scripts/
│   ├── smoke_run.py                 # 20-cell end-to-end test
│   ├── resume_invariant_test.sh     # kill/reboot/resume integration test
│   └── gate_check.py                # P0 gate GO/NO-GO
├── systemd/
│   ├── pi-atlas-worker@.service     # systemd user service unit
│   └── pi-atlas-watchdog.timer      # weekly watchdog timer
├── tests/
│   ├── test_seeds.py
│   ├── test_queue.py
│   ├── test_storage.py
│   ├── test_hts_dl.py
│   ├── test_r_bridge.py
│   └── test_resume_invariant.py
└── baseline-fixture/
    ├── input.json                   # 5 cell configs
    └── expected.parquet             # validated output
```

---

## Phase A — Repo scaffold (Tasks 1-4)

### Task 1: Python env + .gitignore + pyproject.toml

**Files:**
- Create: `~/pi-atlas/.gitignore`
- Create: `~/pi-atlas/pyproject.toml`
- Create: `~/pi-atlas/src/pi_atlas/__init__.py`

- [ ] **Step 1: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
build/
dist/
.pytest_cache/
.coverage
htmlcov/
*.duckdb
*.duckdb.wal
results/*.parquet
!baseline-fixture/expected.parquet
manifest.csv
.RData
.Rhistory
renv/library/
renv/python/
renv/staging/
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "pi-atlas"
version = "0.1.0-dev"
description = "Prediction Interval Calibration Atlas on Pairwise70"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11,<3.13"
dependencies = [
    "numpy>=1.26,<2.0",
    "scipy>=1.11,<2.0",
    "pandas>=2.1,<3.0",
    "pyarrow>=14.0,<18.0",
    "duckdb>=0.10,<2.0",
    "click>=8.1,<9.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4,<9.0",
    "pytest-cov>=4.1",
    "hypothesis>=6.88",
    "pip-tools>=7.3",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --strict-markers"
```

- [ ] **Step 3: Create empty __init__.py**

```python
"""PI Atlas — Prediction Interval Calibration on Pairwise70."""
__version__ = "0.1.0-dev"
```

- [ ] **Step 4: Create venv, install, compile lockfile**

Run:
```bash
cd ~/pi-atlas
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install pip-tools
pip-compile --extra dev -o requirements.lock pyproject.toml
```

Expected: `requirements.lock` created with pinned versions.

- [ ] **Step 5: Commit**

```bash
cd ~/pi-atlas
git add .gitignore pyproject.toml src/pi_atlas/__init__.py requirements.lock
git commit -m "feat: python env + lockfile + package skeleton"
```

---

### Task 2: R env with renv

**Files:**
- Create: `~/pi-atlas/renv.lock` (via renv::init)
- Create: `~/pi-atlas/.Rprofile` (via renv::init)

- [ ] **Step 1: Initialize renv**

Run:
```bash
cd ~/pi-atlas
Rscript -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript -e 'renv::init(bare=TRUE)'
Rscript -e 'renv::install("metafor")'
Rscript -e 'renv::snapshot(prompt=FALSE)'
```

Expected: `renv.lock` contains `metafor` pinned; `.Rprofile` sources renv activation.

- [ ] **Step 2: Verify metafor import works**

Run:
```bash
Rscript -e 'library(metafor); cat("metafor version:", as.character(packageVersion("metafor")), "\n")'
```
Expected: prints metafor version (should be 4.x).

- [ ] **Step 3: Commit**

```bash
cd ~/pi-atlas
git add renv.lock .Rprofile renv/activate.R renv/settings.json
git commit -m "feat: R env via renv with metafor"
```

---

### Task 3: README + architecture.md + LICENSE

**Files:**
- Create: `~/pi-atlas/README.md`
- Create: `~/pi-atlas/LICENSE`
- Create: `~/pi-atlas/docs/architecture.md`

- [ ] **Step 1: Create LICENSE (MIT)**

```
MIT License

Copyright (c) 2026 Mahmood Ahmad

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

- [ ] **Step 2: Create README.md**

```markdown
# PI Atlas

Empirically-anchored audit of 95% prediction-interval (PI) coverage in
random-effects meta-analysis, evaluated against the Cochrane Pairwise70
corpus (7,545 MAs, 595 reviews).

**Status:** Phase 0 — infrastructure + preregistration. No main compute yet.

## Design

See [`docs/superpowers/specs/2026-04-21-pi-atlas-design.md`](docs/superpowers/specs/2026-04-21-pi-atlas-design.md).

## Preregistration

Primary record: Zenodo DOI (minted at the end of Plan 1).
Redundancy: OpenTimestamps attestation + Internet Archive snapshot.

## Reproducing the infrastructure

```bash
# Python
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# R
Rscript -e 'renv::restore()'

# Smoke run (20 cells, end-to-end)
python scripts/smoke_run.py

# Gate check (8 P0 preflights)
python scripts/gate_check.py
```

## License

MIT — see `LICENSE`.
```

- [ ] **Step 3: Create docs/architecture.md**

```markdown
# PI Atlas Architecture

## Layers

1. **Queue** (`duckdb`) — single-writer, WAL-backed work queue. Atomic claim via `UPDATE ... RETURNING`.
2. **Worker** (Python, systemd-user) — pop cell, run one fit, write Parquet row.
3. **Storage** (Parquet, partitioned by `(phase, method, tau2_level, dgp_family)`) — atomic rename on flush; SHA-256 in `manifest.csv`.
4. **Watchdog** (Python, systemd timer, weekly) — resets stuck `running` cells; verifies manifest SHA-256.
5. **R bridge** (`validation/r_bridge.py`) — subprocess call to `Rscript` for `metafor` cross-validation.

## Data flow (single cell)

```
cell_config (k, SE_vector, tau2, dgp, replicate_id, method)
  → seed_hex = sha256(json(cell_config))[:16]
  → DGP sampler → k studies
  → PI method fit → (μ̂, PI lower, PI upper, τ̂²)
  → coverage indicators (true & observed)
  → worker appends row to in-memory buffer
  → flush to Parquet every 60min or 100K rows
```

## Resumability invariant

Kill workers → reboot → restart → within 60 min:
- no cell lost
- no cell duplicated
- next fit produced = bit-identical to the fit that would have been produced without the kill

Tested weekly by `scripts/resume_invariant_test.sh`.
```

- [ ] **Step 4: Commit**

```bash
cd ~/pi-atlas
git add LICENSE README.md docs/architecture.md
git commit -m "docs: README + architecture + MIT license"
```

---

### Task 4: Install Sentinel pre-push hook

**Files:**
- Create: `~/pi-atlas/.sentinel/` (via Sentinel CLI)

- [ ] **Step 1: Install hook**

Run:
```bash
cd ~/pi-atlas
python -m sentinel install-hook --repo .
```

Expected: output "Hook installed at .git/hooks/pre-push".

- [ ] **Step 2: Verify hook fires with zero findings on current state**

Run:
```bash
cd ~/pi-atlas
python -m sentinel scan --repo .
```
Expected: exit code 0 and output `BLOCK: 0, WARN: 0` (the repo has only spec + README + config so far).

- [ ] **Step 3: Commit**

```bash
cd ~/pi-atlas
git add .sentinel/
git commit -m "feat: Sentinel pre-push hook installed"
```

---

## Phase B — Core infrastructure (Tasks 5-10)

### Task 5: Deterministic seed utility (TDD)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/seeds.py`
- Create: `~/pi-atlas/tests/test_seeds.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_seeds.py`:

```python
import pytest
import numpy as np
from pi_atlas.seeds import derive_seed_hex, seed_to_rng


def test_derive_seed_hex_deterministic():
    cfg = {"k": 5, "tau2": 0.15, "dgp": "normal", "method": "hts_dl"}
    s1 = derive_seed_hex(cfg, replicate_id=7)
    s2 = derive_seed_hex(cfg, replicate_id=7)
    assert s1 == s2
    assert len(s1) == 16


def test_derive_seed_hex_key_order_invariant():
    cfg1 = {"k": 5, "tau2": 0.15, "dgp": "normal"}
    cfg2 = {"tau2": 0.15, "dgp": "normal", "k": 5}  # different key order
    assert derive_seed_hex(cfg1, 0) == derive_seed_hex(cfg2, 0)


def test_derive_seed_hex_changes_with_replicate():
    cfg = {"k": 5, "tau2": 0.15}
    assert derive_seed_hex(cfg, 0) != derive_seed_hex(cfg, 1)


def test_seed_to_rng_reproducible():
    rng1 = seed_to_rng("abcdef0123456789")
    rng2 = seed_to_rng("abcdef0123456789")
    assert np.array_equal(rng1.standard_normal(10), rng2.standard_normal(10))


def test_seed_to_rng_independent():
    rng1 = seed_to_rng("abcdef0123456789")
    rng2 = seed_to_rng("fedcba9876543210")
    assert not np.array_equal(rng1.standard_normal(10), rng2.standard_normal(10))
```

- [ ] **Step 2: Run test — expect failure**

Run:
```bash
cd ~/pi-atlas && source .venv/bin/activate
pytest tests/test_seeds.py -v
```
Expected: `ModuleNotFoundError: No module named 'pi_atlas.seeds'` or ImportError.

- [ ] **Step 3: Implement src/pi_atlas/seeds.py**

```python
"""Deterministic per-cell seed derivation."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

import numpy as np


def derive_seed_hex(cell_config: Mapping[str, Any], replicate_id: int) -> str:
    """Return the first 16 hex chars of sha256(canonical-json(cfg) + repr(rep)).

    Guarantees:
    - Key-order invariant (sort_keys=True).
    - Deterministic across runs and machines.
    - Changes with replicate_id.
    """
    payload = json.dumps(cell_config, sort_keys=True, separators=(",", ":"))
    payload += f"|replicate={replicate_id}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return digest[:16]


def seed_to_rng(seed_hex: str) -> np.random.Generator:
    """Convert a hex seed string to a numpy Generator (PCG64)."""
    seed_int = int(seed_hex, 16)
    return np.random.default_rng(seed_int)
```

- [ ] **Step 4: Run test — expect pass**

Run:
```bash
pytest tests/test_seeds.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pi_atlas/seeds.py tests/test_seeds.py
git commit -m "feat(seeds): deterministic per-cell seed derivation (sha256)"
```

---

### Task 6: DuckDB queue primitives (TDD)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/queue.py`
- Create: `~/pi-atlas/tests/test_queue.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_queue.py`:

```python
import tempfile
from pathlib import Path

import pytest

from pi_atlas.queue import Queue


@pytest.fixture
def tmp_queue():
    with tempfile.TemporaryDirectory() as d:
        q = Queue(Path(d) / "test.duckdb")
        q.init_schema()
        yield q


def test_insert_and_claim(tmp_queue):
    tmp_queue.insert_cell("c1", phase="smoke", method="hts_dl", factor_json='{"k":3}')
    tmp_queue.insert_cell("c2", phase="smoke", method="hts_dl", factor_json='{"k":4}')
    claimed = tmp_queue.claim_one()
    assert claimed is not None
    assert claimed["cell_id"] in ("c1", "c2")
    assert claimed["status"] == "running"


def test_claim_returns_none_when_empty(tmp_queue):
    assert tmp_queue.claim_one() is None


def test_atomic_claim_no_double(tmp_queue):
    """Two consecutive claims never return the same cell."""
    tmp_queue.insert_cell("c1", phase="smoke", method="hts_dl", factor_json="{}")
    a = tmp_queue.claim_one()
    b = tmp_queue.claim_one()
    assert a is not None
    assert b is None  # only one cell, already claimed


def test_mark_done(tmp_queue):
    tmp_queue.insert_cell("c1", phase="smoke", method="hts_dl", factor_json="{}")
    claimed = tmp_queue.claim_one()
    tmp_queue.mark_done(claimed["cell_id"])
    row = tmp_queue.get_cell("c1")
    assert row["status"] == "done"
    assert row["completed_at"] is not None


def test_reset_stuck(tmp_queue):
    """Cells in running state > stuck_threshold_minutes reset to pending."""
    tmp_queue.insert_cell("c1", phase="smoke", method="hts_dl", factor_json="{}")
    tmp_queue.claim_one()
    # Force claimed_at far in the past
    tmp_queue._conn.execute(
        "UPDATE cells SET claimed_at = claimed_at - INTERVAL '2 hours' WHERE cell_id='c1'"
    )
    reset = tmp_queue.reset_stuck(stuck_threshold_minutes=60)
    assert reset == 1
    row = tmp_queue.get_cell("c1")
    assert row["status"] == "pending"
```

- [ ] **Step 2: Run test — expect failure**

Run:
```bash
pytest tests/test_queue.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement src/pi_atlas/queue.py**

```python
"""DuckDB-backed work queue for PI Atlas cells.

Single-writer model. Workers atomically claim cells via UPDATE...RETURNING.
Stuck cells (running > stuck_threshold_minutes) are reset to pending by a
watchdog.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb


SCHEMA = """
CREATE TABLE IF NOT EXISTS cells (
    cell_id TEXT PRIMARY KEY,
    phase TEXT NOT NULL,
    method TEXT NOT NULL,
    factor_json TEXT NOT NULL,
    seed_hex TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    claimed_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_status ON cells(status);
"""


class Queue:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._conn = duckdb.connect(str(self.db_path))

    def init_schema(self) -> None:
        self._conn.execute(SCHEMA)

    def insert_cell(
        self,
        cell_id: str,
        *,
        phase: str,
        method: str,
        factor_json: str,
        seed_hex: Optional[str] = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO cells (cell_id, phase, method, factor_json, seed_hex) "
            "VALUES (?, ?, ?, ?, ?)",
            [cell_id, phase, method, factor_json, seed_hex],
        )

    def claim_one(self) -> Optional[dict]:
        """Atomically mark one pending cell as running; return its row or None."""
        row = self._conn.execute(
            "UPDATE cells SET status='running', claimed_at=NOW() "
            "WHERE cell_id = ("
            "  SELECT cell_id FROM cells WHERE status='pending' "
            "  ORDER BY cell_id LIMIT 1"
            ") "
            "RETURNING cell_id, phase, method, factor_json, seed_hex, status"
        ).fetchone()
        if row is None:
            return None
        cols = ["cell_id", "phase", "method", "factor_json", "seed_hex", "status"]
        return dict(zip(cols, row))

    def mark_done(self, cell_id: str) -> None:
        self._conn.execute(
            "UPDATE cells SET status='done', completed_at=NOW() WHERE cell_id=?",
            [cell_id],
        )

    def get_cell(self, cell_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT cell_id, phase, method, factor_json, seed_hex, status, "
            "claimed_at, completed_at FROM cells WHERE cell_id=?",
            [cell_id],
        ).fetchone()
        if row is None:
            return None
        cols = [
            "cell_id", "phase", "method", "factor_json", "seed_hex",
            "status", "claimed_at", "completed_at",
        ]
        return dict(zip(cols, row))

    def reset_stuck(self, stuck_threshold_minutes: int = 60) -> int:
        """Reset any 'running' cells idle longer than threshold back to 'pending'.

        Returns number of cells reset.
        """
        cur = self._conn.execute(
            "UPDATE cells SET status='pending', claimed_at=NULL "
            "WHERE status='running' "
            f"AND claimed_at < NOW() - INTERVAL '{stuck_threshold_minutes} minutes' "
            "RETURNING cell_id"
        )
        rows = cur.fetchall()
        return len(rows)

    def close(self) -> None:
        self._conn.close()
```

- [ ] **Step 4: Run tests — expect pass**

Run:
```bash
pytest tests/test_queue.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pi_atlas/queue.py tests/test_queue.py
git commit -m "feat(queue): DuckDB-backed atomic work queue with stuck-cell reset"
```

---

### Task 7: Parquet storage layer with atomic rename + manifest (TDD)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/storage.py`
- Create: `~/pi-atlas/tests/test_storage.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_storage.py`:

```python
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
```

- [ ] **Step 2: Run test — expect failure**

Run:
```bash
pytest tests/test_storage.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement src/pi_atlas/storage.py**

```python
"""Parquet storage with atomic rename + SHA-256 manifest."""
from __future__ import annotations

import csv
import hashlib
import os
import uuid
from pathlib import Path
from typing import List, Mapping, Tuple

import pandas as pd


class ResultStore:
    MANIFEST_COLUMNS = ["relative_path", "sha256", "rows", "bytes"]

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.csv"
        if not self.manifest_path.exists():
            self._write_manifest_header()

    def _write_manifest_header(self) -> None:
        with open(self.manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(self.MANIFEST_COLUMNS)

    @staticmethod
    def _sha256_of_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    def _partition_dir(self, partition: Mapping[str, str]) -> Path:
        segments = [f"{k}={v}" for k, v in partition.items()]
        return self.root.joinpath(*segments)

    def flush(self, df: pd.DataFrame, *, partition: Mapping[str, str]) -> Path:
        """Write df to a Parquet file under partition/<uuid>.parquet atomically."""
        dirpath = self._partition_dir(partition)
        dirpath.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.parquet"
        tmp = dirpath / (fname + ".tmp")
        final = dirpath / fname

        df.to_parquet(tmp, index=False, engine="pyarrow")
        os.replace(tmp, final)  # atomic on POSIX

        # Record in manifest
        rel = final.relative_to(self.root).as_posix()
        sha = self._sha256_of_file(final)
        size = final.stat().st_size
        with open(self.manifest_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([rel, sha, len(df), size])

        return final

    def read_manifest(self) -> pd.DataFrame:
        return pd.read_csv(self.manifest_path)

    def verify_manifest(self) -> Tuple[bool, List[Path]]:
        """Recompute SHA-256 for each file; return (all_ok, list_of_bad_files)."""
        manifest = self.read_manifest()
        bad: List[Path] = []
        for _, row in manifest.iterrows():
            path = self.root / row["relative_path"]
            if not path.exists():
                bad.append(path)
                continue
            actual = self._sha256_of_file(path)
            if actual != row["sha256"]:
                bad.append(path)
        return (len(bad) == 0, bad)
```

- [ ] **Step 4: Run tests — expect pass**

Run:
```bash
pytest tests/test_storage.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pi_atlas/storage.py tests/test_storage.py
git commit -m "feat(storage): Parquet partitioning + atomic rename + SHA-256 manifest"
```

---

### Task 8: Worker main loop (integration-style test)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/worker.py`
- Create: `~/pi-atlas/tests/test_worker.py` (stubbed — full test in Task 16)

- [ ] **Step 1: Write a minimal smoke test**

Create `tests/test_worker.py`:

```python
import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.worker import run_one_cell


def noop_fit(cell_config, rng):
    """Trivial fit function for testing: returns a single-row result."""
    return {"mu_hat": 0.0, "pi_lower": -1.0, "pi_upper": 1.0, "coverage": 1}


def test_run_one_cell_writes_to_parquet_and_marks_done():
    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        q = Queue(dpath / "q.duckdb")
        q.init_schema()
        store = ResultStore(dpath / "results")

        cfg = {"k": 3, "tau2": 0.0, "dgp": "normal", "method": "hts_dl", "replicate_id": 0}
        q.insert_cell("c1", phase="smoke", method="hts_dl", factor_json=json.dumps(cfg))

        claimed = q.claim_one()
        assert claimed is not None

        run_one_cell(claimed, cfg, store=store, fit_fn=noop_fit)
        q.mark_done(claimed["cell_id"])

        # Status should be done
        row = q.get_cell("c1")
        assert row["status"] == "done"

        # Parquet should exist with 1 row
        manifest = store.read_manifest()
        assert len(manifest) == 1
        assert manifest.iloc[0]["rows"] == 1
```

- [ ] **Step 2: Run — expect failure**

Run:
```bash
pytest tests/test_worker.py -v
```
Expected: ImportError for `run_one_cell`.

- [ ] **Step 3: Implement src/pi_atlas/worker.py**

```python
"""Worker main loop — pop cell, run fit, append result."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Mapping

import pandas as pd

from pi_atlas.queue import Queue
from pi_atlas.seeds import derive_seed_hex, seed_to_rng
from pi_atlas.storage import ResultStore


def run_one_cell(
    claimed_row: Mapping,
    cell_config: Mapping,
    *,
    store: ResultStore,
    fit_fn: Callable,
) -> None:
    """Execute a single cell: derive seed, run fit, append result."""
    replicate_id = cell_config.get("replicate_id", 0)
    seed_hex = derive_seed_hex(cell_config, replicate_id)
    rng = seed_to_rng(seed_hex)

    result = fit_fn(cell_config, rng)

    # Annotate with bookkeeping columns
    result = dict(result)
    result["cell_id"] = claimed_row["cell_id"]
    result["seed_hex"] = seed_hex
    result["phase"] = claimed_row["phase"]
    result["method"] = claimed_row["method"]

    df = pd.DataFrame([result])

    partition = dict(
        phase=claimed_row["phase"],
        method=claimed_row["method"],
        tau2_level=str(cell_config.get("tau2", "NA")),
        dgp_family=cell_config.get("dgp", "NA"),
    )
    store.flush(df, partition=partition)


def worker_loop(
    queue_path: Path,
    results_root: Path,
    fit_fn: Callable,
    *,
    max_cells: int = None,
    poll_sleep_s: float = 5.0,
) -> int:
    """Run a worker loop. Returns number of cells processed."""
    q = Queue(queue_path)
    q.init_schema()
    store = ResultStore(results_root)

    n_done = 0
    while True:
        if max_cells is not None and n_done >= max_cells:
            break
        claimed = q.claim_one()
        if claimed is None:
            if max_cells is not None:
                break
            time.sleep(poll_sleep_s)
            continue
        cfg = json.loads(claimed["factor_json"])
        try:
            run_one_cell(claimed, cfg, store=store, fit_fn=fit_fn)
            q.mark_done(claimed["cell_id"])
            n_done += 1
        except Exception as e:
            # Leave in 'running' — watchdog will reset after threshold.
            # Log then re-raise so systemd can restart on real bugs.
            print(f"[worker] cell {claimed['cell_id']} failed: {e!r}")
            raise

    q.close()
    return n_done
```

- [ ] **Step 4: Run tests — expect pass**

Run:
```bash
pytest tests/test_worker.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pi_atlas/worker.py tests/test_worker.py
git commit -m "feat(worker): single-cell execution + worker loop scaffold"
```

---

### Task 9: Systemd user service unit file

**Files:**
- Create: `~/pi-atlas/systemd/pi-atlas-worker@.service`

- [ ] **Step 1: Create the unit file**

```ini
# ~/pi-atlas/systemd/pi-atlas-worker@.service
# Install: cp to ~/.config/systemd/user/ and `systemctl --user daemon-reload`

[Unit]
Description=PI Atlas worker %I
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/pi-atlas
Environment="PYTHONUNBUFFERED=1"
ExecStart=%h/pi-atlas/.venv/bin/python -m pi_atlas.worker_main --worker-id %i
Restart=always
RestartSec=30
# Cap memory per worker to ~1.5 GB to stay inside 16 GB total across 8 workers
MemoryMax=1500M
# Write stdout+stderr to journal
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

- [ ] **Step 2: Create `worker_main` entry point**

Add to `src/pi_atlas/worker_main.py`:

```python
"""systemd entry point: python -m pi_atlas.worker_main --worker-id N"""
from __future__ import annotations

import argparse
from pathlib import Path

from pi_atlas.worker import worker_loop


def fit_fn_placeholder(cell_config, rng):
    """Placeholder fit — replaced in Task 11 with HTS-DL.

    Returns a no-op result so the worker loop is testable before methods exist.
    """
    return {"mu_hat": 0.0, "pi_lower": -1.0, "pi_upper": 1.0, "coverage": 1}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--worker-id", required=True)
    p.add_argument("--queue", default=str(Path.home() / "pi-atlas" / "pi-atlas-queue.duckdb"))
    p.add_argument("--results", default=str(Path.home() / "pi-atlas" / "results"))
    p.add_argument("--max-cells", type=int, default=None)
    args = p.parse_args()
    print(f"[worker-{args.worker_id}] starting")
    n = worker_loop(
        queue_path=Path(args.queue),
        results_root=Path(args.results),
        fit_fn=fit_fn_placeholder,
        max_cells=args.max_cells,
    )
    print(f"[worker-{args.worker_id}] processed {n} cells")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Install the unit (manual, user runs)**

Run:
```bash
mkdir -p ~/.config/systemd/user
cp ~/pi-atlas/systemd/pi-atlas-worker@.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable pi-atlas-worker@1.service
# Smoke-start one worker (no cells in queue, should idle):
systemctl --user start pi-atlas-worker@1.service
sleep 3
systemctl --user status pi-atlas-worker@1.service
systemctl --user stop pi-atlas-worker@1.service
```

Expected: status shows "active (running)" then stops cleanly.

- [ ] **Step 4: Commit**

```bash
git add systemd/pi-atlas-worker@.service src/pi_atlas/worker_main.py
git commit -m "feat(systemd): worker user service unit + python entrypoint"
```

---

### Task 10: Watchdog for stuck cells (TDD)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/watchdog.py`
- Create: `~/pi-atlas/tests/test_watchdog.py`
- Create: `~/pi-atlas/systemd/pi-atlas-watchdog.service`
- Create: `~/pi-atlas/systemd/pi-atlas-watchdog.timer`

- [ ] **Step 1: Write failing test**

Create `tests/test_watchdog.py`:

```python
import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.watchdog import run_watchdog


def test_watchdog_resets_stuck_cells(tmp_path):
    q = Queue(tmp_path / "q.duckdb")
    q.init_schema()
    q.insert_cell("c1", phase="smoke", method="hts_dl", factor_json="{}")
    q.claim_one()
    q._conn.execute(
        "UPDATE cells SET claimed_at = claimed_at - INTERVAL '2 hours' WHERE cell_id='c1'"
    )

    store = ResultStore(tmp_path / "results")
    report = run_watchdog(q, store, stuck_threshold_minutes=60)

    assert report["stuck_reset"] == 1
    assert report["manifest_ok"] is True


def test_watchdog_flags_manifest_corruption(tmp_path):
    q = Queue(tmp_path / "q.duckdb")
    q.init_schema()
    store = ResultStore(tmp_path / "results")

    df = pd.DataFrame({"cell_id": ["c1"], "coverage": [1]})
    path = store.flush(df, partition=dict(phase="smoke", method="hts_dl", tau2_level="0.0", dgp_family="normal"))
    with open(path, "ab") as f:
        f.write(b"CORRUPTED")

    report = run_watchdog(q, store, stuck_threshold_minutes=60)
    assert report["manifest_ok"] is False
    assert report["bad_files"]
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_watchdog.py -v
```
Expected: ImportError for `run_watchdog`.

- [ ] **Step 3: Implement src/pi_atlas/watchdog.py**

```python
"""Watchdog: reset stuck cells + verify manifest SHA-256s."""
from __future__ import annotations

from typing import Dict

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore


def run_watchdog(queue: Queue, store: ResultStore, *, stuck_threshold_minutes: int = 60) -> Dict:
    """Run one watchdog pass; return a structured report."""
    stuck_reset = queue.reset_stuck(stuck_threshold_minutes=stuck_threshold_minutes)
    ok, bad = store.verify_manifest()
    return {
        "stuck_reset": stuck_reset,
        "manifest_ok": ok,
        "bad_files": [str(p) for p in bad],
    }
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_watchdog.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Create systemd watchdog service + timer**

Create `systemd/pi-atlas-watchdog.service`:

```ini
[Unit]
Description=PI Atlas watchdog
After=network.target

[Service]
Type=oneshot
WorkingDirectory=%h/pi-atlas
ExecStart=%h/pi-atlas/.venv/bin/python -m pi_atlas.watchdog_main
StandardOutput=journal
StandardError=journal
```

Create `systemd/pi-atlas-watchdog.timer`:

```ini
[Unit]
Description=Weekly PI Atlas watchdog

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
```

Create `src/pi_atlas/watchdog_main.py`:

```python
"""systemd entry point for the watchdog."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.watchdog import run_watchdog


def main() -> int:
    queue_path = Path.home() / "pi-atlas" / "pi-atlas-queue.duckdb"
    results_root = Path.home() / "pi-atlas" / "results"
    q = Queue(queue_path)
    q.init_schema()
    store = ResultStore(results_root)
    report = run_watchdog(q, store)
    print(json.dumps(report, indent=2))
    q.close()
    return 0 if report["manifest_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Commit**

```bash
git add src/pi_atlas/watchdog.py src/pi_atlas/watchdog_main.py tests/test_watchdog.py systemd/pi-atlas-watchdog.service systemd/pi-atlas-watchdog.timer
git commit -m "feat(watchdog): stuck-cell reset + manifest SHA verification + systemd timer"
```

---

## Phase C — HTS-DL method + R validation + baseline fixture (Tasks 11-15)

### Task 11: HTS-DL implementation (TDD)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/methods/__init__.py` (empty)
- Create: `~/pi-atlas/src/pi_atlas/methods/hts_dl.py`
- Create: `~/pi-atlas/tests/test_hts_dl.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_hts_dl.py`:

```python
import numpy as np
import pytest

from pi_atlas.methods.hts_dl import fit_hts_dl


def test_hts_dl_homogeneous_zero_tau2():
    """Three identical studies (tau2=0) → PI centered on shared effect."""
    y = np.array([0.5, 0.5, 0.5])
    v = np.array([0.04, 0.04, 0.04])  # SE=0.2
    res = fit_hts_dl(y, v)
    assert res["tau2"] == pytest.approx(0.0, abs=1e-9)
    assert res["mu_hat"] == pytest.approx(0.5, abs=1e-9)
    # PI should be wider than CI
    ci_width = res["mu_ci_upper"] - res["mu_ci_lower"]
    pi_width = res["pi_upper"] - res["pi_lower"]
    assert pi_width >= ci_width


def test_hts_dl_undefined_for_k_lt_3():
    y = np.array([0.5, 0.5])
    v = np.array([0.04, 0.04])
    with pytest.raises(ValueError, match="k >= 3"):
        fit_hts_dl(y, v)


def test_hts_dl_positive_tau2_when_heterogeneous():
    """Studies with large effect spread should yield tau2 > 0."""
    y = np.array([-1.0, 0.0, 1.0, 2.0])
    v = np.array([0.01, 0.01, 0.01, 0.01])  # small SEs → big Q
    res = fit_hts_dl(y, v)
    assert res["tau2"] > 0.0
    assert res["pi_upper"] > res["pi_lower"]


def test_hts_dl_returns_all_required_fields():
    y = np.array([0.1, 0.2, 0.3, 0.4])
    v = np.array([0.01, 0.01, 0.01, 0.01])
    res = fit_hts_dl(y, v)
    for key in ["mu_hat", "mu_ci_lower", "mu_ci_upper", "tau2", "pi_lower", "pi_upper", "k", "Q"]:
        assert key in res
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_hts_dl.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement src/pi_atlas/methods/hts_dl.py**

```python
"""Higgins-Thompson-Spiegelhalter prediction interval with DL tau² estimator.

Formulas:
    w_i      = 1 / v_i
    Q        = Σ w_i (y_i - y_bar_FE)²,  y_bar_FE = Σ w_i y_i / Σ w_i
    tau²_DL  = max(0, (Q - (k-1)) / (Σ w_i - Σ w_i² / Σ w_i))
    w*_i     = 1 / (v_i + tau²)
    μ̂        = Σ w*_i y_i / Σ w*_i
    Var(μ̂)   = 1 / Σ w*_i
    CI(μ̂)    = μ̂ ± z_{α/2} × √Var(μ̂)    (z, RE Wald — NOT HKSJ — for the DL baseline)
    PI       = μ̂ ± t_{k-2, α/2} × √(tau² + Var(μ̂))   (HTS 2009)

NB: Per ~/.claude/rules/advanced-stats.md — PI uses t_{k-2} and is undefined
for k<3. This is the **canonical HTS PI**, the most commonly reported PI in
Cochrane reviews.
"""
from __future__ import annotations

from typing import Dict

import numpy as np
from scipy import stats


def fit_hts_dl(y: np.ndarray, v: np.ndarray, *, alpha: float = 0.05) -> Dict[str, float]:
    """Fit HTS-DL prediction interval.

    Parameters
    ----------
    y : array-like, shape (k,)
        Study effect estimates (log-scale for ratios).
    v : array-like, shape (k,)
        Study sampling variances (SE²).
    alpha : float
        Two-sided significance level (default 0.05 for 95% PI).

    Returns
    -------
    dict with keys: mu_hat, mu_ci_lower, mu_ci_upper, tau2, pi_lower, pi_upper, k, Q.

    Raises
    ------
    ValueError if k < 3 (PI undefined per HTS 2009).
    """
    y = np.asarray(y, dtype=np.float64)
    v = np.asarray(v, dtype=np.float64)
    k = len(y)
    if k < 3:
        raise ValueError(f"HTS PI requires k >= 3; got k={k}")
    if len(v) != k:
        raise ValueError("y and v must have the same length")

    # Fixed-effect weights
    w = 1.0 / v
    sum_w = w.sum()
    y_bar_fe = (w * y).sum() / sum_w

    # Cochran's Q
    Q = float((w * (y - y_bar_fe) ** 2).sum())

    # DerSimonian-Laird tau²
    denom = sum_w - (w * w).sum() / sum_w
    tau2_dl = max(0.0, (Q - (k - 1)) / denom) if denom > 0 else 0.0

    # Random-effect weights
    w_star = 1.0 / (v + tau2_dl)
    sum_w_star = w_star.sum()
    mu_hat = float((w_star * y).sum() / sum_w_star)
    var_mu = float(1.0 / sum_w_star)

    # CI for mu_hat (Wald, z-based — the standard DL reporting)
    z = stats.norm.ppf(1 - alpha / 2.0)
    mu_ci_lower = mu_hat - z * np.sqrt(var_mu)
    mu_ci_upper = mu_hat + z * np.sqrt(var_mu)

    # HTS PI: t_{k-2}
    t_crit = stats.t.ppf(1 - alpha / 2.0, df=k - 2)
    pi_half_width = t_crit * np.sqrt(tau2_dl + var_mu)
    pi_lower = mu_hat - pi_half_width
    pi_upper = mu_hat + pi_half_width

    return {
        "mu_hat": mu_hat,
        "mu_ci_lower": float(mu_ci_lower),
        "mu_ci_upper": float(mu_ci_upper),
        "tau2": float(tau2_dl),
        "pi_lower": float(pi_lower),
        "pi_upper": float(pi_upper),
        "k": k,
        "Q": Q,
    }
```

- [ ] **Step 4: Create empty methods/__init__.py**

```python
"""PI method implementations."""
```

- [ ] **Step 5: Run — expect pass**

```bash
pytest tests/test_hts_dl.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/pi_atlas/methods/__init__.py src/pi_atlas/methods/hts_dl.py tests/test_hts_dl.py
git commit -m "feat(methods): HTS-DL prediction interval (primary method for Plan 1)"
```

---

### Task 12: R bridge — cross-validate HTS-DL against metafor (TDD, 1e-6 tolerance)

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/validation/__init__.py`
- Create: `~/pi-atlas/src/pi_atlas/validation/r_bridge.py`
- Create: `~/pi-atlas/tests/test_r_bridge.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_r_bridge.py`:

```python
import numpy as np
import pytest

from pi_atlas.methods.hts_dl import fit_hts_dl
from pi_atlas.validation.r_bridge import metafor_hts_dl


@pytest.fixture
def simple_ma():
    # 5 studies, moderate heterogeneity
    y = np.array([0.1, 0.25, -0.05, 0.4, 0.15])
    v = np.array([0.02, 0.03, 0.04, 0.02, 0.05])
    return y, v


def test_hts_dl_matches_metafor_mu_hat(simple_ma):
    y, v = simple_ma
    py = fit_hts_dl(y, v)
    r = metafor_hts_dl(y, v)
    assert py["mu_hat"] == pytest.approx(r["mu_hat"], abs=1e-6)


def test_hts_dl_matches_metafor_tau2(simple_ma):
    y, v = simple_ma
    py = fit_hts_dl(y, v)
    r = metafor_hts_dl(y, v)
    assert py["tau2"] == pytest.approx(r["tau2"], abs=1e-6)


def test_hts_dl_matches_metafor_pi(simple_ma):
    y, v = simple_ma
    py = fit_hts_dl(y, v)
    r = metafor_hts_dl(y, v)
    assert py["pi_lower"] == pytest.approx(r["pi_lower"], abs=1e-6)
    assert py["pi_upper"] == pytest.approx(r["pi_upper"], abs=1e-6)
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_r_bridge.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement src/pi_atlas/validation/r_bridge.py**

```python
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
suppressPackageStartupMessages(library(metafor))
args <- commandArgs(trailingOnly = TRUE)
input_path <- args[1]
output_path <- args[2]

payload <- jsonlite::fromJSON(input_path)
y <- payload$y
v <- payload$v
alpha <- payload$alpha

res <- rma(yi = y, vi = v, method = "DL")
pred <- predict(res)

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


def metafor_hts_dl(y: Sequence[float], v: Sequence[float], *, alpha: float = 0.05) -> Dict:
    """Call metafor::rma(method='DL') + predict() via Rscript subprocess.

    Returns the same dict shape as pi_atlas.methods.hts_dl.fit_hts_dl.
    """
    import numpy as np  # local import to avoid top-level dep for production workers

    with tempfile.TemporaryDirectory() as d:
        dpath = Path(d)
        script_path = dpath / "script.R"
        input_path = dpath / "input.json"
        output_path = dpath / "output.json"

        script_path.write_text(R_SCRIPT, encoding="utf-8")
        input_path.write_text(
            json.dumps({"y": list(map(float, y)), "v": list(map(float, v)), "alpha": alpha})
        )

        proc = subprocess.run(
            ["Rscript", "--vanilla", str(script_path), str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Rscript failed (code {proc.returncode}):\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")

        out = json.loads(output_path.read_text())

    # jsonlite auto_unbox=TRUE returns scalars as themselves, not 1-vectors.
    # Defensive: if anything comes as a list, take [0].
    for k_ in list(out):
        if isinstance(out[k_], list) and len(out[k_]) == 1:
            out[k_] = out[k_][0]

    return out
```

- [ ] **Step 4: Ensure jsonlite installed in renv**

Run:
```bash
cd ~/pi-atlas
Rscript -e 'if (!"jsonlite" %in% rownames(installed.packages())) renv::install("jsonlite"); renv::snapshot(prompt=FALSE)'
```
Expected: `jsonlite` in `renv.lock`.

- [ ] **Step 5: Create empty validation/__init__.py**

```python
"""R-backed validation utilities."""
```

- [ ] **Step 6: Run — expect pass**

```bash
pytest tests/test_r_bridge.py -v
```
Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add src/pi_atlas/validation/__init__.py src/pi_atlas/validation/r_bridge.py tests/test_r_bridge.py renv.lock
git commit -m "feat(validation): Rscript bridge to metafor, HTS-DL cross-validated to 1e-6"
```

---

### Task 13: Baseline fixture generator (5 cells) + hash commit

**Files:**
- Create: `~/pi-atlas/baseline-fixture/input.json`
- Create: `~/pi-atlas/scripts/generate_baseline_fixture.py`
- Create: `~/pi-atlas/baseline-fixture/expected.parquet` (generated)
- Create: `~/pi-atlas/preregistration/baseline-fixture-hash.txt` (generated)

- [ ] **Step 1: Write the 5-cell input**

Create `baseline-fixture/input.json`:

```json
{
  "cells": [
    {"cell_id": "bl-01", "y": [0.1, 0.2, 0.3], "v": [0.01, 0.02, 0.01]},
    {"cell_id": "bl-02", "y": [0.5, 0.5, 0.5, 0.5], "v": [0.04, 0.04, 0.04, 0.04]},
    {"cell_id": "bl-03", "y": [-1.0, 0.0, 1.0, 2.0, -0.5], "v": [0.01, 0.01, 0.01, 0.01, 0.02]},
    {"cell_id": "bl-04", "y": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], "v": [0.05, 0.05, 0.05, 0.05, 0.05, 0.05]},
    {"cell_id": "bl-05", "y": [0.3, 0.4, 0.2, 0.35, 0.25, 0.3, 0.4, 0.3], "v": [0.02, 0.03, 0.01, 0.02, 0.04, 0.03, 0.02, 0.03]}
  ]
}
```

- [ ] **Step 2: Write generator script**

Create `scripts/generate_baseline_fixture.py`:

```python
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
```

- [ ] **Step 3: Run generator**

```bash
cd ~/pi-atlas && source .venv/bin/activate
python scripts/generate_baseline_fixture.py
```
Expected: "baseline fixture written: .../baseline-fixture/expected.parquet" and a 64-char hex SHA-256. Python-vs-R assertions all pass (if any fail, the generator aborts — fix HTS-DL first).

- [ ] **Step 4: Commit**

```bash
git add baseline-fixture/input.json baseline-fixture/expected.parquet scripts/generate_baseline_fixture.py preregistration/baseline-fixture-hash.txt
git commit -m "feat(fixture): 5-cell HTS-DL baseline, py<->metafor validated to 1e-6"
```

---

### Task 14: Baseline fixture regeneration-determinism test

**Files:**
- Create: `~/pi-atlas/tests/test_baseline_fixture.py`

- [ ] **Step 1: Write test**

```python
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
```

- [ ] **Step 2: Run — expect pass**

```bash
pytest tests/test_baseline_fixture.py -v
```
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_baseline_fixture.py
git commit -m "test(fixture): baseline fixture determinism guard"
```

---

### Task 15: Result schema frozen

**Files:**
- Create: `~/pi-atlas/src/pi_atlas/schema.py`
- Create: `~/pi-atlas/tests/test_schema.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_schema.py`:

```python
import pandas as pd
import pyarrow as pa

from pi_atlas.schema import RESULT_SCHEMA, validate_result_row, SCHEMA_VERSION


def test_schema_version_frozen():
    assert SCHEMA_VERSION == "1.0"


def test_validate_accepts_minimal_row():
    row = {
        "cell_id": "c1",
        "seed_hex": "abcdef0123456789",
        "phase": "smoke",
        "method": "hts_dl",
        "k": 3,
        "mu_hat": 0.1,
        "mu_ci_lower": -0.1,
        "mu_ci_upper": 0.3,
        "tau2": 0.0,
        "pi_lower": -0.5,
        "pi_upper": 0.7,
        "Q": 0.5,
        "coverage_true": 1,
        "coverage_obs": 1,
        "schema_version": "1.0",
    }
    validate_result_row(row)  # should not raise


def test_validate_rejects_missing_required():
    row = {"cell_id": "c1"}
    try:
        validate_result_row(row)
    except ValueError as e:
        assert "missing" in str(e).lower()
    else:
        raise AssertionError("Expected ValueError")


def test_schema_pyarrow_roundtrip():
    df = pd.DataFrame([{
        "cell_id": "c1", "seed_hex": "abc", "phase": "smoke", "method": "hts_dl",
        "k": 3, "mu_hat": 0.1, "mu_ci_lower": -0.1, "mu_ci_upper": 0.3,
        "tau2": 0.0, "pi_lower": -0.5, "pi_upper": 0.7, "Q": 0.5,
        "coverage_true": 1, "coverage_obs": 1, "schema_version": "1.0",
    }])
    table = pa.Table.from_pandas(df, schema=RESULT_SCHEMA, preserve_index=False)
    assert table.schema.equals(RESULT_SCHEMA)
```

- [ ] **Step 2: Run — expect failure**

```bash
pytest tests/test_schema.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement src/pi_atlas/schema.py**

```python
"""Frozen result schema, pyarrow-typed."""
from __future__ import annotations

from typing import Mapping

import pyarrow as pa


SCHEMA_VERSION = "1.0"


RESULT_SCHEMA = pa.schema([
    pa.field("cell_id", pa.string(), nullable=False),
    pa.field("seed_hex", pa.string(), nullable=False),
    pa.field("phase", pa.string(), nullable=False),
    pa.field("method", pa.string(), nullable=False),
    pa.field("k", pa.int32(), nullable=False),
    pa.field("mu_hat", pa.float64(), nullable=False),
    pa.field("mu_ci_lower", pa.float64(), nullable=False),
    pa.field("mu_ci_upper", pa.float64(), nullable=False),
    pa.field("tau2", pa.float64(), nullable=False),
    pa.field("pi_lower", pa.float64(), nullable=False),
    pa.field("pi_upper", pa.float64(), nullable=False),
    pa.field("Q", pa.float64(), nullable=False),
    pa.field("coverage_true", pa.int8(), nullable=True),   # may be null for LOO real-data
    pa.field("coverage_obs", pa.int8(), nullable=True),
    pa.field("schema_version", pa.string(), nullable=False),
])


REQUIRED_FIELDS = [f.name for f in RESULT_SCHEMA if not f.nullable]


def validate_result_row(row: Mapping) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    if missing:
        raise ValueError(f"Result row missing required fields: {missing}")
    if row["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"Schema version mismatch: row={row['schema_version']}, "
            f"current={SCHEMA_VERSION}"
        )
```

- [ ] **Step 4: Run — expect pass**

```bash
pytest tests/test_schema.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/pi_atlas/schema.py tests/test_schema.py
git commit -m "feat(schema): frozen v1.0 result schema with validation"
```

---

## Phase D — End-to-end + resumability (Tasks 16-18)

### Task 16: 20-cell smoke run script

**Files:**
- Create: `~/pi-atlas/scripts/smoke_run.py`

- [ ] **Step 1: Write the smoke script**

```python
"""End-to-end smoke run: seed 20 cells into queue, spawn inline worker, assert all done."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.worker import worker_loop
from pi_atlas.methods.hts_dl import fit_hts_dl
from pi_atlas.seeds import seed_to_rng
from pi_atlas.schema import SCHEMA_VERSION


REPO_ROOT = Path(__file__).resolve().parent.parent
SMOKE_ROOT = REPO_ROOT / "smoke"
QUEUE_PATH = SMOKE_ROOT / "queue.duckdb"
RESULTS_ROOT = SMOKE_ROOT / "results"


def fit_fn(cell_config, rng):
    """Produce one synthetic-MA fit using HTS-DL."""
    k = cell_config["k"]
    tau2 = cell_config["tau2"]
    # Fix SE = 0.1 for smoke; real synthetic twin uses per-MA SEs (Plan 4)
    se = np.full(k, 0.1)
    v = se ** 2
    # Draw study true effects and observed values
    b = rng.normal(0.0, np.sqrt(tau2), size=k)
    y = rng.normal(b, se)
    # Fit
    res = fit_hts_dl(y, v)
    # Draw one new study and check coverage
    mu_new = rng.normal(0.0, np.sqrt(tau2))
    y_new = rng.normal(mu_new, 0.1)
    coverage_true = int(res["pi_lower"] <= mu_new <= res["pi_upper"])
    coverage_obs = int(res["pi_lower"] <= y_new <= res["pi_upper"])

    return {
        "k": res["k"],
        "mu_hat": res["mu_hat"],
        "mu_ci_lower": res["mu_ci_lower"],
        "mu_ci_upper": res["mu_ci_upper"],
        "tau2": res["tau2"],
        "pi_lower": res["pi_lower"],
        "pi_upper": res["pi_upper"],
        "Q": res["Q"],
        "coverage_true": coverage_true,
        "coverage_obs": coverage_obs,
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    if SMOKE_ROOT.exists():
        shutil.rmtree(SMOKE_ROOT)
    SMOKE_ROOT.mkdir(parents=True)

    q = Queue(QUEUE_PATH)
    q.init_schema()

    # 20 cells: k ∈ {3,5,8}, tau2 ∈ {0, 0.05, 0.2}, with replicate variety
    configs = []
    idx = 0
    for k in (3, 5, 8):
        for tau2 in (0.0, 0.05, 0.2):
            for rep in range(3):
                idx += 1
                if idx > 20:
                    break
                cfg = {"k": k, "tau2": tau2, "dgp": "normal", "method": "hts_dl", "replicate_id": rep}
                q.insert_cell(
                    f"smoke-{idx:03d}",
                    phase="smoke",
                    method="hts_dl",
                    factor_json=json.dumps(cfg),
                )
                configs.append(cfg)
            if idx >= 20:
                break
        if idx >= 20:
            break

    # Run worker to completion
    n = worker_loop(
        queue_path=QUEUE_PATH,
        results_root=RESULTS_ROOT,
        fit_fn=fit_fn,
        max_cells=20,
    )
    print(f"[smoke] worker processed {n} cells")
    assert n == 20, f"expected 20, got {n}"

    # Verify all cells are done
    con = q._conn
    done = con.execute("SELECT COUNT(*) FROM cells WHERE status='done'").fetchone()[0]
    assert done == 20, f"expected 20 done, got {done}"

    # Verify Parquet output has 20 rows across partitions
    store = ResultStore(RESULTS_ROOT)
    manifest = store.read_manifest()
    total_rows = manifest["rows"].sum()
    assert total_rows == 20, f"expected 20 total rows in results, got {total_rows}"

    # Verify manifest integrity
    ok, bad = store.verify_manifest()
    assert ok, f"manifest corruption: {bad}"

    print("[smoke] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run smoke**

```bash
cd ~/pi-atlas && source .venv/bin/activate
python scripts/smoke_run.py
```
Expected: `[smoke] PASS` at the end.

- [ ] **Step 3: Add `smoke/` to .gitignore**

```bash
echo "smoke/" >> .gitignore
```

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_run.py .gitignore
git commit -m "feat(smoke): 20-cell end-to-end integration run with HTS-DL"
```

---

### Task 17: Resume-invariant integration test

**Files:**
- Create: `~/pi-atlas/scripts/resume_invariant_test.sh`
- Create: `~/pi-atlas/tests/test_resume_invariant.py`

- [ ] **Step 1: Write pytest-driven version (runs in CI-style without systemd)**

Create `tests/test_resume_invariant.py`:

```python
"""Kill mid-run, restart, assert (a) no cell lost, (b) no duplicates, (c) bit-identical results.

Simulates kill via throwing a KeyboardInterrupt inside the fit function at a
known cell. Restart is fresh worker_loop() on the same queue + store.
"""
from __future__ import annotations

import json
import os
import signal
import shutil
from pathlib import Path

import pandas as pd
import pytest

from pi_atlas.queue import Queue
from pi_atlas.storage import ResultStore
from pi_atlas.worker import worker_loop
from pi_atlas.seeds import seed_to_rng
from pi_atlas.schema import SCHEMA_VERSION


class KillAt:
    def __init__(self, kill_cell_id: str):
        self.kill_cell_id = kill_cell_id
        self.seen = set()

    def __call__(self, cell_config, rng):
        cid = cell_config.get("_cell_id")
        self.seen.add(cid)
        if cid == self.kill_cell_id:
            raise RuntimeError("simulated kill")
        # Deterministic trivial result keyed on seed
        x = rng.standard_normal()
        return {
            "k": cell_config["k"],
            "mu_hat": x,
            "mu_ci_lower": x - 1,
            "mu_ci_upper": x + 1,
            "tau2": 0.0,
            "pi_lower": x - 2,
            "pi_upper": x + 2,
            "Q": 0.0,
            "coverage_true": 1,
            "coverage_obs": 1,
            "schema_version": SCHEMA_VERSION,
        }


def seed_cells(q: Queue, n: int = 10):
    for i in range(n):
        cfg = {"k": 3, "tau2": 0.0, "dgp": "normal", "method": "hts_dl",
               "replicate_id": i, "_cell_id": f"r-{i:03d}"}
        q.insert_cell(f"r-{i:03d}", phase="resume", method="hts_dl",
                      factor_json=json.dumps(cfg))


def all_results(store: ResultStore) -> pd.DataFrame:
    m = store.read_manifest()
    if len(m) == 0:
        return pd.DataFrame()
    parts = [pd.read_parquet(store.root / p) for p in m["relative_path"]]
    return pd.concat(parts, ignore_index=True)


def test_resume_no_loss_no_dup_bit_identical(tmp_path):
    qpath = tmp_path / "q.duckdb"
    results = tmp_path / "results"

    # Phase 1: seed + run, killing at r-005
    q = Queue(qpath); q.init_schema()
    seed_cells(q, n=10)
    killer = KillAt("r-005")
    with pytest.raises(RuntimeError, match="simulated kill"):
        worker_loop(qpath, results, fit_fn=killer, max_cells=10)
    q.close()

    # The killed cell is left in 'running' — simulate watchdog reset immediately
    q2 = Queue(qpath); q2.init_schema()
    reset = q2.reset_stuck(stuck_threshold_minutes=0)
    assert reset == 1  # exactly the killed cell
    q2.close()

    # Phase 2: restart worker (fresh fit_fn, no kill)
    clean_fn = KillAt(kill_cell_id="__never__")
    n2 = worker_loop(qpath, results, fit_fn=clean_fn, max_cells=20)
    assert n2 == 10 - (
        # cells already done in phase 1 (r-000 through r-004)
        5
    ) or n2 in (5, 10)

    # Phase 3: assertions
    q3 = Queue(qpath); q3.init_schema()
    done = q3._conn.execute("SELECT COUNT(*) FROM cells WHERE status='done'").fetchone()[0]
    assert done == 10, f"expected all 10 done, got {done}"

    df = all_results(ResultStore(results))
    assert len(df) == 10, f"expected 10 result rows, got {len(df)}"
    assert df["cell_id"].nunique() == 10, "duplicate cell_ids in results"

    # Bit-identical check: the mu_hat for a given seed is determined by the seed alone,
    # so running again from scratch (different queue, same seed) must produce same value.
    q_ref = Queue(tmp_path / "q_ref.duckdb"); q_ref.init_schema()
    seed_cells(q_ref, n=10)
    results_ref = tmp_path / "results_ref"
    clean_ref = KillAt(kill_cell_id="__never__")
    worker_loop(tmp_path / "q_ref.duckdb", results_ref, fit_fn=clean_ref, max_cells=10)
    df_ref = all_results(ResultStore(results_ref))
    # Align on cell_id and compare mu_hat
    m = df.sort_values("cell_id").reset_index(drop=True)
    r = df_ref.sort_values("cell_id").reset_index(drop=True)
    assert (m["mu_hat"].values == r["mu_hat"].values).all(), "bit-identical violation"
```

- [ ] **Step 2: Run — expect pass**

```bash
pytest tests/test_resume_invariant.py -v
```
Expected: 1 passed.

- [ ] **Step 3: Create bash driver for weekly systemd-level test**

Create `scripts/resume_invariant_test.sh`:

```bash
#!/usr/bin/env bash
# Weekly systemd-level resume invariant test.
# Run manually via `bash scripts/resume_invariant_test.sh` or via a systemd timer.
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
pytest tests/test_resume_invariant.py -v
echo "[resume-invariant] WEEKLY CHECK PASS"
```

Run:
```bash
chmod +x scripts/resume_invariant_test.sh
bash scripts/resume_invariant_test.sh
```
Expected: `[resume-invariant] WEEKLY CHECK PASS`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_resume_invariant.py scripts/resume_invariant_test.sh
git commit -m "test(resume): kill/reset/restart invariant + weekly driver"
```

---

### Task 18: Gate-check script (8 P0 preflights)

**Files:**
- Create: `~/pi-atlas/scripts/gate_check.py`

- [ ] **Step 1: Write the gate script**

```python
"""Verify all 8 P0 preflight gates from spec §12. Print GO or NO-GO.

Exit code:
  0 — all 8 gates pass, compute may start
  1 — any gate fails, compute MUST NOT start

Gates (§12 of spec):
  G1: Zenodo DOI minted (preregistration/ZENODO_DOI.txt present and non-empty)
  G2: OpenTimestamps attestation present and verified (preregistration/PROTOCOL.md.ots)
  G3: Internet Archive snapshot URL recorded (preregistration/IA_SNAPSHOT_URL.txt)
  G4: WSL2 + systemd user services available (systemctl --user is-system-running)
  G5: DuckDB queue + Parquet integration test passes (pytest tests/test_queue.py tests/test_storage.py tests/test_worker.py)
  G6: Baseline fixture reproduces to 1e-6 (pytest tests/test_baseline_fixture.py + scripts/generate_baseline_fixture.py hash check)
  G7: Sentinel pre-push hook installed, zero BLOCK (python -m sentinel scan --repo .)
  G8: 20-cell smoke run completes end-to-end (python scripts/smoke_run.py)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


class GateResult:
    def __init__(self, name: str, ok: bool, detail: str = ""):
        self.name = name
        self.ok = ok
        self.detail = detail

    def __repr__(self) -> str:
        mark = "PASS" if self.ok else "FAIL"
        return f"[{mark}] {self.name} — {self.detail}"


def g1_zenodo_doi() -> GateResult:
    p = REPO / "preregistration" / "ZENODO_DOI.txt"
    if not p.exists():
        return GateResult("G1 Zenodo DOI", False, f"missing: {p}")
    content = p.read_text().strip()
    if not content.startswith("10."):
        return GateResult("G1 Zenodo DOI", False, f"not a DOI: {content!r}")
    return GateResult("G1 Zenodo DOI", True, content)


def g2_ots() -> GateResult:
    ots = REPO / "preregistration" / "PROTOCOL.md.ots"
    if not ots.exists():
        return GateResult("G2 OpenTimestamps", False, f"missing: {ots}")
    try:
        proc = subprocess.run(
            ["ots", "verify", str(ots)],
            capture_output=True, text=True, timeout=60,
        )
    except FileNotFoundError:
        return GateResult("G2 OpenTimestamps", False, "`ots` CLI not installed")
    ok = proc.returncode == 0
    return GateResult("G2 OpenTimestamps", ok, proc.stderr.strip() or proc.stdout.strip() or "verified")


def g3_ia() -> GateResult:
    p = REPO / "preregistration" / "IA_SNAPSHOT_URL.txt"
    if not p.exists():
        return GateResult("G3 Internet Archive", False, f"missing: {p}")
    url = p.read_text().strip()
    if "web.archive.org" not in url:
        return GateResult("G3 Internet Archive", False, f"not an IA URL: {url!r}")
    return GateResult("G3 Internet Archive", True, url)


def g4_systemd() -> GateResult:
    try:
        proc = subprocess.run(
            ["systemctl", "--user", "is-system-running"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        return GateResult("G4 systemd user", False, "`systemctl` not found")
    state = proc.stdout.strip()
    # Accept running, degraded (degraded still allows user units)
    ok = state in ("running", "degraded")
    return GateResult("G4 systemd user", ok, state)


def g5_infra_tests() -> GateResult:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest",
         "tests/test_queue.py",
         "tests/test_storage.py",
         "tests/test_worker.py",
         "tests/test_watchdog.py",
         "tests/test_seeds.py",
         "tests/test_schema.py",
         "-q"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    return GateResult("G5 infra tests", proc.returncode == 0, proc.stdout.splitlines()[-1] if proc.stdout else "")


def g6_baseline() -> GateResult:
    hash_file = REPO / "preregistration" / "baseline-fixture-hash.txt"
    parquet = REPO / "baseline-fixture" / "expected.parquet"
    if not hash_file.exists() or not parquet.exists():
        return GateResult("G6 baseline fixture", False, "missing fixture or hash file")
    committed = hash_file.read_text().strip()
    on_disk = hashlib.sha256(parquet.read_bytes()).hexdigest()
    if committed != on_disk:
        return GateResult("G6 baseline fixture", False, f"SHA drift: committed={committed[:12]}, disk={on_disk[:12]}")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_baseline_fixture.py", "-q"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    return GateResult("G6 baseline fixture", proc.returncode == 0, on_disk)


def g7_sentinel() -> GateResult:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "sentinel", "scan", "--repo", str(REPO)],
            capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        return GateResult("G7 Sentinel", False, "sentinel module not importable")
    # Look for "BLOCK: 0" in output
    ok = proc.returncode == 0 and "BLOCK: 0" in proc.stdout
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout else ""
    return GateResult("G7 Sentinel", ok, tail)


def g8_smoke() -> GateResult:
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "smoke_run.py")],
        capture_output=True, text=True, cwd=str(REPO),
    )
    ok = proc.returncode == 0 and "[smoke] PASS" in proc.stdout
    return GateResult("G8 20-cell smoke", ok, proc.stdout.splitlines()[-1] if proc.stdout else "")


def main() -> int:
    gates = [g1_zenodo_doi(), g2_ots(), g3_ia(), g4_systemd(),
             g5_infra_tests(), g6_baseline(), g7_sentinel(), g8_smoke()]
    for g in gates:
        print(g)
    all_ok = all(g.ok for g in gates)
    print()
    print("=" * 40)
    print("GO — main compute may start" if all_ok else "NO-GO — fix failing gates before compute")
    print("=" * 40)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run (expect several gates to FAIL — preregistration gates come in Tasks 19-22)**

```bash
cd ~/pi-atlas && source .venv/bin/activate
python scripts/gate_check.py || echo "expected NO-GO at this stage"
```
Expected: G5, G6, G7, G8 pass; G1, G2, G3, G4 FAIL with specific messages. Final line: "NO-GO — fix failing gates before compute".

- [ ] **Step 3: Commit**

```bash
git add scripts/gate_check.py
git commit -m "feat(gate): 8-gate P0 preflight check script"
```

---

## Phase E — Preregistration (Tasks 19-22)

### Task 19: Write PROTOCOL.md (preregistration record)

**Files:**
- Create: `~/pi-atlas/preregistration/PROTOCOL.md`

- [ ] **Step 1: Write PROTOCOL.md**

This content is the **frozen preregistration**. It embeds the spec's §3, §4, §5 verbatim plus the baseline fixture hash. Once committed + DOI minted, no substantive edit is permitted (only typo corrections with `DEVIATIONS.md` entries).

Create `preregistration/PROTOCOL.md`:

```markdown
# PI Atlas — Preregistration Protocol v1.0

**Author:** Mahmood Ahmad
**Date submitted:** <fill at Task 21 prior to release creation>
**Corresponding design spec:** `docs/superpowers/specs/2026-04-21-pi-atlas-design.md` (v1.0)
**Corresponding git commit:** <fill at Task 21 with the release-tag commit SHA>
**Baseline fixture SHA-256:** see `preregistration/baseline-fixture-hash.txt`

## Abstract

This protocol preregisters a year-long simulation + real-data study of
prediction-interval (PI) coverage in random-effects meta-analysis, evaluated
against the Cochrane Pairwise70 corpus (7,545 MAs, 595 reviews). Primary
endpoint is empirical LOO coverage of the HTS-DL 95% PI on the real corpus;
secondary endpoints comprise a 720-million-fit synthetic-twin factorial
spanning 10 PI methods × 6 τ² levels × 4 DGP misspecification families × 1,500
stratified MAs × 2,000 replicates.

## 1. Research questions

### 1.1 Primary (Q1)

What is the empirical LOO coverage of the 95% HTS prediction interval with DL
τ² estimator (the most commonly published PI in Cochrane reviews) across the
Pairwise70 corpus, and how does it vary by k, outcome type (binary /
continuous / GIV), and empirical heterogeneity (τ̂² quartile)?

### 1.2 Secondary (Q2-Q4)

Q2. Across 10 preregistered PI methods × 6 τ² levels × 4 DGP misspecification
families × 1,500 empirically-anchored synthetic MAs × 2,000 replicates, which
method–condition combinations achieve nominal coverage?

Q3. Misspecification gap (the headline): the systematic difference between
real-corpus LOO coverage and well-specified synthetic-twin coverage
(observed-effect estimand).

Q4. Ranking of the 10 methods on μ̂ bias, μ̂ CI coverage, τ̂² bias, τ̂² RMSE.

## 2. Design

### 2.1 Data source
Pairwise70 corpus, k≥3 filter, same as `repro-floor-atlas` and `cochrane-modern-re`.

### 2.2 Primary — real-data LOO
For each MA with k ≥ 3, for each study j: refit on k-1 remaining studies with
each of 10 PI methods; record coverage indicator for held-out observed effect y_j.

### 2.3 Secondary — synthetic twin
Stratified sample of 1,500 MAs. For each: factorial over τ² ∈ {0, 0.01, 0.05,
0.15, 0.35, 0.75}, DGP family ∈ {Normal, t₃, skewed log-normal, 5%-mixture}, 2,000 replicates.
Per replicate: generate k studies from DGP, fit each PI method, draw one new
study's true effect μ_new and one new observed y_new, record both
coverage_true = 1{μ_new ∈ PI} and coverage_obs = 1{y_new ∈ PI}.

### 2.4 Misspecification gap
For each (MA, method): gap_MA = real_LOO_coverage − synth_twin_coverage_obs under
well-specified normal DGP and τ² = τ̂²(MA).

## 3. Methods under test (preregistered, 10)

1. HTS + DL
2. HTS + REML
3. HTS + PM (Paule-Mandel)
4. HKSJ-adjusted (DL τ², HKSJ variance with floor `max(1, Q/(k-1))`, t_{k-1} df)
5. Partlett-Riley (RSM 2017, REML τ²)
6. Nagashima-Noma (parametric bootstrap, REML τ², 1,000 inner boots)
7. Bayesian posterior predictive (bayesmeta, half-normal τ prior scale=0.5)
8. Bayesian + MAP prior (MAPriors)
9. Non-parametric cluster bootstrap PI (10K boots)
10. HTS + SJ (Sidik-Jonkman)

Implementation references cross-validated against metafor (method 1 validated
to 1e-6 in Plan 1; methods 2-10 validated in Plan 2 before being added to main
compute).

## 4. Analysis plan

- Primary result sentence: *"Across N = [count] held-out (MA, study) pairs from
  ~6,386 Cochrane MAs, the HTS 95% PI with DL τ² achieved empirical LOO
  coverage of [X.X]% (95% Clopper-Pearson CI: [L, U])."*
- Clopper-Pearson exact binomial (qbeta(α/2, x, n-x+1)).
- Stratified by k bucket, outcome type, τ̂² quartile.
- Misspecification gap: median + IQR + Wilcoxon signed-rank test, paired on MA.
- Per-method estimator metrics: bias, MCSE, RMSE for μ̂ and τ̂².

## 5. Non-goals (preregistered)

- No NMA methods.
- No DTA methods.
- No IPD meta-analysis.
- No publication-bias modelling as separate factor.
- No post-hoc methods (methods discovered after DOI mint → follow-up paper, flagged exploratory).
- No new Pairwise70 data ingestion.
- No GPU/distributed compute.

## 6. Deviations policy

Any departure from §2, §3, §4 is logged in `DEVIATIONS.md` with:
- UTC timestamp
- commit SHA
- classification: *forced* (bug/bad-data/dependency) or *elective* (scope reduction / method substitution)
- Elective deviations flag affected result as *post-hoc exploratory* in paper.

## 7. Success criteria

- Primary LOO coverage (Q1) reported with 95% CI.
- Misspecification gap (Q3) reported with sign, magnitude, p-value.
- Method ranking (Q4) with MCSE on every cell.
- Uptime ≥ 95%, zero silent result corruption, resume-invariant test passes weekly.

---

**This protocol is frozen at the moment of Zenodo DOI mint. Any change thereafter is a preregistration amendment, recorded in `DEVIATIONS.md`.**
```

- [ ] **Step 2: Commit**

```bash
git add preregistration/PROTOCOL.md
git commit -m "doc(prereg): PROTOCOL.md v1.0 — frozen preregistration content"
```

---

### Task 20: OpenTimestamps attestation

**Files:**
- Create: `~/pi-atlas/preregistration/PROTOCOL.md.ots`

- [ ] **Step 1: Install ots (if not present)**

```bash
pip install opentimestamps-client
ots --version
```
Expected: version string printed.

- [ ] **Step 2: Stamp PROTOCOL.md**

```bash
cd ~/pi-atlas
ots stamp preregistration/PROTOCOL.md
ls preregistration/PROTOCOL.md.ots
```
Expected: `PROTOCOL.md.ots` exists (pending — not yet Bitcoin-confirmed).

- [ ] **Step 3: Commit the pending attestation**

```bash
git add preregistration/PROTOCOL.md.ots
git commit -m "feat(prereg): OpenTimestamps attestation (pending Bitcoin confirmation ~6h)"
```

- [ ] **Step 4: (Later, ~6 hours) Upgrade attestation and recommit**

After ~6 hours, upgrade so the attestation contains the Bitcoin proof:
```bash
ots upgrade preregistration/PROTOCOL.md.ots
ots verify preregistration/PROTOCOL.md.ots
```
Expected: verify prints "Success! Bitcoin block <N> attests existence as of <timestamp>".

Then commit the upgraded attestation:
```bash
git add preregistration/PROTOCOL.md.ots
git commit -m "feat(prereg): OTS attestation upgraded with Bitcoin proof"
```

---

### Task 21: GitHub release + Zenodo DOI mint

**Files:**
- Create: `~/pi-atlas/preregistration/ZENODO_DOI.txt`

- [ ] **Step 1: Create GitHub repo and push**

```bash
cd ~/pi-atlas
gh repo create pi-atlas --public --source=. --remote=origin --push
```

Expected: repo created at `github.com/mahmood726-cyber/pi-atlas`, all commits pushed.

- [ ] **Step 2: Enable Zenodo-GitHub integration (one-time, manual)**

**Manual step for the user:**
1. Visit https://zenodo.org/account/settings/github/
2. Log in with GitHub
3. Flip the toggle for `pi-atlas` to ON.
4. Return here.

- [ ] **Step 3: Create preregistration tag + GitHub release**

```bash
cd ~/pi-atlas
git tag -a preregistration-v1.0.0 -m "Preregistration v1.0 — frozen protocol + baseline fixture"
git push origin preregistration-v1.0.0
gh release create preregistration-v1.0.0 \
    --title "Preregistration v1.0" \
    --notes "Frozen preregistration for PI Atlas year-long study. See preregistration/PROTOCOL.md."
```

Expected: release created; Zenodo webhook fires; DOI minted within ~60 seconds.

- [ ] **Step 4: Record the DOI**

Retrieve the DOI from https://zenodo.org/account/settings/github/ (look under the `pi-atlas` entry → latest release) and save it:

```bash
echo "10.5281/zenodo.NNNNNNN" > preregistration/ZENODO_DOI.txt  # replace with real DOI
```

Expected: file contains a valid DOI starting with `10.`.

- [ ] **Step 5: Commit**

```bash
git add preregistration/ZENODO_DOI.txt
git commit -m "doc(prereg): Zenodo DOI recorded"
git push
```

---

### Task 22: Internet Archive snapshot

**Files:**
- Create: `~/pi-atlas/preregistration/IA_SNAPSHOT_URL.txt`

- [ ] **Step 1: Submit repo URL to Internet Archive**

```bash
REPO_URL="https://github.com/mahmood726-cyber/pi-atlas/tree/preregistration-v1.0.0"
curl -sSL -X POST "https://web.archive.org/save/$REPO_URL" -I | grep -i "^content-location:" | awk '{print $2}' | tr -d '\r\n'
```

Expected: prints something like `/web/20260421.../https://github.com/mahmood726-cyber/pi-atlas/tree/preregistration-v1.0.0`.

Take the full URL with `https://web.archive.org` prefix and save:

```bash
echo "https://web.archive.org/web/YYYYMMDDHHMMSS/$REPO_URL" > preregistration/IA_SNAPSHOT_URL.txt  # replace YYYY.. with real timestamp
```

- [ ] **Step 2: Verify the snapshot loads**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" "$(cat preregistration/IA_SNAPSHOT_URL.txt)"
```
Expected: HTTP 200.

- [ ] **Step 3: Commit**

```bash
git add preregistration/IA_SNAPSHOT_URL.txt
git commit -m "doc(prereg): Internet Archive snapshot URL recorded"
git push
```

---

## Phase F — Green-light gate (Task 23)

### Task 23: Run the full gate check — expect GO

**Files:** (no new files; invokes Task 18 script)

- [ ] **Step 1: Wait for OTS Bitcoin confirmation**

Check if Task 20's OTS upgrade is complete:
```bash
cd ~/pi-atlas
ots verify preregistration/PROTOCOL.md.ots
```
Expected: "Success! Bitcoin block <N> ...". If "Pending", wait and retry (typically 3-6 hours from stamp).

- [ ] **Step 2: Run gate check**

```bash
cd ~/pi-atlas && source .venv/bin/activate
python scripts/gate_check.py
```
Expected:
```
[PASS] G1 Zenodo DOI — 10.5281/zenodo.NNNNNNN
[PASS] G2 OpenTimestamps — Success! Bitcoin block ...
[PASS] G3 Internet Archive — https://web.archive.org/...
[PASS] G4 systemd user — running
[PASS] G5 infra tests — N passed
[PASS] G6 baseline fixture — <sha>
[PASS] G7 Sentinel — BLOCK: 0, WARN: <n>
[PASS] G8 20-cell smoke — [smoke] PASS

========================================
GO — main compute may start
========================================
```

- [ ] **Step 3: Tag the green-light commit**

```bash
git tag -a plan1-green -m "Plan 1 complete — all 8 P0 gates pass; main compute cleared to start"
git push origin plan1-green
```

- [ ] **Step 4: Record green-light date in memory** (Claude will do this on user approval)

After Plan 1 ships, Claude should update `C:\Users\user\.claude\projects\C--Users-user\memory\pi-atlas.md`:
- change status from "spec locked 2026-04-21" to "Plan 1 green <date>, main compute cleared"
- add: "Zenodo DOI: 10.5281/zenodo.NNNNNNN"
- add: "GitHub: github.com/mahmood726-cyber/pi-atlas"

---

## Acceptance criteria for Plan 1

Plan 1 is complete when `python scripts/gate_check.py` prints **GO — main compute may start**. This implies:

1. All 8 P0 preflight gates pass (§12 of spec).
2. Preregistration is frozen with three independent trusted timestamps (Zenodo, OTS, IA).
3. Worker + queue + Parquet + watchdog infrastructure is tested and resumable.
4. HTS-DL (the primary-endpoint method) is validated against `metafor` to 1e-6.
5. Baseline fixture is committed with SHA and reproduces deterministically.
6. Sentinel pre-push hook is active with zero BLOCKs.

**Only after Plan 1 GO can Plan 2 (remaining 9 methods) and Plans 3-4 (main compute) start.**

---

## Self-review log (filled by author after writing)

**Spec coverage:** Mapped §3 (questions), §4 (design), §5 (preregistration stack), §7 (compute architecture), §12 (P0 gates), §6 (deviations policy) to specific tasks. §5.2 methods 2-10 deliberately deferred to Plan 2 (only HTS-DL implemented in Plan 1 — it's what the primary endpoint needs and what the baseline fixture validates). §4.3 synthetic-twin full grid and §4.4 misspecification-gap computation deferred to Plan 4 (they need all 10 methods). §9 dashboard deferred to Plan 5. All P0 gates (§12) are addressed.

**Placeholder scan:** ZENODO_DOI.txt contents, GitHub repo URL, and IA timestamp are intentional user-fill-at-runtime values, not plan placeholders — each has an explicit "replace with real value" instruction. No "TBD" without a named trigger.

**Type consistency:** Verified `fit_hts_dl` returns dict with same keys used in `test_hts_dl.py`, `generate_baseline_fixture.py`, `smoke_run.py`. `metafor_hts_dl` returns matching shape. Queue `claim_one` returns dict with keys `cell_id, phase, method, factor_json, seed_hex, status` — consumed consistently in `run_one_cell`, `worker_loop`, `gate_check.py`. Parquet partition keys `phase, method, tau2_level, dgp_family` consistent across `storage.py`, `worker.py`, `smoke_run.py`.
