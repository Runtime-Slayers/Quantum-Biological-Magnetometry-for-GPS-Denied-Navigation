"""
Quantum-Biological Magnetometry for GPS-Denied Drone Navigation
NV-Diamond Sensors with Radical-Pair-Inspired Signal Processing
"""
import numpy as np

# Physical constants
GAMMA_NV = 28.024e9   # NV gyromagnetic ratio Hz/T
B_EARTH   = 50e-6     # ~50 µT Earth field

def nv_odmr_spectrum(B_field, freq_range_ghz, D_gs=2.87):
    """
    Simulated ODMR (Optically Detected Magnetic Resonance) spectrum.
    Returns PL intensity dip positions for NV centres.
    """
    f = freq_range_ghz  # GHz
    # Zero-field splitting + Zeeman shift
    f_plus  = D_gs + GAMMA_NV * B_field / 1e9
    f_minus = D_gs - GAMMA_NV * B_field / 1e9
    linewidth = 0.002  # GHz
    pl = np.ones_like(f)
    pl -= 0.3 * np.exp(-((f - f_plus)**2) / (2 * linewidth**2))
    pl -= 0.3 * np.exp(-((f - f_minus)**2) / (2 * linewidth**2))
    return pl

def extract_field_from_odmr(pl, freq_ghz, D_gs=2.87):
    """Locate ODMR dips and infer B field."""
    # Find two deepest dips
    neg_pl = -pl
    from_left = np.argsort(neg_pl)[:2]
    peaks = np.sort(freq_ghz[from_left])
    if len(peaks) < 2:
        return None
    splitting = peaks[1] - peaks[0]
    B_est = splitting * 1e9 / (2 * GAMMA_NV)
    return B_est

def radical_pair_compass(B_vec, noise_std=1e-7):
    """Radical-pair singlet yield as compass signal."""
    np.random.seed(42)
    B_mag = np.linalg.norm(B_vec)
    inclination = np.arcsin(B_vec[2] / (B_mag + 1e-12))
    # Anisotropic singlet yield
    yield_signal = 0.5 * (1 + np.cos(2 * inclination))
    noisy = yield_signal + noise_std * np.random.randn()
    return float(noisy), float(np.degrees(inclination))

def dead_reckoning_nav(B_field_sequence, dt=0.1, heading_init=0.0):
    """Estimate heading changes from sequential B field measurements."""
    headings = [heading_init]
    for i in range(1, len(B_field_sequence)):
        delta_B = B_field_sequence[i] - B_field_sequence[i-1]
        d_heading = np.degrees(np.arctan2(delta_B[1], delta_B[0]))
        headings.append(headings[-1] + d_heading * dt)
    return np.array(headings)

if __name__ == "__main__":
    print("Simulating NV-diamond quantum compass navigation...")
    f_ghz = np.linspace(2.80, 2.94, 1000)
    pl = nv_odmr_spectrum(B_EARTH, f_ghz)
    B_est = extract_field_from_odmr(pl, f_ghz)
    print(f"  True B field : {B_EARTH*1e6:.1f} µT")
    print(f"  Estimated B  : {B_est*1e6:.1f} µT")

    B_seq = np.array([[B_EARTH * np.cos(a), B_EARTH * np.sin(a), B_EARTH * 0.3]
                      for a in np.linspace(0, np.pi/6, 50)])
    headings = dead_reckoning_nav(B_seq)
    print(f"  Nav steps    : {len(headings)}")
    print(f"  Heading drift: {headings[-1] - headings[0]:.2f} deg")
    yield_sig, inclination = radical_pair_compass(B_seq[0])
    print(f"  Radical-pair yield: {yield_sig:.4f}  inclination: {inclination:.1f} deg")
    print("Quantum bio navigation complete.")
