import os
import time
import numpy as np
import ctypes

def generate_valid_mask(n_sub, geometry="square"):
    mask = np.ones(n_sub, dtype=np.int32)
    return mask

def generate_spot_field(n_sub, sub_px, bg_noise_std=0.0, photon_count=1000, 
                        shift_x=0.0, shift_y=0.0, true_center=4.5):
    N_1d = int(np.sqrt(n_sub))
    y, x = np.mgrid[0:sub_px, 0:sub_px]
    
    # Pre-allocate large flat array
    img = np.zeros(n_sub * sub_px * sub_px, dtype=np.float32)
    
    # Gaussian spot parameters
    sigma = 1.2
    
    # Generate spots
    for k in range(n_sub):
        cy = true_center + shift_y
        cx = true_center + shift_x
        
        spot = np.exp(-((x - cx)**2 + (y - cy)**2) / (2 * sigma**2))
        spot = (spot / np.sum(spot)) * photon_count
        
        idx_start = k * sub_px * sub_px
        idx_end = (k + 1) * sub_px * sub_px
        img[idx_start:idx_end] = spot.flatten()
        
    # Apply noise
    if photon_count > 0:
        # Poisson noise for signal
        img = np.random.poisson(img).astype(np.float32)
    
    if bg_noise_std > 0:
        # Gaussian read noise
        img += np.random.normal(0, bg_noise_std, img.shape)
        
    return img

def run_comprehensive_benchmark():
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
    
    # 64 Zernikes is standard for large systems
    n_zernike = 64
    sub_px = 12
    n_iterations = 20

    grids = [10, 20, 40, 80]
    scenarios = [
        {"name": "Ideal", "photons": 10000, "noise": 0.0, "shift": 0.0},
        {"name": "Realistic", "photons": 1000, "noise": 5.0, "shift": 0.0},
        {"name": "Extreme Noise", "photons": 50, "noise": 20.0, "shift": 0.0},
        {"name": "Vibration Drift", "photons": 1000, "noise": 5.0, "shift": 2.5},
    ]

    report = []
    report.append("# Comprehensive Project Scalability & Latency Report")
    report.append("This report benchmarks the End-to-End latency of the C-Engine across various grid scales (from small to ELT scale) and physical scenarios.")
    report.append("")
    report.append("| Array Size | Sub-apertures | Frame Size (px) | Scenario | End-to-End Latency (ms) | Speed vs Deadline |")
    report.append("|:---|---:|---:|:---|---:|:---|")

    for N_1d in grids:
        n_sub = N_1d * N_1d
        n_valid = n_sub
        n_slopes = n_sub * 2
        n_actuators = n_sub # Rough assumption: 1 actuator per lenslet
        
        valid_mask = generate_valid_mask(n_sub)
        # Random normal synthetic matrices
        g_plus = np.random.normal(0, 1e-4, (n_zernike, n_slopes)).astype(np.float32).flatten()
        dm_coupling = np.random.normal(0, 1e-4, (n_actuators, n_zernike)).astype(np.float32).flatten()
        
        for sc in scenarios:
            latencies = []
            for i in range(n_iterations):
                img_data = generate_spot_field(n_sub, sub_px, bg_noise_std=sc["noise"], 
                                               photon_count=sc["photons"], shift_x=sc["shift"], shift_y=sc["shift"])
                
                slopes = np.zeros(n_slopes, dtype=np.float32)
                zernikes = np.zeros(n_zernike, dtype=np.float32)
                actuators = np.zeros(n_actuators, dtype=np.float32)
                
                t0 = time.perf_counter()
                
                # 1. Centroiding
                lib.compute_slopes_weighted(img_data, slopes, valid_mask, n_sub, n_valid, sub_px,
                                            0.0, 0.0, 0.0, 1.0, 0.5)
                # 2. MVM Zernikes
                lib.reconstruct_zernikes(slopes, g_plus, zernikes, n_zernike, n_slopes)
                # 3. MVM Actuators
                lib.compute_actuator_map(zernikes, dm_coupling, actuators, n_actuators, n_zernike, -1.0, 1.0)
                
                t1 = time.perf_counter()
                latencies.append((t1 - t0) * 1000.0)
                
            avg_lat = np.mean(latencies)
            # Hard deadline is 10ms for atmospheric turbulence (100 Hz / tau0)
            deadline = 10.0
            speed_ratio = deadline / avg_lat
            
            frame_px = N_1d * sub_px
            frame_dim = f"{frame_px}x{frame_px}"
            
            report.append(f"| {N_1d}x{N_1d} | {n_sub} | {frame_dim} | {sc['name']} | **{avg_lat:.4f} ms** | {speed_ratio:.1f}x Faster |")

    out_path = os.path.join(project_root, "tests", "nasa_grade", "ultimate_report.md")
    with open(out_path, "w") as f:
        f.write("\\n".join(report))
        
    print(f"Report successfully generated at {out_path}")

if __name__ == "__main__":
    run_comprehensive_benchmark()
