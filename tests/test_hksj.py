import numpy as np
import pytest

from pi_atlas.methods.hksj import fit_hksj
from pi_atlas.validation.r_bridge import metafor_hksj


@pytest.fixture
def simple_ma():
    # 5 studies, moderate heterogeneity
    y = np.array([0.1, 0.25, -0.05, 0.4, 0.15])
    v = np.array([0.02, 0.03, 0.04, 0.02, 0.05])
    return y, v


def test_hksj_matches_metafor_mu_hat(simple_ma):
    y, v = simple_ma
    py = fit_hksj(y, v)
    r = metafor_hksj(y, v)
    assert py["mu_hat"] == pytest.approx(r["mu_hat"], abs=1e-5)


def test_hksj_matches_metafor_tau2(simple_ma):
    # HKSJ uses DL tau2
    y, v = simple_ma
    py = fit_hksj(y, v)
    r = metafor_hksj(y, v)
    assert py["tau2"] == pytest.approx(r["tau2"], abs=1e-5)


def test_hksj_matches_metafor_ci(simple_ma):
    y, v = simple_ma
    py = fit_hksj(y, v)
    r = metafor_hksj(y, v)
    # The Knapp-Hartung CI
    assert py["mu_ci_lower"] == pytest.approx(r["mu_ci_lower"], abs=1e-5)
    assert py["mu_ci_upper"] == pytest.approx(r["mu_ci_upper"], abs=1e-5)


def test_hksj_matches_metafor_pi(simple_ma):
    y, v = simple_ma
    py = fit_hksj(y, v)
    r = metafor_hksj(y, v)
    assert py["pi_lower"] == pytest.approx(r["pi_lower"], abs=1e-5)
    assert py["pi_upper"] == pytest.approx(r["pi_upper"], abs=1e-5)

def test_hksj_zero_heterogeneity():
    y = np.array([0.5, 0.5, 0.5])
    v = np.array([0.04, 0.04, 0.04])
    py = fit_hksj(y, v)
    assert py["tau2"] == pytest.approx(0.0, abs=1e-9)
    assert py["pi_upper"] == pytest.approx(py["pi_lower"], abs=1e-9)
