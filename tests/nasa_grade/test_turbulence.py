import pytest
import ctypes
import os
import numpy as np

@pytest.fixture(scope="session")
def shwfs_core():
    # Load the core shared library
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lib_path = os.path.join(project_root, "src", "core", "libshwfs.so")
    
    if not os.path.exists(lib_path):
        pytest.skip(f"libshwfs.so not found at {lib_path}, skipping turbulence tests.")
        
    lib = ctypes.CDLL(lib_path)
    
    # float estimate_fried_parameter(const float* zernike_variances, const float* noll_coefficients, int num_modes, float aperture_diameter)
    try:
        lib.estimate_fried_parameter.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_int, ctypes.c_float
        ]
        lib.estimate_fried_parameter.restype = ctypes.c_float

        # float estimate_coherence_time(const float* frame_variances, int num_samples, float frame_interval_ms)
        lib.estimate_coherence_time.argtypes = [
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            ctypes.c_int, ctypes.c_float
        ]
        lib.estimate_coherence_time.restype = ctypes.c_float
    except AttributeError:
        pytest.skip("Turbulence functions not exposed in libshwfs.so.")
        
    return lib

def test_fried_parameter_extreme_turbulence(shwfs_core):
    """
    Tests r0 estimation under extremely strong turbulence (very high variance).
    Expects a very small r0.
    """
    num_modes = 15
    aperture_diameter = 8.0 # 8 meter telescope
    
    # Huge variance
    zernike_variances = np.full(num_modes, 1000.0, dtype=np.float32)
    # Mock Noll coefficients
    noll_coefficients = np.array([0.0]*3 + [0.1]*(num_modes-3), dtype=np.float32)
    
    r0 = shwfs_core.estimate_fried_parameter(zernike_variances, noll_coefficients, num_modes, aperture_diameter)
    
    # With var=1000 and c_j=0.1, ratio = 10000. ratio^0.6 = 251. 8 / 251 = ~0.03m (3cm).
    assert r0 > 0.0, "Fried parameter cannot be zero or negative."
    assert r0 < 0.05, "Extreme turbulence should yield r0 < 5cm for this test case."

def test_fried_parameter_no_turbulence(shwfs_core):
    """
    Tests r0 estimation in perfect vacuum (zero variance).
    Should handle div by zero or return default.
    """
    num_modes = 15
    aperture_diameter = 8.0
    
    zernike_variances = np.zeros(num_modes, dtype=np.float32)
    noll_coefficients = np.array([0.0]*3 + [0.1]*(num_modes-3), dtype=np.float32)
    
    r0 = shwfs_core.estimate_fried_parameter(zernike_variances, noll_coefficients, num_modes, aperture_diameter)
    
    # The C function falls back to 0.1f if no valid modes are found (variance=0 -> valid=0)
    np.testing.assert_allclose(r0, 0.1, atol=1e-5, err_msg="Zero turbulence did not return the default r0.")
