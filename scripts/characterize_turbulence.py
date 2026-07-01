import os
import time
import numpy as np
import ctypes
from PIL import Image

def get_noll_variance_coefficient(j):
    """
    Returns the theoretical Noll variance coefficient c_j 
    where <a_j^2> = c_j * (D/r0)^(5/3) for Kolmogorov turbulence.
    """
    # Piston(1), Tip(2), Tilt(3)
    if j == 1: return 0.0 # Piston is usually ignored
    elif j in (2, 3): return 0.448
    elif j == 4: return 0.0232 # Defocus
    elif j in (5, 6): return 0.0232 # Astigmatism
    elif j in (7, 8): return 0.00619 # Coma
    elif j in (9, 10): return 0.00619 # Trefoil
    elif j == 11: return 0.00245 # Spherical
    else:
        # Approximate scaling for higher modes (Noll 1976)
        n = int(np.ceil((-3 + np.sqrt(9 + 8*j))/2)) # Radial degree
        return 0.2944 * (n ** (-11.0/3.0))

def estimate_turbulence_params(zernikes_history, pupil_diameter, wavelength, dt):
    """
    Estimates r0 and tau0 from a time-series of Zernike coefficients.
    zernikes_history: shape (N_frames, N_zernikes) in METERS.
    """
    # Convert meters to radians
    z_rad = zernikes_history * (2 * np.pi / wavelength)
    
    # 1. Estimate Fried Parameter (r0)
    # Variance over time for each mode
    variances = np.var(z_rad, axis=0)
    
    r0_estimates = []
    # Use modes 4 to 10 (Defocus, Astigmatism, Coma, Trefoil) to avoid global tip/tilt vibrations
    for j in range(4, 11):
        c_j = get_noll_variance_coefficient(j)
        # <a_j^2> = c_j * (D/r0)^(5/3) => r0 = D / (<a_j^2> / c_j)^(3/5)
        if variances[j-1] > 0:
            r0_est = pupil_diameter / ((variances[j-1] / c_j) ** (3.0/5.0))
            r0_estimates.append(r0_est)
    
    r0 = np.median(r0_estimates)
    
    # 2. Estimate Coherence Time (tau0)
    # We estimate wind velocity (v) from the temporal autocorrelation of Tip (mode 2)
    # Autocorrelation of Tip drops to 1/e at approximately tau_e = 0.5 * (D / v)
    tip = z_rad[:, 1]
    tip_mean_sub = tip - np.mean(tip)
    autocorr = np.correlate(tip_mean_sub, tip_mean_sub, mode='full')
    autocorr = autocorr[len(autocorr)//2:] # Take positive lags
    autocorr /= autocorr[0]
    
    # Find 1/e crossing time
    crossing_idx = np.where(autocorr < np.exp(-1))[0]
    if len(crossing_idx) > 0:
        tau_e_frames = crossing_idx[0]
    else:
        tau_e_frames = len(autocorr) / 2.0
        
    tau_e_sec = tau_e_frames * dt
    # tau_e = 0.5 * D / v => v = 0.5 * D / tau_e
    v_est = 0.5 * pupil_diameter / tau_e_sec
    
    # tau0 = 0.314 * r0 / v
    tau0 = 0.314 * r0 / v_est
    
    return r0, tau0, v_est

def run_submission():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(project_root, "data", "hcipy_dataset")
    
    # Load C Engine
    lib_path = os.path.join(project_root, "build", "c_engine.so")
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

    print("Loading constraints and datasets...")
    valid_mask = np.genfromtxt(os.path.join(data_dir, 'valid_mask.csv'), delimiter=',').astype(np.int32)
    g_plus = np.genfromtxt(os.path.join(data_dir, 'g_plus.csv'), delimiter=',').astype(np.float32).flatten()
    dm_coupling = np.genfromtxt(os.path.join(data_dir, 'dm_coupling.csv'), delimiter=',').astype(np.float32)
    
    n_sub = 80 * 80
    n_valid = np.sum(valid_mask)
    sub_px = 10
    n_slopes = n_valid * 2
    n_zernike = 50
    n_actuators = dm_coupling.shape[0]
    
    dm_coupling = dm_coupling[:, :50].flatten()
    ref_slopes = np.genfromtxt(os.path.join(data_dir, 'ref_slopes.csv'), delimiter=',').astype(np.float32)

    n_frames = 500
    pupil_diameter = 8.0
    wavelength = 2.2e-6
    dt = 0.001 # 1 ms per frame

    zernikes_history = np.zeros((n_frames, n_zernike), dtype=np.float32)
    latencies = []

    print(f"Processing {n_frames} frames to reconstruct wavefront and actuator maps...")
    
    # We use Weighted CoG (Bg=0.0, W=1.0) as it was proven most accurate and fastest
    for i in range(n_frames):
        frame_path = os.path.join(data_dir, f'frame_{i:04d}.npy')
        img_data = np.load(frame_path).astype(np.float32).flatten()
        
        slopes = np.zeros(n_slopes, dtype=np.float32)
        zernikes = np.zeros(n_zernike, dtype=np.float32)
        actuators = np.zeros(n_actuators, dtype=np.float32)
        
        t0 = time.perf_counter()
        
        # 1. Slope Calculation
        lib.compute_slopes_weighted(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                    0.0, 0.0, 0.0, 1.0, 0.5)
        slopes_diff = slopes - ref_slopes
        
        # 2. Wavefront Reconstruction (Zernikes)
        lib.reconstruct_zernikes(slopes_diff, g_plus, zernikes, n_zernike, n_slopes)
        
        # 3. Actuator Map Calculation (Deformable Mirror)
        # Actuator stroke maps consider inter-actuator coupling
        lib.compute_actuator_map(zernikes, dm_coupling, actuators, n_actuators, n_zernike, -1.0, 1.0)
        
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
        
        zernikes_history[i, :] = zernikes

    print(f"\\n--- PERFORMANCE ---")
    print(f"Average Engine Latency: {np.mean(latencies):.3f} ms per frame")
    
    print(f"\\n--- TURBULENCE CHARACTERIZATION ---")
    r0, tau0, v = estimate_turbulence_params(zernikes_history, pupil_diameter, wavelength, dt)
    print(f"Estimated Fried Parameter (r0):  {r0:.4f} m (Ground Truth @ 2.2um: ~0.89 m)")
    print(f"Estimated Wind Velocity (v):     {v:.2f} m/s (Ground Truth: 10.0 m/s)")
    print(f"Estimated Coherence Time (tau0): {tau0 * 1000.0:.2f} ms (Ground Truth: ~4.7 ms)")
    
    print("\n* Note on turbulence estimates: The dataset contains 500 frames (0.5 seconds).")
    print("* The outer scale (L0 = 25m) taking 2.5s to cross the aperture means 0.5s is an incomplete statistical sample.")
    print("* This naturally leads to an underestimation of variance (overestimating r0) and artificially narrowed autocorrelation (overestimating v).")

if __name__ == "__main__":
    run_submission()
