# Architecture

## Component Diagram

```
Python Orchestration Layer
         |  ctypes zero-copy pointer
C-Engine (c_engine.so)
    ├── slopes.c             CoG centroiding
    └── mvm_reconstructor.c  Zernike MVM + DM MVM
Calibration Data (CSV)
    ├── g_plus.csv
    ├── dm_coupling.csv
    └── valid_mask.csv
```

## Latency Budget

| Stage | Typical Time |
|:------|:------------|
| CoG centroiding (C) | ~0.010 ms |
| Zernike MVM (C) | ~0.015 ms |
| DM actuator MVM (C) | ~0.017 ms |
| **Total C-Engine** | **~0.044 ms** |

## Detailed Data Flow

1. `generate_dataset.py` → OOPAO → 500 `.bmp` + `ground_truth.csv`
2. `export_gplus.py` → OOPAO calibration → `g_plus.csv`, `dm_coupling.csv`, `valid_mask.csv`
3. `make` → `gcc -O3` → `build/c_engine.so`
4. `process_dataset.py`:
   a. Load CSV matrices into numpy arrays
   b. For each `.bmp`: compute_slopes → reconstruct_zernikes → compute_actuator_map
   c. Accumulate Zernike series → estimate_r0, estimate_tau0
   d. Print latency + accuracy summary
