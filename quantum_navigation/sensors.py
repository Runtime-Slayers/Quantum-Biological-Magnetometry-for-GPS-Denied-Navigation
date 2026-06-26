import numpy as np

GAMMA_NV = 28.024e9   # NV gyromagnetic ratio Hz/T
B_EARTH   = 50e-6     # ~50 µT Earth field

def nv_odmr_spectrum(B_field, freq_range_ghz, D_gs=2.87):
    f = freq_range_ghz  # GHz
    f_plus  = D_gs + GAMMA_NV * B_field / 1e9
    f_minus = D_gs - GAMMA_NV * B_field / 1e9
    linewidth = 0.0003  # GHz — narrow linewidth to resolve close ODMR dips
    pl = np.ones_like(f)
    pl -= 0.3 * np.exp(-((f - f_plus)**2) / (2 * linewidth**2))
    pl -= 0.3 * np.exp(-((f - f_minus)**2) / (2 * linewidth**2))
    return pl

def extract_field_from_odmr(pl, freq_ghz, D_gs=2.87):
    """Extract magnetic field magnitude from NV-diamond ODMR spectrum.

    The ODMR spectrum has two dips at f± = D_gs ± GAMMA_NV * B / 1e9 (GHz).
    The splitting between dips is 2 * GAMMA_NV * B / 1e9, so
    B = splitting_GHz * 1e9 / (2 * GAMMA_NV).
    """
    # Find the two dip positions as the two smallest local minima
    # by searching in lower and upper halves of spectrum
    left_mask = freq_ghz < D_gs
    right_mask = freq_ghz > D_gs
    if not np.any(left_mask) or not np.any(right_mask):
        return None
    # Find deepest dip in each half
    peak_left_idx = np.argmin(pl[left_mask])
    peak_right_idx = np.argmin(pl[right_mask])
    peak_left = freq_ghz[left_mask][peak_left_idx]
    peak_right = freq_ghz[right_mask][peak_right_idx]
    splitting = peak_right - peak_left   # GHz
    B_est = splitting * 1e9 / (2 * GAMMA_NV)   # T
    return B_est
