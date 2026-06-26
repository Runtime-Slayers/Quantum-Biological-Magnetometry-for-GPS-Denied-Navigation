import numpy as np

def radical_pair_compass(B_vec, noise_std=1e-7, seed=42):
    if seed is not None:
        np.random.seed(seed)
    B_mag = np.linalg.norm(B_vec)
    inclination = np.arcsin(B_vec[2] / (B_mag + 1e-12))
    yield_signal = 0.5 * (1 + np.cos(2 * inclination))
    noisy = yield_signal + noise_std * np.random.randn()
    return float(noisy), float(np.degrees(inclination))
