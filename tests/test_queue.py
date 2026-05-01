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
    tmp_queue._execute_with_retry(
        "UPDATE cells SET claimed_at = claimed_at - INTERVAL '2 hours' WHERE cell_id='c1'"
    )
    reset = tmp_queue.reset_stuck(stuck_threshold_minutes=60)
    assert reset == 1
    row = tmp_queue.get_cell("c1")
    assert row["status"] == "pending"
