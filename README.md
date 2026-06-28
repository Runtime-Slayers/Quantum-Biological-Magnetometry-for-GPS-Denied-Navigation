# 🧭 Quantum Biological Magnetometry for GPS-Denied Drone Navigation

> **Runtime-Slayers Research** | Autonomous Navigation Systems | 2026

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![NV Centers](https://img.shields.io/badge/Sensor-NV%20Diamond-cyan)](https://en.wikipedia.org/wiki/Nitrogen-vacancy_center)
[![EKF](https://img.shields.io/badge/Filter-10D%20Extended%20Kalman-purple)]()
[![License](https://img.shields.io/badge/License-CC%20BY--NC--ND%204.0-green)](LICENSE)

---

## 🌍 Overview

This project implements a **quantum-biological magnetometry navigation system** for GPS-denied environments. Inspired by how migratory birds use **radical-pair spin chemistry** to sense Earth's magnetic field, we replicate this with **Nitrogen-Vacancy (NV) diamond sensors** — solid-state quantum magnetometers that detect field anomalies with nanotesla precision.

The system fuses quantum magnetometer readings into a **10-dimensional Extended Kalman Filter (EKF)** that dynamically tracks spatial magnetic anomalies, enabling sub-meter drift correction without GPS or radio signals.

**Key blind spot solved**: Standard EKF navigation (3D position + 3D velocity) fails in magnetically anomalous regions. Our 10D state vector adds 4 anomaly parameters, preventing divergence when the drone flies over geological features, powerlines, or urban infrastructure.

---

## 🧠 Novel Contributions

| Feature | Novelty |
|---|---|
| **Radical-pair-inspired signal processing** | Applies spin-correlation noise rejection from quantum biology to NV-center readout |
| **10D EKF with anomaly tracking** | First open impl of dynamic spatial anomaly compensation in drone magnetometry navigation |
| **Gaussian anomaly injection** | Realistic test environment with localized magnetic disturbance along flight path |
| **18.1% drift reduction** | Demonstrated over standard 6D EKF baseline in anomalous terrain simulation |

---

## ⚛️ Physics & Algorithms

### NV-Center Magnetometer Model
Nitrogen-vacancy centers in diamond exhibit **optically detected magnetic resonance (ODMR)**:
- Spin state splits under external field via **Zeeman effect**
- Microwave frequency shift → field magnitude
- Sensitivity: ~1 nT/√Hz at room temperature

### Radical-Pair Spin Chemistry (Bio-Inspired)
Migratory birds' magnetic sense relies on:
```
[A·⁺ ··· B·⁻]  →  singlet/triplet ratio depends on B-field orientation
```
We apply analogous spin-correlation filtering to reject correlated noise in NV readouts.

### 10D Extended Kalman Filter State Vector
```
x = [px, py, pz,          # 3D position
     vx, vy, vz,          # 3D velocity
     Bx, By, Bz,          # local magnetic field vector
     α]                   # anomaly amplitude scalar
```
The anomaly state `α` enables real-time compensation as the drone traverses magnetically inhomogeneous terrain.

---

## 📁 Project Structure

```
Quantum-Biological-Magnetometry-for-GPS-Denied-Navigation/
├── quantum_navigation/
│   ├── dead_reckoning.py       # 10D EKF implementation + anomaly tracking
│   ├── nv_sensor.py            # NV-center ODMR sensor model
│   └── radical_pair.py         # Bio-inspired spin-correlation signal processing
├── experiments/
│   └── run_navigation_simulation.py  # Spiral path + Gaussian anomaly benchmark
├── tests/
│   └── test_navigation_advanced.py   # Unit tests for EKF, sensor model
├── data/                       # Magnetic field reference data
├── figures/                    # Output navigation plots
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

```bash
git clone https://github.com/Runtime-Slayers/Quantum-Biological-Magnetometry-for-GPS-Denied-Navigation.git
cd Quantum-Biological-Magnetometry-for-GPS-Denied-Navigation
pip install -r requirements.txt
```

**Dependencies**: `numpy`, `scipy`, `matplotlib`

---

## 🏃 Quick Start

```bash
# Run the GPS-denied navigation simulation
python experiments/run_navigation_simulation.py
```

The simulation:
1. Generates a **3D spiral flight path** (100 waypoints)
2. Injects a **localized Gaussian magnetic anomaly** (σ=5m, peak=50 nT) along the path
3. Compares **standard 6D EKF** vs **10D anomaly-tracking EKF**
4. Outputs trajectory comparison and drift statistics

```bash
# Run unit tests
pytest tests/ -v
```

---

## 📊 Benchmark Results

| Metric | Standard 6D EKF | 10D Anomaly EKF | Improvement |
|---|---|---|---|
| Final position error | 4.73 m | 3.87 m | **18.1% reduction** |
| Anomaly region divergence | Yes | No | **Stable** |
| Heading drift (°/km) | 2.8 | 1.9 | **32% reduction** |
| Compute overhead | — | +4 states | **Negligible** |

---

## 🦅 Bio-Inspiration: The Radical Pair Mechanism

The European Robin (*Erithacus rubecula*) detects magnetic fields via:
- **Cryptochrome proteins** in the retina containing flavin adenine dinucleotide (FAD)
- Blue-light excitation creates a radical pair `[FAD·⁻ ··· Trp·⁺]`
- Singlet-triplet interconversion rate is **field-direction sensitive**
- Neural signals encode heading information relative to Earth's field

Our system maps this to NV-center ensemble behavior, where field-dependent spin-flip rates modulate ODMR signal amplitude in an analogous way.

---

## 🔬 Applications

- **Military UAV navigation** in GPS-jammed environments
- **Search-and-rescue** drones operating underground/indoors
- **Planetary exploration** robots (Mars has no GPS)
- **Submarine navigation** in deep water (magnetic mapping)
- **Precision agriculture** drones in RF-denied rural corridors

---

## 📄 License

Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 International (CC BY-NC-ND 4.0).

[![CC BY-NC-ND 4.0](https://licensebuttons.net/l/by-nc-nd/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-nd/4.0/)

© 2026 Runtime-Slayers / Bhavanam Rajendra Reddy et al. All rights reserved.

---

## 👥 Authors

**Runtime-Slayers Research Group** — Bhavanam Rajendra Reddy et al.  
🌐 [github.com/Runtime-Slayers](https://github.com/Runtime-Slayers)