import os
import sys
import time
import ctypes as ct
import numpy as np
import hcipy as hp

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define C-Engine interface
def load_c_engine():
    lib_path = os.path.join(BASE, 'build', 'c_engine.so')
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"C-Engine not found at {lib_path}. Run 'make' in src/c_engine.")
    
    lib = ct.CDLL(lib_path)
    lib.compute_slopes.argtypes = [
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_int),
        ct.c_int,
        ct.c_int,
        ct.c_int
    ]
    lib.compute_slopes.restype = None
    
    lib.reconstruct_zernikes.argtypes = [
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_float),
        ct.c_int,
        ct.c_int
    ]
    lib.reconstruct_zernikes.restype = None
    return lib

def main():
    print("="*60)
    print("Project Radius: HCIPy Independent Validation")
    print("="*60)
    
    lib = load_c_engine()
    
    # 1. Hardware & Grid Setup
    D = 8.0
    wavelength = 2.2e-6
    num_lenslets = 20
    n_zernike = 20
    
    print("Initializing HCIPy Optic Elements...")
    pupil_grid = hp.make_pupil_grid(400, D)
    aperture = hp.make_circular_aperture(D)(pupil_grid)
    
    # Zernike Basis (HCIPy uses Noll indexing starting from 1)
    # We will ignore piston later when computing MSE
    zernike_basis = hp.make_zernike_basis(n_zernike, D, pupil_grid, starting_mode=1)
    z_norm = np.ones(n_zernike) # HCIPy Zernikes are RMS normalized over the pupil
    
    shwfs = hp.SquareShackHartmannWavefrontSensorOptics(
        pupil_grid, 
        f_number=40, 
        num_lenslets=num_lenslets, 
        pupil_diameter=D
    )
    
    wf = hp.Wavefront(aperture, wavelength)
    img_wf = shwfs(wf)
    camera = hp.NoiselessDetector(img_wf.grid)
    camera.integrate(img_wf, 1.0)
    ref_image = camera.read_out()
    
    sub_px = int(np.sqrt(img_wf.grid.size) / num_lenslets)
    
    # 2. Extract valid_mask
    ref_2d = ref_image.shaped
    valid_mask = np.zeros((num_lenslets, num_lenslets), dtype=np.int32)
    for i in range(num_lenslets):
        for j in range(num_lenslets):
            patch = ref_2d[i*sub_px:(i+1)*sub_px, j*sub_px:(j+1)*sub_px]
            if np.sum(patch) > 0.1 * np.max(ref_2d):  # threshold for partial illumination
                valid_mask[i, j] = 1
                
    valid_mask = valid_mask.flatten()
    n_valid = int(np.sum(valid_mask))
    n_slopes = n_valid * 2
    print(f"HCIPy SHWFS: {sub_px} pixels per subaperture. Valid Subapertures: {n_valid}")
    
    # 3. Calibrate Interaction Matrix
    print("Calibrating C-Engine Interaction Matrix using HCIPy Zernikes...")
    amp = 1e-6 # 1 micron poke
    
    ref_slopes = np.zeros(n_slopes, dtype=np.float32)
    lib.compute_slopes(
        ref_image.astype(np.float32).ctypes.data_as(ct.POINTER(ct.c_float)),
        ref_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
        valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
        ct.c_int(num_lenslets**2),
        ct.c_int(n_valid),
        ct.c_int(sub_px)
    )
    
    M = np.zeros((n_slopes, n_zernike), dtype=np.float32)
    slopes_buf = np.zeros(n_slopes, dtype=np.float32)
    
    for i in range(n_zernike):
        phase = zernike_basis[i] * amp
        wf = hp.Wavefront(aperture * np.exp(1j * phase * 2 * np.pi / wavelength), wavelength)
        camera.integrate(shwfs(wf), 1.0)
        img = camera.read_out().astype(np.float32)
        
        # C-Engine computes absolute slopes
        lib.compute_slopes(
            img.ctypes.data_as(ct.POINTER(ct.c_float)),
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            ct.c_int(num_lenslets**2),
            ct.c_int(n_valid),
            ct.c_int(sub_px)
        )
        M[:, i] = (slopes_buf - ref_slopes) / amp
        
    g_plus = np.linalg.pinv(M, rcond=1e-2).astype(np.float32)
    
    # 4. Turbulence Simulation Setup
    print("Setting up HCIPy Von Karman Atmosphere...")
    fried_parameter = 0.15
    L0 = 25.0
    velocity = 10.0
    Cn2 = hp.Cn_squared_from_fried_parameter(fried_parameter, 500e-9)
    layer = hp.InfiniteAtmosphericLayer(pupil_grid, Cn2, L0, velocity)
    
    # 5. Real-Time Benchmark
    n_frames = 100
    mses, r2s = [], []
    pred_buf = np.zeros(n_zernike, dtype=np.float32)
    
    print("\n--- Starting HCIPy Real-Time Loop ---")
    for frame in range(n_frames):
        t0 = time.time()
        
        # Evolve atmosphere by 10ms
        layer.evolve_until(frame * 0.01)
        
        # Ground Truth Phase (in radians) -> meters
        phase_rad = layer.phase_for(wavelength)
        wf = hp.Wavefront(aperture * np.exp(1j * phase_rad), wavelength)
        
        # True Zernikes
        true_phase_m = (phase_rad * wavelength) / (2 * np.pi)
        # Project using HCIPy transformation matrix
        true_zernikes = zernike_basis.transformation_matrix.T.dot(true_phase_m * aperture) / np.sum(aperture)
        # Wait, the projection should be over the pupil. Let's use a simpler discrete dot product:
        # zernike_basis is shape (N, pixels).
        true_zernikes = np.array([np.sum(true_phase_m * aperture * Z) / np.sum(aperture * Z**2) for Z in zernike_basis])
        
        # Generate WFS Image
        camera.integrate(shwfs(wf), 1.0)
        img = camera.read_out().astype(np.float32)
        
        # C-Engine Pipeline
        lib.compute_slopes(
            img.ctypes.data_as(ct.POINTER(ct.c_float)),
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            ct.c_int(num_lenslets**2),
            ct.c_int(n_valid),
            ct.c_int(sub_px)
        )
        
        slopes_buf -= ref_slopes
        
        lib.reconstruct_zernikes(
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
            pred_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            n_zernike,
            n_slopes
        )
        
        t1 = time.time()
        
        # Metrics (exclude piston = index 0)
        true_no_piston = true_zernikes[1:]
        pred_no_piston = pred_buf[1:]
        
        mse = np.mean((true_no_piston - pred_no_piston)**2)
        ss_res = np.sum((true_no_piston - pred_no_piston)**2)
        ss_tot = np.sum((true_no_piston - np.mean(true_no_piston))**2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
        
        if frame == 0:
            print("DEBUG Frame 0 True Zernikes:", true_no_piston[:5])
            print("DEBUG Frame 0 Pred Zernikes:", pred_no_piston[:5])
            print("DEBUG sum slopes:", np.sum(np.abs(slopes_buf)))
            
        mses.append(mse)
        r2s.append(r2)
        fps = 1.0 / (t1 - t0)
        
        print(f"Frame {frame+1:03d} | MSE: {mse:.4e} | R2: {r2*100:6.2f}% | {fps:5.1f} FPS")

    print("--- Done ---")
    print(f"HCIPy Validation Average R2: {np.mean(r2s)*100:.2f}%")

if __name__ == '__main__':
    main()
