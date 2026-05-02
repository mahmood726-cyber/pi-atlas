import numpy as np
import pytest

from pi_atlas.methods.hts_generic import fit_hts_pm
from pi_atlas.validation.r_bridge import metafor_hts_pm


@pytest.fixture
def simple_ma():
    # 5 studies, moderate heterogeneity
    y = np.array([0.1, 0.25, -0.05, 0.4, 0.15])
    v = np.array([0.02, 0.03, 0.04, 0.02, 0.05])
    return y, v


def test_hts_pm_matches_metafor_mu_hat(simple_ma):
    y, v = simple_ma
    py = fit_hts_pm(y, v)
    r = metafor_hts_pm(y, v)
    assert py["mu_hat"] == pytest.approx(r["mu_hat"], abs=1e-4)


def test_hts_pm_matches_metafor_tau2(simple_ma):
    y, v = simple_ma
    py = fit_hts_pm(y, v)
    r = metafor_hts_pm(y, v)
    assert py["tau2"] == pytest.approx(r["tau2"], abs=1e-4)


def test_hts_pm_matches_metafor_pi(simple_ma):
    y, v = simple_ma
    py = fit_hts_pm(y, v)
    r = metafor_hts_pm(y, v)
    assert py["pi_lower"] == pytest.approx(r["pi_lower"], abs=1e-3)
    assert py["pi_upper"] == pytest.approx(r["pi_upper"], abs=1e-3)

def test_pm_zero_heterogeneity():
    y = np.array([0.5, 0.5, 0.5])
    v = np.array([0.04, 0.04, 0.04])
    py = fit_hts_pm(y, v)
    assert py["tau2"] == pytest.approx(0.0, abs=1e-9)
