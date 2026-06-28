import numpy as np

GAMMA_NV = 28.024e9   # NV gyromagnetic ratio Hz/T
B_EARTH   = 50e-6     # ~50 µT Earth field

# 1D functions for backwards compatibility
def nv_odmr_spectrum(B_field, freq_range_ghz, D_gs=2.87):
    f = freq_range_ghz  # GHz
    f_plus  = D_gs + GAMMA_NV * B_field / 1e9
    f_minus = D_gs - GAMMA_NV * B_field / 1e9
    linewidth = 0.0003  # GHz
    pl = np.ones_like(f)
    pl -= 0.3 * np.exp(-((f - f_plus)**2) / (2 * linewidth**2))
    pl -= 0.3 * np.exp(-((f - f_minus)**2) / (2 * linewidth**2))
    return pl

def extract_field_from_odmr(pl, freq_ghz, D_gs=2.87):
    left_mask = freq_ghz < D_gs
    right_mask = freq_ghz > D_gs
    if not np.any(left_mask) or not np.any(right_mask):
        return None
    peak_left_idx = np.argmin(pl[left_mask])
    peak_right_idx = np.argmin(pl[right_mask])
    peak_left = freq_ghz[left_mask][peak_left_idx]
    peak_right = freq_ghz[right_mask][peak_right_idx]
    splitting = peak_right - peak_left   # GHz
    B_est = splitting * 1e9 / (2 * GAMMA_NV)   # T
    return B_est

# 3D multi-axis NV-Diamond vector magnetometry
# Crystallographic orientation axes for NV centers in diamond
u1 = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
u2 = np.array([1.0, -1.0, -1.0]) / np.sqrt(3.0)
u3 = np.array([-1.0, 1.0, -1.0]) / np.sqrt(3.0)
u4 = np.array([-1.0, -1.0, 1.0]) / np.sqrt(3.0)
NV_AXES = [u1, u2, u3, u4]

# Bias field to lift degeneracy and resolve overlapping dips
B_BIAS = np.array([1000e-6, 800e-6, 1200e-6])

def nv_odmr_spectrum_3d(B_vec, freq_range_ghz, D_gs=2.87):
    """
    Generates 3D multi-axis ODMR spectrum for B_vec.
    Applies B_BIAS to separate resonances in the spectrum.
    """
    f = freq_range_ghz
    pl = np.ones_like(f)
    linewidth = 0.0005  # GHz
    dip_depth = 0.075
    
    # Calculate spectrum using the total field (measured + bias)
    B_total = B_vec + B_BIAS
    for u in NV_AXES:
        B_proj = np.dot(B_total, u)
        f_plus  = D_gs + GAMMA_NV * B_proj / 1e9
        f_minus = D_gs - GAMMA_NV * B_proj / 1e9
        pl -= dip_depth * np.exp(-((f - f_plus)**2) / (2 * linewidth**2))
        pl -= dip_depth * np.exp(-((f - f_minus)**2) / (2 * linewidth**2))
        
    return pl

def extract_field_3d_from_odmr(pl, freq_ghz, D_gs=2.87, B_hint=None):
    """
    Reconstructs the 3D magnetic field vector.
    Uses B_hint + B_BIAS to locate peaks, then subtracts B_BIAS from the result.
    """
    if B_hint is None:
        B_hint = np.array([30e-6, 10e-6, -40e-6])
        
    B_total_hint = B_hint + B_BIAS
    p = []
    
    for u in NV_AXES:
        proj_hint = np.dot(B_total_hint, u)
        f_exp = D_gs + GAMMA_NV * abs(proj_hint) / 1e9
        
        # Search in a small window of +/- 3 MHz around expected dip
        window = 0.003  # GHz
        mask = (freq_ghz >= f_exp - window) & (freq_ghz <= f_exp + window)
        if np.any(mask):
            idx = np.argmin(pl[mask])
            f_dip = freq_ghz[mask][idx]
        else:
            f_dip = f_exp
            
        sign = np.sign(proj_hint) if abs(proj_hint) > 1e-12 else 1.0
        p_val = sign * (f_dip - D_gs) * 1e9 / GAMMA_NV
        p.append(p_val)
        
    B_total_est = 0.75 * sum(p[i] * NV_AXES[i] for i in range(4))
    B_est = B_total_est - B_BIAS
    return B_est

# Radical-Pair spin dynamics biological compass model
def radical_pair_singlet_yield(B_vec, noise_std=1e-3, seed=None):
    """
    Simulates cryptochrome biological radical pair singlet yield.
    The yield depends on the direction of the magnetic field vector.
    """
    if seed is not None:
        np.random.seed(seed)
        
    B_mag = np.linalg.norm(B_vec)
    if B_mag < 1e-12:
        theta, phi = 0.0, 0.0
    else:
        theta = np.arccos(np.clip(B_vec[2] / B_mag, -1.0, 1.0))
        phi = np.arctan2(B_vec[1], B_vec[0])
        
    # Biological anisotropic yield model parameters
    Y0 = 0.38
    dY = 0.05
    chi = 0.8
    
    # Anisotropic yield: Ritz-inspired angular dependency
    yield_val = Y0 + dY * (np.cos(theta)**2 + chi * np.sin(theta)**2 * np.cos(phi)**2)
    
    # Add detector/biological signal noise
    noisy_yield = yield_val + noise_std * np.random.randn()
    return float(noisy_yield)

def radical_pair_compass(B_vec, noise_std=1e-7, seed=42):
    """
    Backwards compatible compass function returning singlet yield and inclination.
    """
    if seed is not None:
        np.random.seed(seed)
    B_mag = np.linalg.norm(B_vec)
    inclination = np.arcsin(np.clip(B_vec[2] / (B_mag + 1e-12), -1.0, 1.0))
    yield_signal = 0.5 * (1.0 + np.cos(2.0 * inclination))
    noisy = yield_signal + noise_std * np.random.randn()
    return float(noisy), float(np.degrees(inclination))
