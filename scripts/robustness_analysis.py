"""
robustness_analysis.py
----------------------
Rigorous, unbiased robustness analysis of the Project Radius C-Engine pipeline.
Simulates real-world conditions on the calibration dataset:
1. Photon Noise (varying average photons per subaperture)
2. Readout Noise (adding Gaussian noise to WFS pixels)
3. Calibration Drift / Misalignment (sub-pixel shifting of the WFS image)
"""
import os
import sys
import time
import numpy as np
import ctypes as ct
from PIL import Image
from scipy.ndimage import shift
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE, 'data', 'dataset')
BUILD_DIR = os.path.join(BASE, 'build')

def run_reconstruction(lib, frames, valid_mask, ref_slopes, g_plus, ground_truth, modifier_func=None):
    n_valid = int(valid_mask.sum())
    n_slopes = 2 * n_valid
    n_zernike = 20
    
    slopes_buf = np.zeros(n_slopes, dtype=np.float32)
    zernikes = np.zeros(n_zernike, dtype=np.float32)
    
    generated_z = np.zeros((len(frames), n_zernike), dtype=np.float32)
    
    for idx, fname in enumerate(frames):
        img = np.array(Image.open(os.path.join(DATA_DIR, fname))).astype(np.float32)
        
        if modifier_func:
            img = modifier_func(img)
            
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
        
    # Calculate Global Temporal R^2 (excluding piston, index 0)
    ss_r = sum(np.sum((generated_z[i, 1:] - ground_truth[i, 1:])**2) for i in range(len(frames)))
    ss_t = np.sum((ground_truth[:, 1:] - ground_truth[:, 1:].mean(axis=0))**2)
    r2_global = 1.0 - ss_r / ss_t if ss_t > 0 else 0.0
    
    # Calculate Average Per-Frame Spatial R^2
    r2_per_frame = []
    for i in range(len(frames)):
        ss_res_f = np.sum((generated_z[i, 1:] - ground_truth[i, 1:])**2)
        ss_tot_f = np.sum((ground_truth[i, 1:] - np.mean(ground_truth[i, 1:]))**2)
        r2_f = 1.0 - (ss_res_f / ss_tot_f) if ss_tot_f > 0 else 1.0
        r2_per_frame.append(r2_f)
        
    return r2_global * 100, np.mean(r2_per_frame) * 100

