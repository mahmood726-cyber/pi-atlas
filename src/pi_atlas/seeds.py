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
