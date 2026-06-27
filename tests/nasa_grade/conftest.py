import pytest
import ctypes
import os
import numpy as np

@pytest.fixture(scope="session")
def c_engine():
    # Load the shared library
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    lib_path = os.path.join(project_root, "build", "c_engine.so")
    
    if not os.path.exists(lib_path):
        # Fallback to root if not in build
        lib_path = os.path.join(project_root, "c_engine.so")
        
    if not os.path.exists(lib_path):
        pytest.fail(f"Could not find c_engine.so at {lib_path}")
        
    lib = ctypes.CDLL(lib_path)

    # void compute_slopes(const float *img_data, float *slopes, const int *valid_mask, int n_sub, int n_valid, int sub_px)
    lib.compute_slopes.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_int
    ]
    lib.compute_slopes.restype = None

    # void compute_slopes_weighted(const float *img_data, float *slopes, const int *valid_mask, int n_sub, int n_valid, int sub_px, float bg_threshold, float shift_x, float shift_y, float weight_exp, float thr_mul)
    lib.compute_slopes_weighted.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float
    ]
    lib.compute_slopes_weighted.restype = None
    
    # void compute_slopes_enhanced(const float *img_data, float *slopes, const int *valid_mask, int n_sub, int n_valid, int sub_px, float bg_threshold, float shift_x, float shift_y)
    lib.compute_slopes_enhanced.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_float, ctypes.c_float, ctypes.c_float
    ]
    lib.compute_slopes_enhanced.restype = None

    # void reconstruct_zernikes(const float *slopes, const float *G_plus, float *zernikes, int n_zernike, int n_slopes)
    lib.reconstruct_zernikes.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int
    ]
    lib.reconstruct_zernikes.restype = None

    # void compute_actuator_map(const float *zernikes, const float *C_DM, float *actuators, int n_actuators, int n_zernike)
    lib.compute_actuator_map.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float
    ]
    lib.compute_actuator_map.restype = None

    return lib