def main():
    print("="*80)
    print("PROJECT RADIUS: UNBIASED REAL-WORLD ROBUSTNESS ANALYSIS")
    print("="*80)
    
    # Load calibration matrices
    g_plus = np.loadtxt(os.path.join(DATA_DIR, 'g_plus.csv'), delimiter=',').astype(np.float32)
    valid_mask = np.loadtxt(os.path.join(DATA_DIR, 'valid_mask.csv'), delimiter=',').astype(np.int32)
    ref_slopes = np.loadtxt(os.path.join(DATA_DIR, 'ref_slopes.csv'), delimiter=',').astype(np.float32)
    ground_truth = np.loadtxt(os.path.join(DATA_DIR, 'ground_truth.csv'), delimiter=',').astype(np.float32)
    
    n_valid = int(valid_mask.sum())
    
    # Load C-Engine
    lib = ct.CDLL(os.path.join(BUILD_DIR, 'c_engine.so'))
    lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3
    lib.compute_slopes.restype  = None
    lib.reconstruct_zernikes.argtypes = [ct.POINTER(ct.c_float)]*3 + [ct.c_int]*2
    lib.reconstruct_zernikes.restype  = None
    
    frames = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.bmp')])
    
    # Baseline run (no noise)
    r2_g_base, r2_f_base = run_reconstruction(lib, frames, valid_mask, ref_slopes, g_plus, ground_truth)
    print(f"Baseline (No Noise) Accuracy:  Global Temporal R² = {r2_g_base:.4f}%, Avg Per-Frame R² = {r2_f_base:.4f}%")
    
    results = {}
    
    # -------------------------------------------------------------
    # Scenario A: Photon Noise (Shot Noise)
    # -------------------------------------------------------------
    print("\nEvaluating Scenario A: Photon Noise (Varying Guide Star Brightness)...")
    photon_levels = [100000, 10000, 1000, 500, 200]
    photon_results = []
    
    for photons in photon_levels:
        # Modifier function to apply photon noise
        def add_photon_noise(img):
            # Normalize image to have sum = photons * n_subapertures
            total_photons = photons * n_valid
            img_norm = img / img.sum() * total_photons
            noisy = np.random.poisson(img_norm).astype(np.float32)
            return noisy
            
        r2_g, r2_f = run_reconstruction(lib, frames, valid_mask, ref_slopes, g_plus, ground_truth, add_photon_noise)
        photon_results.append((photons, r2_g, r2_f))
        print(f"  Photons/Subap/Frame: {photons:<6d} | Global R²: {r2_g:6.2f}% | Avg Spatial R²: {r2_f:6.2f}%")
        
    results['photon'] = photon_results
    
    # -------------------------------------------------------------
    # Scenario B: Readout Noise (RON)
    # -------------------------------------------------------------
    print("\nEvaluating Scenario B: Readout Noise (At Faint Guide Star: 1000 photons/subap)...")
    ron_levels = [0.0, 1.0, 3.0, 5.0, 10.0]
    ron_results = []
    
    for ron in ron_levels:
        def add_photon_and_read_noise(img):
            # 1. Photon noise
            total_photons = 1000 * n_valid
            img_norm = img / img.sum() * total_photons
            noisy_photon = np.random.poisson(img_norm).astype(np.float32)
            # 2. Readout noise
            noisy_read = np.random.normal(0.0, ron, size=img.shape).astype(np.float32)
            # WFS pixels are non-negative
            final_img = np.clip(noisy_photon + noisy_read, 0.0, None)
            return final_img
            
        r2_g, r2_f = run_reconstruction(lib, frames, valid_mask, ref_slopes, g_plus, ground_truth, add_photon_and_read_noise)
        ron_results.append((ron, r2_g, r2_f))
        print(f"  Readout Noise (RON): {ron:<4.1f} e-  | Global R²: {r2_g:6.2f}% | Avg Spatial R²: {r2_f:6.2f}%")
        
    results['ron'] = ron_results
    
    # -------------------------------------------------------------
    # Scenario C: Alignment Shift (Calibration Drift)
    # -------------------------------------------------------------
    print("\nEvaluating Scenario C: Calibration Drift (WFS Image Alignment Shift)...")
    shift_levels = [0.0, 0.05, 0.1, 0.2, 0.5, 1.0] # in pixels
    shift_results = []
    
    for s in shift_levels:
        def shift_image(img):
            # Shift image in both X and Y directions
            return shift(img, [s, s], order=3, mode='constant', cval=0.0)
            
        r2_g, r2_f = run_reconstruction(lib, frames, valid_mask, ref_slopes, g_plus, ground_truth, shift_image)
        shift_results.append((s, r2_g, r2_f))
        print(f"  Pixel Shift (X & Y): {s:<4.2f} px  | Global R²: {r2_g:6.2f}% | Avg Spatial R²: {r2_f:6.2f}%")
        
    results['shift'] = shift_results
    
    # -------------------------------------------------------------
    # Generate Robustness Plot
    # -------------------------------------------------------------
    plt.figure(figsize=(15, 5))
    
    # Plot Photon Noise
    plt.subplot(1, 3, 1)
    p_levels = [r[0] for r in photon_results]
    p_r2_g = [r[1] for r in photon_results]
    p_r2_f = [r[2] for r in photon_results]
    plt.semilogx(p_levels, p_r2_g, 'o-', label='Global Temporal R²')
    plt.semilogx(p_levels, p_r2_f, 's-', label='Avg Spatial R²')
    plt.xlabel('Photons per Subaperture')
    plt.ylabel('R² Accuracy (%)')
    plt.title('Reconstruction vs. Photon Noise')
    plt.grid(True)
    plt.legend()
    
    # Plot Readout Noise
    plt.subplot(1, 3, 2)
    r_levels = [r[0] for r in ron_results]
    r_r2_g = [r[1] for r in ron_results]
    r_r2_f = [r[2] for r in ron_results]
    plt.plot(r_levels, r_r2_g, 'o-', label='Global Temporal R²')
    plt.plot(r_levels, r_r2_f, 's-', label='Avg Spatial R²')
    plt.xlabel('Readout Noise (e- RMS)')
    plt.ylabel('R² Accuracy (%)')
    plt.title('RON Degradation (at 1000 Photons)')
    plt.grid(True)
    plt.legend()
    
    # Plot Alignment Shift
    plt.subplot(1, 3, 3)
    s_levels = [r[0] for r in shift_results]
    s_r2_g = [r[1] for r in shift_results]
    s_r2_f = [r[2] for r in shift_results]
    plt.plot(s_levels, s_r2_g, 'o-', label='Global Temporal R²')
    plt.plot(s_levels, s_r2_f, 's-', label='Avg Spatial R²')
    plt.xlabel('Subaperture Shift (pixels)')
    plt.ylabel('R² Accuracy (%)')
    plt.title('Reconstruction vs. Alignment Drift')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plot_path = os.path.join(BASE, 'data', 'comparisons', 'robustness_analysis.png')
    plt.savefig(plot_path, dpi=150)
    print(f"\nSaved robustness analysis plots to: {plot_path}")
    print("="*80)

if __name__ == '__main__':
    main()
