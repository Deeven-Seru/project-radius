import numpy as np
import ctypes as ct
import os
import sys
import time

BASE = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(BASE, 'vendor', 'oopao'))

from OOPAO.Telescope import Telescope
from OOPAO.Source import Source
from OOPAO.ShackHartmann import ShackHartmann
from OOPAO.Atmosphere import Atmosphere
from OOPAO.Zernike import Zernike

sys.path.insert(0, os.path.join(BASE, 'src'))
from turbulence_characterize import estimate_r0, estimate_tau0

def compute_zernike_interaction_matrix(tel, wfs, zernike_basis, n_zernike, n_slopes):
    """Calibrate the Zernike interaction matrix by poking each mode."""
    M = np.zeros((n_slopes, n_zernike), dtype=np.float32)
    amp = 1e-6 # 1 micron to avoid numerical precision loss in OOPAO WFS
    src = Source('K', magnitude=8)
    for i in range(n_zernike):
        opd = np.zeros((tel.resolution, tel.resolution), dtype=np.float32)
        opd[tel.pupil > 0] = zernike_basis.modes[:, i] * amp
        src.OPD_no_pupil = opd
        src * tel * wfs
        M[:, i] = wfs.signal.flatten() / amp
    return M

def main():
    print("Initializing OOPAO objects...")
    resolution = 400
    tel = Telescope(resolution=resolution, diameter=8.0)
    src = Source('K', magnitude=8)
    src * tel
    
    # 20 subapertures => resolution 100 is 5 pixels per subaperture
    wfs = ShackHartmann(nSubap=20, telescope=tel, lightRatio=0.5)
    
    atm = Atmosphere(telescope=tel, r0=0.15, L0=25, fractionalR0=[1.0], windSpeed=[10], windDirection=[0], altitude=[0], src=src)
    atm.initializeAtmosphere(tel)
    
    n_zernike = 20
    n_slopes = int(wfs.nSignal)
    
    print(f"Generating Zernike basis (N={n_zernike})...")
    Z = Zernike(tel, J=n_zernike)
    Z.computeZernike(tel, remove_piston=0) # keep piston or remove? Zernike J=1 is piston
    
    print("Computing Interaction Matrix...")
    M = compute_zernike_interaction_matrix(tel, wfs, Z, n_zernike, n_slopes)
    print("Inverting Interaction Matrix...")
    g_plus = np.linalg.pinv(M, rcond=1e-2).astype(np.float32)
    g_plus = np.ascontiguousarray(g_plus)
    print("M nans:", np.isnan(M).sum(), "g_plus nans:", np.isnan(g_plus).sum())
    print("M max/min:", np.max(M), np.min(M))
    print("g_plus max/min:", np.max(g_plus), np.min(g_plus))
    
    print(f"Loading C-engine from {os.path.join(BASE, 'build', 'c_engine.so')}...")
    lib = ct.CDLL(os.path.join(BASE, 'build', 'c_engine.so'))
    lib.reconstruct_zernikes.argtypes = [ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.c_int, ct.c_int]
    lib.reconstruct_zernikes.restype  = None
    
    n_frames = 100
    mses = []
    r2s = []
    pred_zlog = []
    true_zlog = []
    
    print("\n--- Starting Real-Time Loop ---")
    
    # Pre-calculate normalizer for Zernike projection
    z_norm = np.sum(Z.modes**2, axis=0)
    print("z_norm zeros:", np.sum(z_norm == 0))
    
    for i in range(n_frames):
        t0 = time.time()
        
        # 1. Update atmosphere
        atm.update()
        src * atm * tel * wfs
        slopes = np.ascontiguousarray(wfs.signal.flatten().astype(np.float32))
        
        # 2. Get True Zernike coefficients from phase
        true_phase = src.OPD[tel.pupil > 0]
        true_zernikes = np.sum(true_phase[:, None] * Z.modes, axis=0) / z_norm
        true_zernikes = true_zernikes.astype(np.float32)
        
        # 3. Predict Zernike coefficients via c_engine
        pred_zernikes = np.ascontiguousarray(np.zeros(n_zernike, dtype=np.float32))
        lib.reconstruct_zernikes(
            slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
            g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
            pred_zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
            ct.c_int(n_zernike), ct.c_int(n_slopes)
        )
        
        # 4. Compute metrics (ignore Piston, which is mode 0)
        pred_no_piston = pred_zernikes[1:]
        true_no_piston = true_zernikes[1:]
        mse = np.mean((pred_no_piston - true_no_piston)**2)
        ss_res = np.sum((pred_no_piston - true_no_piston)**2)
        ss_tot = np.sum((true_no_piston - np.mean(true_no_piston))**2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
        
        mses.append(mse)
        r2s.append(r2)
        pred_zlog.append(pred_zernikes.copy())
        true_zlog.append(true_zernikes.copy())
        
        t1 = time.time()
        fps = 1.0 / (t1 - t0)
        
        if i == 0:
            print("True:", true_no_piston[:4])
            print("Pred:", pred_no_piston[:4])
            print("Ratio:", true_no_piston[:4] / pred_no_piston[:4])
            
        print(f"Frame {i+1:03d} | MSE: {mse:.4e} | R2: {r2*100:6.2f}% | {fps:5.1f} FPS")
        
    print("--- Done ---")
    
    pred_zlog = np.array(pred_zlog)
    wavelength = 2.2e-6
    pred_zlog_rad = pred_zlog * (2 * np.pi / wavelength)
    
    r0 = estimate_r0(pred_zlog_rad, D=tel.D)
    tau0 = estimate_tau0(pred_zlog_rad, fps=100.0) # Assumes 100Hz WFS rate for tau0 calculation
    
    print(f"Average MSE: {np.mean(mses):.4e}")
    print(f"Average R2:  {np.mean(r2s)*100:.2f}%")
    print(f"Estimated r0: {r0:.4e} m")
    print(f"Estimated tau0: {tau0:.4f} s")

if __name__ == '__main__':
    main()
