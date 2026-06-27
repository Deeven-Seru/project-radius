import os
import time
import numpy as np
from PIL import Image
import ctypes
from tests.nasa_grade.conftest import c_engine
import pytest

def run_evaluation():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "dataset")
    
    # 1. Load C Engine manually since this is a standalone script
    lib_path = os.path.join(project_root, "build", "c_engine.so")
    if not os.path.exists(lib_path):
        lib_path = os.path.join(project_root, "c_engine.so")
    lib = ctypes.CDLL(lib_path)
    
    lib.compute_slopes_weighted.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float
    ]
    lib.reconstruct_zernikes.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int
    ]
    lib.compute_actuator_map.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float
    ]

    # 2. Load Matrices
    print("Loading datasets...")
    valid_mask = np.genfromtxt(os.path.join(data_dir, 'valid_mask.csv'), delimiter=',').astype(np.int32)
    g_plus = np.genfromtxt(os.path.join(data_dir, 'g_plus.csv'), delimiter=',').astype(np.float32).flatten()
    dm_coupling = np.genfromtxt(os.path.join(data_dir, 'dm_coupling.csv'), delimiter=',').astype(np.float32).flatten()
    gt = np.genfromtxt(os.path.join(data_dir, 'ground_truth.csv'), delimiter=',')
    try:
        ref_slopes = np.genfromtxt(os.path.join(data_dir, 'ref_slopes.csv'), delimiter=',').astype(np.float32)
    except OSError:
        ref_slopes = np.zeros(632, dtype=np.float32)
        
    n_sub = 400
    n_valid = 316
    sub_px = 20
    n_slopes = 632
    n_zernike = 55
    n_actuators = 357
    n_frames = 500

    def evaluate_condition(condition_name, noise_std, intensity_scale, shift_val, bg_thr=0.0, weight_exp=1.0, thr_mul=0.5):
        zernike_errors_no_piston = []
        gt_signals_no_piston = []
        latencies = []
        
        for i in range(min(50, n_frames)):  # Run on 50 frames for fast search
            frame_path = os.path.join(data_dir, f"frame_{i:04d}.bmp")
            if not os.path.exists(frame_path):
                break
                
            img = Image.open(frame_path).convert('L')
            img_data = np.array(img, dtype=np.float32)
            
            # Apply Perturbations
            img_data *= intensity_scale
            if noise_std > 0:
                img_data += np.random.normal(0, noise_std, img_data.shape)
            img_data = img_data.flatten().astype(np.float32)

            slopes = np.zeros(n_slopes, dtype=np.float32)
            zernikes = np.zeros(n_zernike, dtype=np.float32)
            actuators = np.zeros(n_actuators, dtype=np.float32)
            
            t0 = time.perf_counter()
            lib.compute_slopes_weighted(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                        bg_thr, shift_val, shift_val, weight_exp, thr_mul)
            slopes_diff = slopes - ref_slopes
            lib.reconstruct_zernikes(slopes_diff, g_plus, zernikes, n_zernike, n_slopes)
            lib.compute_actuator_map(zernikes, dm_coupling, actuators, n_actuators, n_zernike, -1.0, 1.0)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
            
            gt_zernikes = gt[i]
            # Exclude Piston
            rmse = np.sqrt(np.mean((zernikes[1:] - gt_zernikes[1:])**2))
            sig = np.sqrt(np.mean(gt_zernikes[1:]**2))
            zernike_errors_no_piston.append(rmse)
            gt_signals_no_piston.append(sig)
            
        avg_rmse = np.mean(zernike_errors_no_piston)
        avg_sig = np.mean(gt_signals_no_piston)
        acc = (1.0 - (avg_rmse / avg_sig)) * 100.0
        
        print(f"{condition_name} | Acc: {acc:.2f}% | Latency: {np.mean(latencies):.3f}ms")
        return acc

    print("Running Hyper-parameter Search...")
    best_acc = 0
    best_params = None
    for bg in [0.0, 5.0, 10.0, 20.0, 40.0]:
        for w in [1.0, 1.5, 2.0]:
            acc = evaluate_condition(f"Bg: {bg}, W: {w}", 0.0, 1.0, 0.0, bg_thr=bg, weight_exp=w)
            if acc > best_acc:
                best_acc = acc
                best_params = (bg, w)
    print(f"\\nBest Params Found: Bg={best_params[0]}, Weight={best_params[1]} -> Accuracy = {best_acc:.2f}%")

    # Run Scenarios
    evaluate_condition("Condition A (Base: Clean BMPs)", noise_std=0.0, intensity_scale=1.0, shift_val=0.0)
    evaluate_condition("Condition B (Low Light: 10% Intensity, 2px Noise)", noise_std=2.0, intensity_scale=0.1, shift_val=0.0)
    evaluate_condition("Condition C (High Bg Noise: 20px Noise)", noise_std=20.0, intensity_scale=1.0, shift_val=0.0)
    evaluate_condition("Condition D (Sub-pixel Misalignment: 2.5px shift)", noise_std=0.0, intensity_scale=1.0, shift_val=2.5)

if __name__ == "__main__":
    run_evaluation()
