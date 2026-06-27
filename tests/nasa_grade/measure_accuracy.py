import numpy as np
import ctypes
import os
import sys

def main():
    # Load C Engine
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

    from tests.nasa_grade.utils import generate_spot_field, generate_valid_mask
    
    n_sub = 1600   # 40x40 lenslet array
    sub_px = 24    # 24x24 pixels per sub-aperture
    valid_mask = generate_valid_mask(n_sub, geometry="square")
    
    print("=== Centroiding Accuracy (RMS Error in Pixels) ===")
    print(f"{'Photon Count':<15} | {'Noise Std':<10} | {'RMS Error (px)':<15}")
    print("-" * 45)
    
    # Ground truth center is (sub_px - 1) * 0.5
    true_center = (sub_px - 1.0) * 0.5
    
    test_cases = [
        (10000, 0.0),    # Ideal
        (5000, 1.0),     # Low noise
        (1000, 5.0),     # Medium noise
        (100, 10.0),     # High noise
        (50, 20.0),      # Extreme noise
    ]
    
    for photons, noise in test_cases:
        # Run 10 trials for statistical significance
        rms_errors = []
        for _ in range(10):
            img = generate_spot_field(n_sub=n_sub, sub_px=sub_px, photon_count=photons, noise_std=noise)
            slopes = np.zeros(n_sub * 2, dtype=np.float32)
            lib.compute_slopes_weighted(img, slopes, valid_mask, n_sub, n_sub, sub_px, 
                                        0.0, 0.0, 0.0, 1.0, 0.5)
            
            # calculate error against true center (which translates to 0 slope deviation if reference is 4.5)
            # Wait, our compute_slopes returns the absolute centroid if shift is 0.
            error = np.sqrt(np.mean((slopes - true_center)**2))
            rms_errors.append(error)
            
        print(f"{photons:<15} | {noise:<10.1f} | {np.mean(rms_errors):<15.4f}")

if __name__ == "__main__":
    main()
