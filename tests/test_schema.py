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
