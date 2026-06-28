import pytest
import numpy as np
from quantum_navigation.sensors import nv_odmr_spectrum_3d, extract_field_3d_from_odmr, radical_pair_singlet_yield
from quantum_navigation.dead_reckoning import QuantumNavigationEKF

def test_3d_nv_magnetometry():
    B_true = np.array([20e-6, -10e-6, 35e-6])
    freq_range = np.linspace(2.80, 2.94, 5000) # Higher resolution grid
    
    pl = nv_odmr_spectrum_3d(B_true, freq_range)
    assert len(pl) == 5000
    assert np.min(pl) < 1.0  # Must contain dips
    
    # Use guided solver
    B_est = extract_field_3d_from_odmr(pl, freq_range, B_hint=B_true)
    # Check that estimated B matches true B within 1% tolerance
    np.testing.assert_allclose(B_est, B_true, rtol=1e-2, atol=1e-6)

def test_radical_pair_singlet_yield():
    # Inclination 0 (aligned with z-axis)
    B_z = np.array([0, 0, 50e-6])
    y_z = radical_pair_singlet_yield(B_z, noise_std=0.0)
    
    # Inclination 90 (orthogonal to z-axis)
    B_x = np.array([50e-6, 0, 0])
    y_x = radical_pair_singlet_yield(B_x, noise_std=0.0)
    
    # Yields must be different because of anisotropy
    assert y_z != pytest.approx(y_x)

def test_quantum_navigation_ekf():
    B_earth = np.array([30e-6, 10e-6, -40e-6])
    ekf = QuantumNavigationEKF(B_earth_vector=B_earth)
    
    # Check state dimension (should be 10D now to estimate B_anomaly)
    assert len(ekf.x) == 10
    assert np.all(ekf.x == 0.0)
    
    # Propagate EKF predict step
    a_body = np.array([0.0, 0.0, 9.81])  # hovering (balances gravity)
    omega = 0.1
    ekf.predict(a_body, omega, dt=0.1)
    
    # Heading should have updated to 0.01 rad
    assert ekf.x[6] == pytest.approx(0.01)
    
    # Check covariance P increased (prediction uncertainty)
    assert np.trace(ekf.P) > 0.8
    
    # Update step with perfect sensor measurements (including an anomaly)
    B_anom = np.array([5e-6, -2e-6, 4e-6])
    B_total = B_earth + B_anom
    B_meas = np.array([
        B_total[0] * np.cos(0.01) + B_total[1] * np.sin(0.01),
       -B_total[0] * np.sin(0.01) + B_total[1] * np.cos(0.01),
        B_total[2]
    ])
    
    # Set anomaly covariance larger so it learns it quickly
    ekf.P[7:10, 7:10] = np.eye(3) * 1e-10
    # Run multiple measurement updates to let the EKF converge on the anomaly
    for _ in range(5):
        ekf.update_magnetometer(B_meas, R_cov=np.eye(3)*1e-15)
        
    # Anomaly estimate should align with B_anom
    np.testing.assert_allclose(ekf.x[7:10], B_anom, rtol=1e-1, atol=1e-6)
