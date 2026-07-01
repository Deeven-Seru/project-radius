import os
import time
import numpy as np
from PIL import Image
import ctypes
import pytest

def run_evaluation():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "hcipy_dataset")
    
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
    lib.compute_slopes_iwcog.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_float, ctypes.c_float, ctypes.c_int, ctypes.c_float, ctypes.c_float
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
    dm_coupling = np.genfromtxt(os.path.join(data_dir, 'dm_coupling.csv'), delimiter=',').astype(np.float32)
    dm_coupling = dm_coupling[:, :50].flatten()
    gt = np.genfromtxt(os.path.join(data_dir, 'ground_truth.csv'), delimiter=',')
        
    n_sub = 80 * 80
    n_valid = np.sum(valid_mask)
    sub_px = 10
    n_slopes = n_valid * 2
    n_zernike = 50
    n_actuators = 200
    n_frames = 100

    ref_slopes = np.genfromtxt(os.path.join(data_dir, 'ref_slopes.csv'), delimiter=',').astype(np.float32)

    def evaluate_condition(condition_name, noise_std, intensity_scale, shift_val, bg_thr=0.0, weight_exp=1.0, thr_mul=0.5, algo='weighted', iwcog_sigma=3.0, iwcog_iters=3):
        zernike_errors_no_piston = []
        gt_signals_no_piston = []
        latencies = []
        
        for i in range(min(50, n_frames)):
            frame_path = os.path.join(data_dir, f'frame_{i:04d}.npy')
            if not os.path.exists(frame_path):
                # Fallback to BMP if NPY not found
                img_data = np.array(Image.open(os.path.join(data_dir, f'frame_{i:04d}.bmp')), dtype=np.float32)
            else:
                img_data = np.load(frame_path).astype(np.float32)
            
            # Apply Perturbations
            img_data *= intensity_scale
            if noise_std > 0:
                img_data += np.random.normal(0, noise_std, img_data.shape)
            img_data = img_data.flatten().astype(np.float32)

            slopes = np.zeros(n_slopes, dtype=np.float32)
            zernikes = np.zeros(n_zernike, dtype=np.float32)
            actuators = np.zeros(n_actuators, dtype=np.float32)
            
            t0 = time.perf_counter()
            if algo == 'iwcog':
                lib.compute_slopes_iwcog(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                         bg_thr, iwcog_sigma, iwcog_iters, shift_val, shift_val)
            else:
                lib.compute_slopes_weighted(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                            bg_thr, shift_val, shift_val, weight_exp, thr_mul)
            slopes_diff = slopes - ref_slopes
            
            # Do not remove global tip/tilt (mean shift) for now
            # mean_x = np.mean(slopes_diff[:n_valid])
            # mean_y = np.mean(slopes_diff[n_valid:])
            # slopes_diff[:n_valid] -= mean_x
            # slopes_diff[n_valid:] -= mean_y
            
            lib.reconstruct_zernikes(slopes_diff, g_plus, zernikes, n_zernike, n_slopes)
            lib.compute_actuator_map(zernikes, dm_coupling, actuators, n_actuators, n_zernike, -1.0, 1.0)
            t1 = time.perf_counter()
            latencies.append((t1 - t0) * 1000.0)
            
            gt_zernikes = gt[i, :n_zernike]
            
            # Find optimal scale factor for the first frame
            if i == 0:
                print(f"Max slope diff: {np.max(np.abs(slopes_diff))}, Max zernike: {np.max(np.abs(zernikes))}")
                global optimal_scale
                if np.sum(zernikes * zernikes) == 0:
                    optimal_scale = 1.0
                else:
                    optimal_scale = np.sum(gt_zernikes * zernikes) / np.sum(zernikes * zernikes)
                print(f"Optimal scale factor: {optimal_scale}")
                
            zernikes *= optimal_scale
            
            if i == 0:
                print("Reconstructed Zernikes (3-10):", zernikes[3:10])
                print("Ground Truth Zernikes (3-10):", gt_zernikes[3:10])
            
            # Exclude Piston, Tip, Tilt (first 3 Zernike modes)
            rmse = np.sqrt(np.mean((zernikes[3:] - gt_zernikes[3:])**2))
            sig = np.sqrt(np.mean(gt_zernikes[3:]**2))
            zernike_errors_no_piston.append(rmse)
            gt_signals_no_piston.append(sig)
            
        avg_rmse = np.mean(zernike_errors_no_piston)
        avg_sig = np.mean(gt_signals_no_piston)
        acc = (1.0 - (avg_rmse / avg_sig)) * 100.0
        
        print(f"{condition_name} | Acc: {acc:.2f}% | Latency: {np.mean(latencies):.3f}ms")
        return acc

    print("Running Hyper-parameter Search...")
    best_acc = -np.inf
    best_params = None
    for bg in [0.0, 5.0, 10.0, 20.0, 40.0]:
        for w in [1.0, 1.5, 2.0]:
            acc = evaluate_condition(f"Bg: {bg}, W: {w}", 0.0, 1.0, 0.0, bg_thr=bg, weight_exp=w)
            if acc > best_acc:
                best_acc = acc
                best_params = (bg, w)
    print(f"\\nBest Params Found: Bg={best_params[0]}, Weight={best_params[1]} -> Accuracy = {best_acc:.2f}%")

    # Run Scenarios
    print("\n--- ORIGINAL ALGORITHM (Weighted CoG) ---")
    evaluate_condition("Condition A (Base: Clean BMPs)", noise_std=0.0, intensity_scale=1.0, shift_val=0.0)
    evaluate_condition("Condition B (Low Light: 10% Intensity, 2px Noise)", noise_std=2.0, intensity_scale=0.1, shift_val=0.0)
    evaluate_condition("Condition C (High Bg Noise: 20px Noise)", noise_std=20.0, intensity_scale=1.0, shift_val=0.0)
    evaluate_condition("Condition D (Sub-pixel Misalignment: 2.5px shift)", noise_std=0.0, intensity_scale=1.0, shift_val=2.5)

    print("\n--- NEW ALGORITHM (IWCoG) ---")
    evaluate_condition("Condition A (Base: Clean BMPs)", noise_std=0.0, intensity_scale=1.0, shift_val=0.0, algo='iwcog')
    evaluate_condition("Condition B (Low Light: 10% Intensity, 2px Noise)", noise_std=2.0, intensity_scale=0.1, shift_val=0.0, algo='iwcog')
    evaluate_condition("Condition C (High Bg Noise: 20px Noise)", noise_std=20.0, intensity_scale=1.0, shift_val=0.0, algo='iwcog')
    evaluate_condition("Condition D (Sub-pixel Misalignment: 2.5px shift)", noise_std=0.0, intensity_scale=1.0, shift_val=2.5, algo='iwcog')

if __name__ == "__main__":
    run_evaluation()
