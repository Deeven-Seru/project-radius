"""
compare_outputs.py
------------------
Runs C-Engine reconstruction on the dataset's BMP frames,
compares the generated output (predicted Zernike coefficients) with the 
known output (ground_truth.csv), and generates an accuracy report + comparison plot.
"""
import numpy as np
import ctypes as ct
import os
import matplotlib.pyplot as plt
from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, 'data', 'dataset')
BUILD_DIR = os.path.join(BASE, 'build')

def main():
    print("="*60)
    print("Loading calibration matrices and ground truth...")
    g_plus = np.loadtxt(os.path.join(DATA_DIR, 'g_plus.csv'), delimiter=',').astype(np.float32)
    dm_coupling = np.loadtxt(os.path.join(DATA_DIR, 'dm_coupling.csv'), delimiter=',').astype(np.float32)
    valid_mask = np.loadtxt(os.path.join(DATA_DIR, 'valid_mask.csv'), delimiter=',').astype(np.int32)
    ref_slopes = np.loadtxt(os.path.join(DATA_DIR, 'ref_slopes.csv'), delimiter=',').astype(np.float32)
    ground_truth = np.loadtxt(os.path.join(DATA_DIR, 'ground_truth.csv'), delimiter=',').astype(np.float32)
    
    n_valid = int(valid_mask.sum())
    n_slopes = 2 * n_valid
    n_zernike = 20
    n_act = 357
    
    # Load C-Engine
    lib = ct.CDLL(os.path.join(BUILD_DIR, 'c_engine.so'))
    lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3
    lib.compute_slopes.restype  = None
    lib.reconstruct_zernikes.argtypes = [ct.POINTER(ct.c_float)]*3 + [ct.c_int]*2
    lib.reconstruct_zernikes.restype  = None
    
    frames = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.bmp')])
    n_frames = len(frames)
    
    # Pre-allocate buffers
    slopes_buf = np.zeros(n_slopes, dtype=np.float32)
    zernikes = np.zeros(n_zernike, dtype=np.float32)
    
    generated_z = np.zeros((n_frames, n_zernike), dtype=np.float32)
    
    print(f"Processing {n_frames} frames through the C-Engine...")
    for idx, fname in enumerate(frames):
        img = np.array(Image.open(os.path.join(DATA_DIR, fname))).astype(np.float32)
        img_flat = np.ascontiguousarray(img.flatten())
        
        # Centroiding
        lib.compute_slopes(
            img_flat.ctypes.data_as(ct.POINTER(ct.c_float)),
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            ct.c_int(400), ct.c_int(n_valid), ct.c_int(20)
        )
        
        # Subtract reference slopes
        slopes_buf -= ref_slopes
        
        # Zernike reconstruction
        lib.reconstruct_zernikes(
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
            zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
            ct.c_int(n_zernike), ct.c_int(n_slopes)
        )
        
        generated_z[idx, :] = zernikes
        
    print("\n" + "="*70)
    print("SAMPLE FRAME COMPARISONS (KNOWN vs GENERATED)")
    print("="*70)
    
    sample_indices = [0, 100, 200, 300, 400]
    for idx in sample_indices:
        print(f"\n--- Frame {idx:03d} Zernike Modes (excluding Piston Z1) ---")
        print(f"{'Mode':<8} | {'Known Output (m)':<20} | {'Generated Output (m)':<20} | {'Abs Diff (m)':<15}")
        print("-"*70)
        for mode in range(1, 10): # Show modes Z2 to Z10 for space
            val_gt = ground_truth[idx, mode]
            val_pred = generated_z[idx, mode]
            diff = abs(val_gt - val_pred)
            print(f"Z{mode+1:<7d} | {val_gt:+19.6e} | {val_pred:+19.6e} | {diff:14.6e}")
            
    print("\n" + "="*50)
    print("PER-MODE ACCURACY METRICS (Z2 to Z20)")
    print("="*50)
    print(f"{'Mode':<8} | {'MSE':<12} | {'R2 Score':<10}")
    print("-"*36)
    
    r2_modes = []
    for j in range(1, n_zernike):
        mse = np.mean((generated_z[:, j] - ground_truth[:, j])**2)
        ss_res = np.sum((generated_z[:, j] - ground_truth[:, j])**2)
        ss_tot = np.sum((ground_truth[:, j] - np.mean(ground_truth[:, j]))**2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
        r2_modes.append(r2)
        print(f"Z{j+1:02d}      | {mse:.4e} | {r2*100:6.2f}%")
        
    # Global metrics
    ss_r = sum(np.sum((generated_z[i, 1:] - ground_truth[i, 1:])**2) for i in range(n_frames))
    ss_t = np.sum((ground_truth[:, 1:] - ground_truth[:, 1:].mean(axis=0))**2)
    r2_global = 1.0 - ss_r / ss_t if ss_t > 0 else 0.0
    
    r2_per_frame = []
    for i in range(n_frames):
        ss_res_f = np.sum((generated_z[i, 1:] - ground_truth[i, 1:])**2)
        ss_tot_f = np.sum((ground_truth[i, 1:] - np.mean(ground_truth[i, 1:]))**2)
        r2_f = 1.0 - (ss_res_f / ss_tot_f) if ss_tot_f > 0 else 1.0
        r2_per_frame.append(r2_f)
        
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    print(f"Absolute Global Temporal R² Accuracy: {r2_global*100:.4f}%")
    print(f"Average Per-Frame Spatial R² Accuracy: {np.mean(r2_per_frame)*100:.4f}%")
    
    # Generate visual comparison plot
    plt.figure(figsize=(12, 6))
    
    # Plot Tip (Z2) and Tilt (Z3) modes over time
    plt.subplot(2, 1, 1)
    plt.plot(ground_truth[:100, 1], 'k-', label='Known Tip (Z2) [Ground Truth]', alpha=0.8)
    plt.plot(generated_z[:100, 1], 'r--', label='Generated Tip (Z2) [C-Engine Output]', alpha=0.8)
    plt.title("Tip (Z2) Mode Tracking over 100 Frames")
    plt.ylabel("Coefficient (meters)")
    plt.grid(True)
    plt.legend()
    
    plt.subplot(2, 1, 2)
    plt.plot(ground_truth[:100, 2], 'k-', label='Known Tilt (Z3) [Ground Truth]', alpha=0.8)
    plt.plot(generated_z[:100, 2], 'b--', label='Generated Tilt (Z3) [C-Engine Output]', alpha=0.8)
    plt.title("Tilt (Z3) Mode Tracking over 100 Frames")
    plt.xlabel("Frame Index")
    plt.ylabel("Coefficient (meters)")
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plot_path = os.path.join(BASE, 'data', 'comparisons', 'zernike_comparison.png')
    plt.savefig(plot_path, dpi=150)
    print(f"\nSaved tracking comparison plot to: {plot_path}")
    print("="*60)

if __name__ == '__main__':
    main()
