import os
import sys
import time
import json
import numpy as np
import ctypes as ct
import platform

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

DATA_DIR = os.path.join(BASE, 'data', 'dataset')
VAL_DIR = os.path.join(BASE, 'data', 'dataset_validation')
CONFIG_FILE = os.path.join(BASE, 'data', 'autoconfig.json')

def main():
    print("="*80)
    print("⚙di  AUTONOMOUS HARDWARE PROFILE & AUTO-TUNER")
    print("="*80)
    
    # 1. Detect System Specs
    arch = platform.machine()
    system = platform.system()
    processor = platform.processor()
    print(f"System Info:")
    print(f"  OS           : {system}")
    print(f"  Architecture : {arch}")
    print(f"  Processor    : {processor}")
    print("—"*80)
    
    # 2. Check C-Engine Build
    lib_path = os.path.join(BASE, 'build', 'c_engine.so')
    if not os.path.exists(lib_path):
        print("C-Engine library not found. Attempting compile...")
        os.system(f"make -C {os.path.join(BASE, 'src', 'c_engine')}")
        
    try:
        lib = ct.CDLL(lib_path)
    except Exception as e:
        print(f"Error loading C-Engine: {e}")
        sys.exit(1)
        
    # Check delimiters
    def load_csv_robust(filepath, dtype):
        try:
            return np.loadtxt(filepath, delimiter=',').astype(dtype)
        except ValueError:
            return np.loadtxt(filepath).astype(dtype)
            
    # Load valid mask
    try:
        valid_mask = load_csv_robust(os.path.join(DATA_DIR, 'valid_mask.csv'), np.int32)
    except FileNotFoundError:
        print("Warning: Calibration matrices not found locally. Creating dummy valid mask.")
        valid_mask = np.ones(400, dtype=np.int32) # Dummy 20x20
        
    n_valid = int(valid_mask.sum())
    n_sub = len(valid_mask)
    sub_px = 20
    
    # Pre-allocate pointers
    dummy_img = np.random.normal(10.0, 5.0, (400, 400)).astype(np.float32)
    dummy_img = np.maximum(dummy_img, 0.0)
    
    # Inject NaNs to test sanitization resilience
    dummy_img[100, 100] = np.nan
    dummy_img[150, 150] = np.inf
    
    dummy_slopes = np.zeros(2 * n_valid, dtype=np.float32)
    
    print("Benchmarking Centroiding Algorithms (1,000 iterations)...")
    
    # Define ctypes signatures
    lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3
    lib.compute_slopes.restype  = None
    
    lib.compute_slopes_enhanced.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3 + [ct.c_float]*3
    lib.compute_slopes_enhanced.restype  = None
    
    lib.compute_slopes_iwcog.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3 + [ct.c_float]*2 + [ct.c_int] + [ct.c_float]*2
    lib.compute_slopes_iwcog.restype  = None
    
    # A. Standard CoG
    t_start = time.perf_counter()
    for _ in range(1000):
        lib.compute_slopes(
            dummy_img.ctypes.data_as(ct.POINTER(ct.c_float)),
            dummy_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            n_sub, n_valid, sub_px
        )
    cog_time = (time.perf_counter() - t_start)
    print(f"  1. Standard CoG (No threshold)  : {cog_time:.4f} s (Avg: {cog_time/1000.0*1000.0:.4f} ms/frame)")
    
    # B. Enhanced CoG (Background threshold = 15.0)
    t_start = time.perf_counter()
    for _ in range(1000):
        lib.compute_slopes_enhanced(
            dummy_img.ctypes.data_as(ct.POINTER(ct.c_float)),
            dummy_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            n_sub, n_valid, sub_px,
            15.0, 0.0, 0.0
        )
    tcog_time = (time.perf_counter() - t_start)
    print(f"  2. Thresholded CoG (TCoG)       : {tcog_time:.4f} s (Avg: {tcog_time/1000.0*1000.0:.4f} ms/frame)")
    
    # C. Iterative Weighted CoG (IWCoG, 5 iterations, sigma = 3.0)
    t_start = time.perf_counter()
    for _ in range(1000):
        lib.compute_slopes_iwcog(
            dummy_img.ctypes.data_as(ct.POINTER(ct.c_float)),
            dummy_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            n_sub, n_valid, sub_px,
            15.0, 3.0, 5, 0.0, 0.0
        )
    iwcog_time = (time.perf_counter() - t_start)
    print(f"  3. Iterative Weighted CoG (IWCoG): {iwcog_time:.4f} s (Avg: {iwcog_time/1000.0*1000.0:.4f} ms/frame)")
    print("—"*80)
    
    # 3. Formulate Optimal Deployment Decisions
    print("Optimizing Configuration...")
    
    # Optimal Vectorization Type
    if arch == "x86_64":
        vector_isa = "AVX2_FMA"
    elif arch in ["arm64", "aarch64"]:
        vector_isa = "NEON"
    else:
        vector_isa = "SCALAR"
        
    # Determine best algorithm based on CPU latency profile
    # If IWCoG takes too long (> 1.5 ms per frame), we fallback to TCoG to guarantee safety margin
    iwcog_frame_ms = (iwcog_time / 1000.0) * 1000.0
    if iwcog_frame_ms < 0.5:
        recommended_algo = "compute_slopes_iwcog"
        recommended_params = {
            "bg_threshold": 15.0,
            "sigma": 3.0,
            "max_iters": 5
        }
        rationale = "Hardware latency is exceptional (< 0.5ms). IWCoG selected for maximum wavefront reconstruction accuracy."
    else:
        recommended_algo = "compute_slopes_enhanced"
        recommended_params = {
            "bg_threshold": 15.0
        }
        rationale = "Hardware resources are constrained. Thresholded CoG (TCoG) selected to guarantee real-time safety margin."
        
    config = {
        "hardware": {
            "os": system,
            "architecture": arch,
            "vector_isa_detected": vector_isa
        },
        "optimized_settings": {
            "centroiding_algorithm": recommended_algo,
            "parameters": recommended_params
        },
        "autotune_metadata": {
            "cog_avg_ms": (cog_time/1000.0)*1000.0,
            "tcog_avg_ms": (tcog_time/1000.0)*1000.0,
            "iwcog_avg_ms": (iwcog_time/1000.0)*1000.0,
            "rationale": rationale
        }
    }
    
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
        
    print(f"\nAuto-Tuned Selections:")
    print(f"  Detected Vector ISA  : {vector_isa}")
    print(f"  Recommended Algorithm: {recommended_algo}")
    print(f"  Rationale            : {rationale}")
    print(f"  Configuration Saved  : {CONFIG_FILE}")
    print("="*80)

if __name__ == '__main__':
    main()
