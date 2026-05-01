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
