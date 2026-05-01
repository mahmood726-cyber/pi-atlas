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
