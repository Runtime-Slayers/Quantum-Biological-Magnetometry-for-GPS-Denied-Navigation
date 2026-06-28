import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import argparse
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from quantum_navigation import (
    B_EARTH,
    nv_odmr_spectrum,
    extract_field_from_odmr,
    radical_pair_compass,
    dead_reckoning_nav,
    nv_odmr_spectrum_3d,
    extract_field_3d_from_odmr,
    radical_pair_singlet_yield,
    QuantumNavigationEKF
)

def main():
    parser = argparse.ArgumentParser(description="Quantum Navigation Simulation CLI")
    parser.add_argument("--noise-std", type=float, default=1e-3, help="Radical-pair singlet yield noise")
    parser.add_argument("--mag-noise-tesla", type=float, default=1e-7, help="NV magnetic field measurement noise")
    parser.add_argument("--num-steps", type=int, default=100, help="Number of navigation steps")
    parser.add_argument("--output-json", type=str, default="output/navigation_results.json", help="Path to save output results")
    parser.add_argument("--no-plots", action="store_true", help="Disable plotting")
    args = parser.parse_args()
    
    logger.info("Starting advanced 3D Quantum Navigation EKF Simulation...")
    
    dt = 0.1
    t_steps = args.num_steps
    
    # 1. Generate ground truth trajectory (a circle ascending in spirals)
    # Positions, velocities, heading (theta)
    t = np.linspace(0, 4 * np.pi, t_steps)
    r = 10.0  # radius of circle
    true_x = r * np.cos(t)
    true_y = r * np.sin(t)
    true_z = 0.5 * t
    
    true_pos = np.vstack((true_x, true_y, true_z)).T
    
    # Compute ground truth heading (tangent to circle)
    true_theta = (t + np.pi/2) % (2 * np.pi)
    
    # Compute ground truth velocities
    true_vx = -r * np.sin(t) * (4 * np.pi / t_steps) / dt
    true_vy = r * np.cos(t) * (4 * np.pi / t_steps) / dt
    true_vz = np.ones(t_steps) * 0.5 * (4 * np.pi / t_steps) / dt
    true_vel = np.vstack((true_vx, true_vy, true_vz)).T
    
    # Earth Magnetic Field vector in Earth frame (approx. 50 uT, pointing down/north-east)
    B_earth_vector = np.array([30e-6, 10e-6, -40e-6])
    
    # Simulate a spatial magnetic anomaly (e.g. localized Gaussian magnetic field disturbance)
    # Peak of anomaly is 40 uT in North, -20 uT in East, 30 uT in Down
    B_anom_peak = np.array([40e-6, -20e-6, 30e-6])
    p_anomaly_center = np.array([0.0, 15.0, 10.0]) # Near the midpoint of flight
    sigma_anomaly = 10.0  # Anomaly spatial radius (m)
    
    # 2. Simulate noisy IMU inputs
    np.random.seed(42)
    gyro_noise_std = 0.05   # rad/s
    accel_noise_std = 0.2   # m/s^2
    
    # Ground truth angular velocity (omega = dtheta/dt)
    true_omega = np.ones(t_steps) * (4 * np.pi / t_steps) / dt
    noisy_omega = true_omega + gyro_noise_std * np.random.randn(t_steps)
    
    # Ground truth acceleration in Earth frame
    true_ax_earth = -r * np.cos(t) * ((4 * np.pi / t_steps) / dt)**2
    true_ay_earth = -r * np.sin(t) * ((4 * np.pi / t_steps) / dt)**2
    true_az_earth = np.zeros(t_steps)
    
    # Transform to body frame
    noisy_a_body = []
    for i in range(t_steps):
        cos_t = np.cos(true_theta[i])
        sin_t = np.sin(true_theta[i])
        R_earth_to_body = np.array([
            [cos_t,  sin_t, 0.0],
            [-sin_t, cos_t, 0.0],
            [0.0,    0.0,   1.0]
        ])
        a_gravity = np.array([0.0, 0.0, 9.81])
        a_accel = np.array([true_ax_earth[i], true_ay_earth[i], true_az_earth[i]]) + a_gravity
        a_body = R_earth_to_body.dot(a_accel)
        noisy_a_body.append(a_body + accel_noise_std * np.random.randn(3))
        
    noisy_a_body = np.array(noisy_a_body)
    
    # 3. Instantiate Filters
    # Initial state matches ground truth
    x_init = np.array([true_pos[0,0], true_pos[0,1], true_pos[0,2], true_vel[0,0], true_vel[0,1], true_vel[0,2], true_theta[0]])
    P_init = np.eye(7) * 0.01
    
    # Upgraded 10D Anomaly-Tracking EKF
    ekf_upgraded = QuantumNavigationEKF(x_init=x_init, P_init=P_init, B_earth_vector=B_earth_vector)
    
    # Standard 7D EKF (anomaly estimation disabled)
    ekf_standard = QuantumNavigationEKF(x_init=x_init, P_init=P_init, B_earth_vector=B_earth_vector)
    # Set anomaly process noise and covariance to 0 so it stays locked at 0
    ekf_standard.Q[7:10, 7:10] = 0.0
    ekf_standard.P[7:10, 7:10] = 0.0
    
    # Raw dead reckoning
    dr_state = np.zeros(10)
    dr_state[0:7] = x_init.copy()
    dr_pos = [dr_state[0:3].copy()]
    dr_theta = dr_state[6]
    
    # EKF states log
    ekf_up_pos = [ekf_upgraded.x[0:3].copy()]
    ekf_up_theta = [ekf_upgraded.x[6]]
    
    ekf_std_pos = [ekf_standard.x[0:3].copy()]
    ekf_std_theta = [ekf_standard.x[6]]
    
    # 4. Main Simulation Loop
    for i in range(1, t_steps):
        # --- Dead Reckoning prediction ---
        dr_theta = (dr_theta + noisy_omega[i] * dt) % (2 * np.pi)
        cos_dr = np.cos(dr_theta)
        sin_dr = np.sin(dr_theta)
        R_dr = np.array([[cos_dr, -sin_dr, 0.0], [sin_dr, cos_dr, 0.0], [0.0, 0.0, 1.0]])
        a_dr = R_dr.dot(noisy_a_body[i]) - np.array([0.0, 0.0, 9.81])
        dr_state[3:6] += a_dr * dt
        dr_state[0:3] += dr_state[3:6] * dt
        dr_pos.append(dr_state[0:3].copy())
        
        # --- EKF Prediction Step ---
        ekf_upgraded.predict(noisy_a_body[i], noisy_omega[i], dt=dt)
        ekf_standard.predict(noisy_a_body[i], noisy_omega[i], dt=dt)
        
        # --- Spatial Magnetic Anomaly Simulation ---
        dist = np.linalg.norm(true_pos[i] - p_anomaly_center)
        anomaly_factor = np.exp(-(dist**2) / (2 * (sigma_anomaly**2)))
        B_anom_true = B_anom_peak * anomaly_factor
        B_earth_total = B_earth_vector + B_anom_true
        
        # --- EKF Update Step (Quantum Sensors) ---
        cos_tr = np.cos(true_theta[i])
        sin_tr = np.sin(true_theta[i])
        R_body = np.array([[cos_tr, sin_tr, 0.0], [-sin_tr, cos_tr, 0.0], [0.0, 0.0, 1.0]])
        B_body_true = R_body.dot(B_earth_total)
        
        f_ghz = np.linspace(2.80, 2.94, 2000)
        pl_clean = nv_odmr_spectrum_3d(B_body_true, f_ghz)
        pl_noisy = pl_clean + 1e-4 * np.random.randn(len(pl_clean))
        
        B_meas = extract_field_3d_from_odmr(pl_noisy, f_ghz)
        B_meas += args.mag_noise_tesla * np.random.randn(3)
        
        # EKF Update
        R_mag = np.eye(3) * (args.mag_noise_tesla**2 + 1e-13)
        
        # Upgraded EKF update
        ekf_upgraded.update_magnetometer(B_meas, R_mag)
        Y_meas = radical_pair_singlet_yield(B_body_true, noise_std=args.noise_std)
        ekf_upgraded.update_radical_pair(Y_meas, R_cov=args.noise_std**2)
        
        # Standard EKF update
        ekf_standard.update_magnetometer(B_meas, R_mag)
        ekf_standard.update_radical_pair(Y_meas, R_cov=args.noise_std**2)
        
        # Log states
        ekf_up_pos.append(ekf_upgraded.x[0:3].copy())
        ekf_up_theta.append(ekf_upgraded.x[6])
        
        ekf_std_pos.append(ekf_standard.x[0:3].copy())
        ekf_std_theta.append(ekf_standard.x[6])
        
    dr_pos = np.array(dr_pos)
    ekf_up_pos = np.array(ekf_up_pos)
    ekf_std_pos = np.array(ekf_std_pos)
    ekf_up_theta = np.array(ekf_up_theta)
    
    # Calculate performance metrics
    dr_err = np.linalg.norm(dr_pos - true_pos, axis=1)
    ekf_up_err = np.linalg.norm(ekf_up_pos - true_pos, axis=1)
    ekf_std_err = np.linalg.norm(ekf_std_pos - true_pos, axis=1)
    
    rmse_dr = np.sqrt(np.mean(dr_err**2))
    rmse_up = np.sqrt(np.mean(ekf_up_err**2))
    rmse_std = np.sqrt(np.mean(ekf_std_err**2))
    
    logger.info(f"Dead Reckoning Position RMSE: {rmse_dr:.3f} m")
    logger.info(f"Standard EKF Position RMSE:   {rmse_std:.3f} m")
    logger.info(f"Upgraded EKF Position RMSE:   {rmse_up:.3f} m")
    logger.info(f"Drift Reduction (Upgraded vs Standard): {((rmse_std - rmse_up) / rmse_std * 100):.2f}%")
    
    results = {
        "parameters": {
            "noise_std": args.noise_std,
            "mag_noise_tesla": args.mag_noise_tesla,
            "num_steps": args.num_steps
        },
        "metrics": {
            "dead_reckoning_rmse_m": rmse_dr,
            "standard_ekf_rmse_m": rmse_std,
            "upgraded_ekf_rmse_m": rmse_up,
            "drift_reduction_pct": (rmse_std - rmse_up) / rmse_std * 100
        },
        "trajectory": {
            "ground_truth": true_pos.tolist(),
            "dead_reckoning": dr_pos.tolist(),
            "standard_ekf": ekf_std_pos.tolist(),
            "upgraded_ekf": ekf_up_pos.tolist()
        }
    }
    
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {args.output_json}")
    
    if not args.no_plots:
        fig = plt.figure(figsize=(15, 6))
        
        # 1. 3D Position Plot
        ax1 = fig.add_subplot(121, projection='3d')
        ax1.plot(true_pos[:,0], true_pos[:,1], true_pos[:,2], label="Ground Truth", color="green", linewidth=2.0)
        ax1.plot(dr_pos[:,0], dr_pos[:,1], dr_pos[:,2], label="Raw Dead Reckoning", color="red", linestyle="--", alpha=0.8)
        ax1.plot(ekf_std_pos[:,0], ekf_std_pos[:,1], ekf_std_pos[:,2], label="Standard EKF Fusion", color="orange", linestyle="-.", alpha=0.9)
        ax1.plot(ekf_up_pos[:,0], ekf_up_pos[:,1], ekf_up_pos[:,2], label="Upgraded EKF (Anomaly tracking)", color="blue", linewidth=1.8)
        
        ax1.set_xlabel("X (m)")
        ax1.set_ylabel("Y (m)")
        ax1.set_zlabel("Z (m)")
        ax1.set_title("3D Flight Trajectory Comparison")
        ax1.legend()
        
        # 2. Position Error over time
        ax2 = fig.add_subplot(122)
        ax2.plot(dr_err, label="Raw Dead Reckoning Error", color="red", linewidth=1.5)
        ax2.plot(ekf_std_err, label="Standard EKF Error", color="orange", linewidth=1.5)
        ax2.plot(ekf_up_err, label="Upgraded 10D EKF Error", color="blue", linewidth=1.5)
        ax2.set_xlabel("Simulation Step")
        ax2.set_ylabel("Position Error (m)")
        ax2.set_title("Tracking Error Comparison under Magnetic Anomaly")
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend()
        
        plt.tight_layout()
        plot_path = args.output_json.replace('.json', '_plots.png')
        plt.savefig(plot_path, dpi=150)
        plt.close()
        logger.info(f"High-fidelity trajectory plots saved to {plot_path}")

if __name__ == "__main__":
    main()
