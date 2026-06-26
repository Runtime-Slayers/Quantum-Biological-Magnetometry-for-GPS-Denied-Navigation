import pytest
import numpy as np
from quantum_navigation import (
    GAMMA_NV,
    B_EARTH,
    nv_odmr_spectrum,
    extract_field_from_odmr,
    radical_pair_compass,
    dead_reckoning_nav
)

def test_nv_odmr():
    # Use high-resolution grid so narrow ODMR dips are well sampled
    f_ghz = np.linspace(2.80, 2.94, 5000)
    pl = nv_odmr_spectrum(B_EARTH, f_ghz)
    assert len(pl) == 5000
    assert np.min(pl) < 1.0

    B_est = extract_field_from_odmr(pl, f_ghz)
    # Allow 5% tolerance due to finite grid discretization of peak positions
    assert B_est == pytest.approx(B_EARTH, rel=5e-2)

def test_radical_pair_compass():
    B_vec = np.array([B_EARTH, 0, 0])
    y, inc = radical_pair_compass(B_vec, noise_std=0.0)
    assert inc == 0.0
    assert y == 1.0

def test_dead_reckoning():
    B_seq = np.array([[B_EARTH, 0, 0], [B_EARTH, B_EARTH, 0]])
    headings = dead_reckoning_nav(B_seq, dt=1.0)
    assert len(headings) == 2
    assert headings[0] == 0.0
    assert headings[1] == 90.0
