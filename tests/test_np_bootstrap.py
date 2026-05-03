import numpy as np
import pytest

from pi_atlas.methods.np_bootstrap import fit_np_bootstrap


@pytest.fixture
def simple_ma():
    y = np.array([0.1, 0.25, -0.05, 0.4, 0.15])
    v = np.array([0.02, 0.03, 0.04, 0.02, 0.05])
    return y, v


def test_np_bootstrap_returns_valid_dict(simple_ma):
    y, v = simple_ma
    res = fit_np_bootstrap(y, v)
    assert "pi_lower" in res
    assert "pi_upper" in res
    assert res["pi_lower"] < res["pi_upper"]
    assert res["mu_ci_lower"] < res["mu_ci_upper"]
    assert res["mu_hat"] > -0.5 and res["mu_hat"] < 0.5


def test_np_bootstrap_zero_heterogeneity():
    y = np.array([0.5, 0.5, 0.5])
    v = np.array([0.04, 0.04, 0.04])
    py = fit_np_bootstrap(y, v)
    
    # Since all y are identical, y_rand - base_mu = 0
    # and mu_hat_b will always be exactly 0.5
    assert py["pi_lower"] == pytest.approx(0.5, abs=1e-5)
    assert py["pi_upper"] == pytest.approx(0.5, abs=1e-5)
