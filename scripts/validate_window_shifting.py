"""
validate_window_shifting.py
---------------------------
Rigorous unit test verifying the dynamic subaperture integration window shifting
logic in the C-Engine slopes.c under large pixel shifts.
"""
import os
import ctypes as ct
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lib_path = os.path.join(BASE, 'build', 'c_engine.so')

def main():
    print("="*80)
    print("VALIDATING DYNAMIC INTEGRATION WINDOW SHIFTING IN C-ENGINE")
    print("="*80)

    # 1. Load C-Engine
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"C-Engine not found at {lib_path}")
    
    lib = ct.CDLL(lib_path)
    lib.compute_slopes_enhanced.argtypes = [
        ct.POINTER(ct.c_float), # img_data
        ct.POINTER(ct.c_float), # slopes
        ct.POINTER(ct.c_int),   # valid_mask
        ct.c_int,               # n_sub
        ct.c_int,               # n_valid
        ct.c_int,               # sub_px
        ct.c_float,             # bg_threshold
        ct.c_float,             # shift_x
        ct.c_float,             # shift_y
    ]
    lib.compute_slopes_enhanced.restype = None

    # Define simple geometry: 2x2 subapertures, sub_px = 20 (Image: 40x40)
    n_sub = 4
    n_valid = 4
    sub_px = 20
    valid_mask = np.ones(n_sub, dtype=np.int32)

    # Place a single bright Gaussian spot at subaperture 0 (nominal center is (9.5, 9.5))
    # We will simulate a physical camera shift of delta_x = 3.2, delta_y = -2.7 pixels.
    # Therefore, the spot is physically shifted to (9.5 + 3.2, 9.5 - 2.7) = (12.7, 6.8).
    img = np.zeros((40, 40), dtype=np.float32)
    
    # Subaperture 0 lies in col [0, 20], row [0, 20]
    true_x = 9.5 + 3.2
    true_y = 9.5 - 2.7
    
    # Generate Gaussian spot in the image
    for y in range(40):
        for x in range(40):
            dist_sq = (x - true_x)**2 + (y - true_y)**2
            img[y, x] = np.exp(-dist_sq / (2.0 * 1.5**2)) * 100.0

    # Output buffer for slopes
    slopes_no_corr = np.zeros(2 * n_valid, dtype=np.float32)
    slopes_corr = np.zeros(2 * n_valid, dtype=np.float32)

    # Case A: Compute slopes with shift_x = 0, shift_y = 0 (uncompensated)
    lib.compute_slopes_enhanced(
        img.ctypes.data_as(ct.POINTER(ct.c_float)),
        slopes_no_corr.ctypes.data_as(ct.POINTER(ct.c_float)),
        valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
        n_sub, n_valid, sub_px,
        0.0, 0.0, 0.0
    )

    # Case B: Compute slopes with shift_x = 3.2, shift_y = -2.7 (compensated)
    # The algorithm should shift the window by:
    #   offset_x = round(3.2) = 3
    #   offset_y = round(-2.7) = -3
    # The remaining fractional shift:
    #   frac_x = 3.2 - 3 = 0.2
    #   frac_y = -2.7 - (-3) = 0.3
    lib.compute_slopes_enhanced(
        img.ctypes.data_as(ct.POINTER(ct.c_float)),
        slopes_corr.ctypes.data_as(ct.POINTER(ct.c_float)),
        valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
        n_sub, n_valid, sub_px,
        0.0, 3.2, -2.7
    )

    print("Subaperture 0 measured centroids:")
    print(f"  Uncompensated : X = {slopes_no_corr[0]:.4f}, Y = {slopes_no_corr[n_valid]:.4f}")
    print(f"  Compensated   : X = {slopes_corr[0]:.4f}, Y = {slopes_corr[n_valid]:.4f}")
    print(f"  Expected target after calibration: X = 9.5000, Y = 9.5000")
    
    # Check if the corrected centroid matches the nominal center (9.5, 9.5) closely
    diff_x = abs(slopes_corr[0] - 9.5)
    diff_y = abs(slopes_corr[n_valid] - 9.5)
    print(f"  Absolute Errors: dX = {diff_x:.6f}, dY = {diff_y:.6f}")

    assert diff_x < 1e-3, f"Correction X error too high: {diff_x:.6f}"
    assert diff_y < 1e-3, f"Correction Y error too high: {diff_y:.6f}"
    
    print("\n>> Test Result: PASSED (Integration window dynamically shifted and corrected for subpixel alignment error)")
    print("="*80)

if __name__ == '__main__':
    main()
