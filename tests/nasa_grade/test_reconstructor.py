import pytest
import numpy as np

def test_mvm_reconstructor_extreme_aberrations(c_engine):
    """
    Tests Matrix-Vector Multiplication for wavefront reconstruction with physically impossible, 
    extreme aberration slopes to ensure no numerical overflow or crash occurs.
    """
    n_slopes = 1024 # 512 subapertures * 2
    n_zernike = 64
    
    # Generate extreme slopes (e.g. 10^6 deviation, which is physically impossible but stress-tests the float limit)
    slopes = np.full(n_slopes, 1e6, dtype=np.float32)
    G_plus = np.random.uniform(-1.0, 1.0, (n_zernike, n_slopes)).astype(np.float32)
    zernikes = np.zeros(n_zernike, dtype=np.float32)
    
    # Flatten G_plus for the C API which expects a 1D contiguous array
    G_plus_flat = G_plus.flatten()
    
    c_engine.reconstruct_zernikes(slopes, G_plus_flat, zernikes, n_zernike, n_slopes)
    
    # Ensure no NaN or Inf propagates
    assert not np.any(np.isnan(zernikes)), "NaN detected in extreme aberration reconstruction."
    assert not np.any(np.isinf(zernikes)), "Infinity detected in extreme aberration reconstruction."

def test_mvm_reconstructor_zero_slopes(c_engine):
    """
    Tests reconstructor with perfectly zeroed slopes (ideal flat wavefront).
    Zernike coefficients should be exactly zero.
    """
    n_slopes = 1024
    n_zernike = 64
    
    slopes = np.zeros(n_slopes, dtype=np.float32)
    G_plus = np.random.uniform(-1.0, 1.0, (n_zernike, n_slopes)).astype(np.float32)
    zernikes = np.ones(n_zernike, dtype=np.float32) * 999.0 # Initialize with garbage
    
    G_plus_flat = G_plus.flatten()
    
    c_engine.reconstruct_zernikes(slopes, G_plus_flat, zernikes, n_zernike, n_slopes)
    
    np.testing.assert_allclose(zernikes, 0.0, atol=1e-7, err_msg="Zero slope input did not yield zero Zernike coefficients.")

def test_actuator_map_near_singular_matrix(c_engine):
    """
    Tests compute_actuator_map coupling matrix inversion robustness. 
    While the C code just does MVM (since inversion is offline), we test if 
    extreme values from an ill-conditioned inverse matrix crash the AVX logic.
    """
    n_zernike = 64
    n_actuators = 144
    
    # Simulate an ill-conditioned inverse coupling matrix with huge condition number
    # i.e., very large float values
    C_DM = np.full((n_actuators, n_zernike), 1e10, dtype=np.float32)
    C_DM_flat = C_DM.flatten()
    
    zernikes = np.ones(n_zernike, dtype=np.float32)
    actuators = np.zeros(n_actuators, dtype=np.float32)
    
    c_engine.compute_actuator_map(zernikes, C_DM_flat, actuators, n_actuators, n_zernike, -1.0, 1.0)
    
    assert not np.any(np.isnan(actuators)), "NaN detected in actuator mapping."
    assert np.all(actuators == 1.0), "Actuator values did not clip correctly to 1.0."
