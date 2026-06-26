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
    dead_reckoning_nav
)

def main():
    parser = argparse.ArgumentParser(description="Quantum Navigation Simulation CLI")
    parser.add_argument("--noise-std", type=float, default=1e-7, help="Singlet yield compass noise")
    parser.add_argument("--num-steps", type=int, default=50, help="Number of navigation steps")
    parser.add_argument("--output-json", type=str, default="output/navigation_results.json", help="Path to save output results")
    parser.add_argument("--no-plots", action="store_true", help="Disable plotting")
    args = parser.parse_args()
    
    logger.info("Simulating NV-diamond quantum compass navigation...")
    
    f_ghz = np.linspace(2.80, 2.94, 1000)
    pl = nv_odmr_spectrum(B_EARTH, f_ghz)
    B_est = extract_field_from_odmr(pl, f_ghz)
    
    logger.info(f"True B field: {B_EARTH*1e6:.1f} uT | Estimated B: {B_est*1e6:.1f} uT")
    
    # Generate B field sequence
    B_seq = np.array([[B_EARTH * np.cos(a), B_EARTH * np.sin(a), B_EARTH * 0.3]
                      for a in np.linspace(0, np.pi/6, args.num_steps)])
    
    headings = dead_reckoning_nav(B_seq)
    logger.info(f"Heading drift over {args.num_steps} steps: {headings[-1] - headings[0]:.2f} deg")
    
    yield_sig, inclination = radical_pair_compass(B_seq[0], noise_std=args.noise_std)
    logger.info(f"Radical-pair yield: {yield_sig:.4f} | Inclination: {inclination:.1f} deg")
    
    results = {
        "parameters": {
            "noise_std": args.noise_std,
            "num_steps": args.num_steps
        },
        "odmr_estimation": {
            "true_B_field_T": B_EARTH,
            "estimated_B_field_T": B_est
        },
        "dead_reckoning": {
            "heading_drift_deg": headings[-1] - headings[0],
            "initial_heading_deg": headings[0],
            "final_heading_deg": headings[-1],
            "headings_sequence": headings.tolist()
        },
        "radical_pair": {
            "singlet_yield": yield_sig,
            "inclination_deg": inclination
        }
    }
    
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    with open(args.output_json, 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {args.output_json}")
    
    if not args.no_plots:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # 1. ODMR Spectrum
        ax = axes[0]
        ax.plot(f_ghz, pl, color='purple')
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("PL Intensity")
        ax.set_title("Simulated ODMR Spectrum")
        
        # 2. Heading
        ax = axes[1]
        ax.plot(headings, color='blue', marker='o')
        ax.set_xlabel("Step")
        ax.set_ylabel("Heading (deg)")
        ax.set_title("Estimated Heading over Steps")
        
        plt.tight_layout()
        plot_path = args.output_json.replace('.json', '_plots.png')
        plt.savefig(plot_path, dpi=150)
        plt.close()
        logger.info(f"Plots saved to {plot_path}")

if __name__ == "__main__":
    main()
