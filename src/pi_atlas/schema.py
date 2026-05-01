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
