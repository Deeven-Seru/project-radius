import os
import sys
import time
import ctypes
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

CAL_DATA_DIR = os.path.join(BASE, 'data', 'dataset')
VAL_DATA_DIR = os.path.join(BASE, 'data', 'dataset_validation')

def load_csv_robust(filepath, dtype):
    try:
        return np.loadtxt(filepath, delimiter=',').astype(dtype)
    except ValueError:
        return np.loadtxt(filepath).astype(dtype)

def main():
    print("="*80)
    print("VERIFYING C-ENGINE IMPLEMENTATION OF Z-DKF")
    print("="*80)
    
    # 1. Load Datasets
    gt_train = load_csv_robust(os.path.join(CAL_DATA_DIR, 'ground_truth.csv'), np.float32)
    gt_val   = load_csv_robust(os.path.join(VAL_DATA_DIR, 'ground_truth.csv'), np.float32)
    
    np.random.seed(42)
    noise_std = 2e-8
    noisy_inputs = (gt_val + np.random.normal(0, noise_std, gt_val.shape)).astype(np.float32)
    
    n_frames, n_zernike = gt_val.shape
    
    # 2. System Identification (AR1 coefficients)
    a_coeffs = np.zeros(n_zernike, dtype=np.float32)
    w_vars   = np.zeros(n_zernike, dtype=np.float32)
    v_vars   = np.ones(n_zernike, dtype=np.float32) * (noise_std**2)
    
    for j in range(n_zernike):
        z_col = gt_train[:, j]
        var_z = np.var(z_col)
        if var_z > 1e-25:
            cov_matrix = np.cov(z_col[1:], z_col[:-1])
            a = cov_matrix[0, 1] / cov_matrix[0, 0]
            a = np.clip(a, 0.5, 0.999)
            w_var = var_z * (1.0 - a**2)
        else:
            a = 0.0 # piston or inactive
            w_var = 0.0
            v_vars[j] = 0.0 # marks it as inactive to skip in C
        a_coeffs[j] = a
        w_vars[j] = w_var
        
    # 3. Load C-Engine and define types
    lib_path = os.path.join(BASE, 'build', 'c_engine.so')
    lib = ctypes.CDLL(lib_path)
    
    lib.apply_kalman_filter.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # zernikes_in
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # zernikes_out
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # predicted_zernikes
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # a_coeffs
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # w_vars
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # v_vars
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # x_est
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'), # P
        ctypes.c_int # n_zernike
    ]
    lib.apply_kalman_filter.restype = None
    
    # 4. Allocate buffers
    x_est = np.zeros(n_zernike, dtype=np.float32)
    P = np.ones(n_zernike, dtype=np.float32) * 1e-15
    
    filtered_c = np.zeros_like(noisy_inputs)
    predicted_c = np.zeros_like(noisy_inputs)
    
    # Run the C-Engine Kalman Filter
    t0 = time.perf_counter()
    for t in range(n_frames):
        lib.apply_kalman_filter(
            noisy_inputs[t],
            filtered_c[t],
            predicted_c[t],
            a_coeffs,
            w_vars,
            v_vars,
            x_est,
            P,
            ctypes.c_int(n_zernike)
        )
    t1 = time.perf_counter()
    c_time = (t1 - t0) * 1000.0
    
    # 5. Run Python reference model for exact comparison
    x_est_py = np.zeros(n_zernike, dtype=np.float32)
    P_py = np.ones(n_zernike, dtype=np.float32) * 1e-15
    filtered_py = np.zeros_like(noisy_inputs)
    predicted_py = np.zeros_like(noisy_inputs)
    
    for t in range(n_frames):
        for j in range(n_zernike):
            if v_vars[j] < 1e-25:
                filtered_py[t, j] = noisy_inputs[t, j]
                predicted_py[t, j] = noisy_inputs[t, j]
                continue
            x_pred = a_coeffs[j] * x_est_py[j]
            P_pred = (a_coeffs[j]**2) * P_py[j] + w_vars[j]
            K = P_pred / (P_pred + v_vars[j])
            x_est_py[j] = x_pred + K * (noisy_inputs[t, j] - x_pred)
            P_py[j] = (1.0 - K) * P_pred
            filtered_py[t, j] = x_est_py[j]
            predicted_py[t, j] = a_coeffs[j] * x_est_py[j]
            
    # 6. Verify outputs match
    diff_filt = np.max(np.abs(filtered_c - filtered_py))
    diff_pred = np.max(np.abs(predicted_c - predicted_py))
    
    print("\n" + "="*80)
    print("VERIFICATION RESULTS")
    print("="*80)
    print(f"C-Engine Kalman execution time   : {c_time:.4f} ms")
    print(f"Average latency per frame        : {c_time/n_frames*1000.0:.4f} microseconds")
    print(f"Max difference on Filtered states: {diff_filt:.8e} m")
    print(f"Max difference on Pred states    : {diff_pred:.8e} m")
    
    if diff_filt < 1e-7 and diff_pred < 1e-7:
        print("STATUS: VERIFIED SUCCESSFUL (C-Engine exactly matches Python reference)")
    else:
        print("STATUS: ERROR (Numerical discrepancy detected)")
    print("="*80)

if __name__ == '__main__':
    main()
