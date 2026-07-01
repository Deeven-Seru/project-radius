# Project Radius — Quickstart Guide

> **3 steps. Run the AO pipeline in under 5 minutes.**

---

## 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> **OOPAO** (the simulation library) and its dependencies are installed automatically. Make sure you have `gcc` available for the C-Engine build step.

---

## 2. Build the C-Engine

The C-Engine is the high-performance real-time reconstruction core. Build it once:

```bash
make -C src/c_engine
```

Expected output: `Built: ../../build/c_engine.so`

---

## 3. Generate Data → Calibrate → Run

Run the three steps in sequence:

```bash
# Step 1: Generate 500 frames of simulated SH-WFS turbulence (OOPAO)
python scripts/generate_dataset.py

# Step 2: Calibrate the C-Engine interaction matrix
python scripts/export_gplus.py

# Step 3: Run the real-time AO pipeline at 1000 Hz
python scripts/live_camera_test.py --mode playback --frames 500 --fps 1000.0
```

You should see a live table of per-frame `R²` accuracy and Strehl Ratio, finishing with a summary:

```
C-Engine Processing Avg Latency: ~0.31 ms
Average Loop Rate:               ~1000 Hz
Shape Matching Accuracy (R²):    ~99.4%
```

---

## Configuration

All key parameters live at the **top of each script** — no config files required:

| Parameter | Script | Default | Description |
| :--- | :--- | :--- | :--- |
| `N_SUBAP` | `generate_dataset.py` | `20` | Number of subapertures per axis (e.g. 10, 20, 40) |
| `N_FRAMES` | `generate_dataset.py` | `500` | Number of telemetry frames to simulate |
| `r0` | `generate_dataset.py` | `0.15 m` | Fried parameter (smaller = stronger turbulence) |
| `N_ZERNIKE` | `export_gplus.py` | `55` | Number of Zernike modes to reconstruct |
| `--fps` | `live_camera_test.py` | `1000.0` | Target loop frequency in Hz |
| `--frames` | `live_camera_test.py` | `500` | Number of frames to process |

---

## Verify Accuracy

To compare C-Engine output against OOPAO ground truth:

```bash
python scripts/compare_outputs.py
```

---

## File Structure (this branch)

```
Project Radius/
├── src/c_engine/         ← Core C reconstruction engine (slopes.c, mvm_reconstructor.c)
├── src/core/             ← Hardware abstraction layer (camera_interface.py)
├── scripts/
│   ├── generate_dataset.py   ← Step 1: Simulate SH-WFS frames
│   ├── export_gplus.py       ← Step 2: Calibrate interaction matrix
│   ├── live_camera_test.py   ← Step 3: Run AO pipeline
│   └── compare_outputs.py    ← Verify accuracy vs. ground truth
├── data/
│   └── dataset/          ← Generated frames live here (auto-created)
├── docs/                 ← Architecture and physics documentation
├── requirements.txt      ← Python dependencies
└── QUICKSTART.md         ← This file
```
