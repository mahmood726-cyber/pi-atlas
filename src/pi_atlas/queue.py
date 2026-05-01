"""DuckDB-backed work queue for PI Atlas cells.

Single-writer model. Workers atomically claim cells via UPDATE...RETURNING.
Stuck cells (running > stuck_threshold_minutes) are reset to pending by a
watchdog.
"""
from __future__ import annotations

import time
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
    def __init__(self, db_path: Path, read_only: bool = False):
        self.db_path = Path(db_path)
        self.read_only = read_only

    def _execute_with_retry(self, query: str, params: list = None, fetchone=False, fetchall=False):
        retries = 50
        for i in range(retries):
            try:
                # context manager automatically closes the connection
                with duckdb.connect(str(self.db_path), read_only=self.read_only) as conn:
                    cur = conn.execute(query, params or [])
                    if fetchone:
                        return cur.fetchone()
                    if fetchall:
                        return cur.fetchall()
                    return None
            except duckdb.IOException as e:
                err_str = str(e).lower()
                if "being used by another process" in err_str or "lock" in err_str:
                    time.sleep(0.5 + 0.1 * i)
                else:
                    raise
        raise RuntimeError(f"Could not acquire DuckDB lock on {self.db_path} after {retries} retries.")

    def init_schema(self) -> None:
        self._execute_with_retry(SCHEMA)

    def insert_cell(
        self,
        cell_id: str,
        *,
        phase: str,
        method: str,
        factor_json: str,
        seed_hex: Optional[str] = None,
    ) -> None:
        self._execute_with_retry(
            "INSERT INTO cells (cell_id, phase, method, factor_json, seed_hex) VALUES (?, ?, ?, ?, ?)",
            [cell_id, phase, method, factor_json, seed_hex]
        )

    def claim_one(self) -> Optional[dict]:
        row = self._execute_with_retry(
            """
            UPDATE cells SET status='running', claimed_at=NOW() 
            WHERE cell_id = (
              SELECT cell_id FROM cells WHERE status='pending' 
              ORDER BY cell_id LIMIT 1
            ) 
            RETURNING cell_id, phase, method, factor_json, seed_hex, status
            """,
            fetchone=True
        )
        if row is None:
            return None
        cols = ["cell_id", "phase", "method", "factor_json", "seed_hex", "status"]
        return dict(zip(cols, row))

    def mark_done(self, cell_id: str) -> None:
        self._execute_with_retry(
            "UPDATE cells SET status='done', completed_at=NOW() WHERE cell_id=?",
            [cell_id]
        )

    def get_cell(self, cell_id: str) -> Optional[dict]:
        row = self._execute_with_retry(
            """
            SELECT cell_id, phase, method, factor_json, seed_hex, status, 
            claimed_at, completed_at FROM cells WHERE cell_id=?
            """,
            [cell_id],
            fetchone=True
        )
        if row is None:
            return None
        cols = [
            "cell_id", "phase", "method", "factor_json", "seed_hex",
            "status", "claimed_at", "completed_at",
        ]
        return dict(zip(cols, row))

    def reset_stuck(self, stuck_threshold_minutes: int = 60) -> int:
        rows = self._execute_with_retry(
            f"""
            UPDATE cells SET status='pending', claimed_at=NULL 
            WHERE status='running' 
            AND claimed_at < NOW() - INTERVAL '{stuck_threshold_minutes} minutes' 
            RETURNING cell_id
            """,
            fetchall=True
        )
        return len(rows) if rows else 0

    def close(self) -> None:
        # Nothing to close if we connect per-query
        pass

