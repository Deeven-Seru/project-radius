import pytest
import numpy as np
from tests.nasa_grade.utils import generate_spot_field, generate_valid_mask

def test_centroiding_zero_photons(c_engine):
    """
    Simulates absolute darkness (zero photons, zero read noise).
    Expects centroids to fall back to the exact center of the sub-aperture.
    """
    n_sub = 16
    sub_px = 10
    n_valid = n_sub
    
    img_data = generate_spot_field(n_sub=n_sub, sub_px=sub_px, photon_count=0, noise_std=0.0)
    valid_mask = generate_valid_mask(n_sub, geometry="square")
    slopes = np.zeros(n_valid * 2, dtype=np.float32)
    
    c_engine.compute_slopes(img_data, slopes, valid_mask, n_sub, n_valid, sub_px)
    
    # Expected fallback is (sub_px - 1) * 0.5 = 4.5
    expected_fallback = (sub_px - 1.0) * 0.5
    np.testing.assert_allclose(slopes, expected_fallback, err_msg="Zero photon test failed: centroids should fallback to geometric center.")

def test_centroiding_saturation(c_engine):
    """
    Simulates saturated pixels (all pixels at 255) to test overflow / denominator stability.
    """
    n_sub = 16
    sub_px = 10
    n_valid = n_sub
    
    img_data = np.full(n_sub * sub_px * sub_px, 255.0, dtype=np.float32)
    valid_mask = generate_valid_mask(n_sub, geometry="square")
    slopes = np.zeros(n_valid * 2, dtype=np.float32)
    
    c_engine.compute_slopes(img_data, slopes, valid_mask, n_sub, n_valid, sub_px)
    
    # For a uniform saturated block, the CoG is exactly the center
    expected_fallback = (sub_px - 1.0) * 0.5
    np.testing.assert_allclose(slopes, expected_fallback, atol=1e-5, err_msg="Saturation test failed.")

def test_centroiding_extreme_noise(c_engine):
    """
    Tests compute_slopes_weighted under extremely low SNR.
    Weighted centroiding should reject heavy background noise.
    """
    n_sub = 16
    sub_px = 10
    n_valid = n_sub
    
    # Very high noise (SNR ~ 1)
    img_data = generate_spot_field(n_sub=n_sub, sub_px=sub_px, photon_count=100, noise_std=100.0)
    valid_mask = generate_valid_mask(n_sub, geometry="square")
    slopes = np.zeros(n_valid * 2, dtype=np.float32)
    
    # Provide background thresholding parameters
    bg_threshold = 0.0
    shift_x = 0.0
    shift_y = 0.0
    weight_exp = 2.0  # Square the intensity to heavily penalize noise
    thr_mul = 1.0     # Threshold at mean + 1 std
    
    c_engine.compute_slopes_weighted(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                     bg_threshold, shift_x, shift_y, weight_exp, thr_mul)
    
    # While it will be noisy, it shouldn't produce completely divergent slopes (e.g., NaN or way outside sub_px)
    assert not np.any(np.isnan(slopes)), "Slopes contain NaN under extreme noise."
    assert np.all(slopes >= -sub_px) and np.all(slopes <= sub_px), "Slopes bounded out of physically possible bounds."

def test_centroiding_subpixel_shift_tolerance(c_engine):
    """
    Verifies that compute_slopes_enhanced properly compensates for global alignment drift.
    """
    n_sub = 16
    sub_px = 10
    n_valid = n_sub
    
    # Shift spot by exactly 2.5 pixels
    shift_val = 2.5
    img_data = generate_spot_field(n_sub=n_sub, sub_px=sub_px, photon_count=10000, noise_std=0.0, shift_x=shift_val, shift_y=shift_val)
    valid_mask = generate_valid_mask(n_sub, geometry="square")
    slopes = np.zeros(n_valid * 2, dtype=np.float32)
    
    bg_threshold = 0.0
    
    c_engine.compute_slopes_enhanced(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                     bg_threshold, shift_val, shift_val)
                                     
    # If the sub-aperture center is (4.5), and we physically shifted the spot by +2.5, 
    # the uncompensated CoG is 7.0. But the enhanced function subtracts shift_val.
    # Therefore, the output slopes should report ~4.5 (which acts as a 0 deviation if 4.5 is the reference).
    expected_fallback = (sub_px - 1.0) * 0.5
    np.testing.assert_allclose(slopes, expected_fallback, atol=0.2, err_msg="Subpixel shift tolerance failed.")
