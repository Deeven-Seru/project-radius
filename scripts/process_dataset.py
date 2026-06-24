"""
process_dataset.py
------------------
Main benchmark: loads 500 BMP frames, runs C-Engine (CoG + Zernike MVM +
DM actuator MVM) per frame, reports MSE, R2 accuracy, latency, r0, tau0.
"""
import numpy as np, ctypes as ct, os, time
from PIL import Image
import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.turbulence_characterize import estimate_r0, estimate_tau0

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DATA = os.path.join(BASE, 'data', 'dataset')
BUILD= os.path.join(BASE, 'build')

N_ZERNIKE, N_ACT, FPS, D = 20, 357, 100.0, 8.0

def main():
    print("="*60 + "\nProject Radius: Processing Synthetic WFS Dataset\n" + "="*60)
    g_plus      = np.loadtxt(os.path.join(DATA,'g_plus.csv'),      delimiter=None).astype(np.float32)
    dm_coupling = np.loadtxt(os.path.join(DATA,'dm_coupling.csv'), delimiter=None).astype(np.float32)
    valid_mask  = np.loadtxt(os.path.join(DATA,'valid_mask.csv'),  delimiter=None).astype(np.int32)
    ground_truth= np.loadtxt(os.path.join(DATA,'ground_truth.csv'),delimiter=None).astype(np.float32)
    n_valid = int(valid_mask.sum())
    print(f"Loaded valid_mask: {n_valid} valid out of {len(valid_mask)}")

    lib = ct.CDLL(os.path.join(BUILD, 'c_engine.so'))
    for fn, args in [('compute_slopes',      [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3),
                     ('reconstruct_zernikes',[ct.POINTER(ct.c_float)]*3 + [ct.c_int]*2),
                     ('compute_actuator_map',[ct.POINTER(ct.c_float)]*3 + [ct.c_int]*2)]:
        getattr(lib, fn).argtypes = args
        getattr(lib, fn).restype  = None

    frames = sorted([f for f in os.listdir(DATA) if f.endswith('.bmp')])
    n_frames = len(frames)
    n_slopes = 2 * n_valid
    slopes_buf = np.zeros(n_slopes,  dtype=np.float32)
    zernikes   = np.zeros(N_ZERNIKE, dtype=np.float32)
    actuators  = np.zeros(N_ACT,     dtype=np.float32)
    mask_buf   = valid_mask.astype(np.int32)

    mse_list, latencies, zlog = [], [], []
    print(f"Processing {n_frames} Frames...")

    for idx, fname in enumerate(frames):
        img = np.array(Image.open(os.path.join(DATA, fname))).astype(np.float32)
        img_flat = np.ascontiguousarray(img.flatten())
        t0 = time.perf_counter()
        lib.compute_slopes(img_flat.ctypes.data_as(ct.POINTER(ct.c_float)),
                           slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                           mask_buf.ctypes.data_as(ct.POINTER(ct.c_int)),
                           ct.c_int(400), ct.c_int(n_valid), ct.c_int(8))
        lib.reconstruct_zernikes(slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  ct.c_int(N_ZERNIKE), ct.c_int(n_slopes))
        lib.compute_actuator_map(zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  dm_coupling.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  actuators.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  ct.c_int(N_ACT), ct.c_int(N_ZERNIKE))
        t1 = time.perf_counter()
        latencies.append((t1-t0)*1e3)
        mse_list.append(float(np.mean((zernikes - ground_truth[idx,:N_ZERNIKE])**2)))
        zlog.append(zernikes.copy())

    zlog = np.array(zlog)
    r0   = estimate_r0(zlog,  D=D)
    tau0 = estimate_tau0(zlog, fps=FPS)
    mse  = np.mean(mse_list)
    ss_r = sum(np.sum((zlog[i]-ground_truth[i,:N_ZERNIKE])**2) for i in range(n_frames))
    ss_t = np.sum((ground_truth[:n_frames,:N_ZERNIKE] - ground_truth[:n_frames,:N_ZERNIKE].mean())**2)
    r2   = 1.0 - ss_r/ss_t if ss_t > 0 else 0.0

    print(f"\n{'':->60}\nRESULTS SUMMARY\n{'':->60}")
    print(f"Turbulence: r0 Estimated:            {r0:.4e} m")
    print(f"Turbulence: tau0 Estimated:          {tau0:.4f} s")
    print(f"C-Engine End-to-End Average MSE:     {mse:.8e}")
    print(f"Absolute Numerical Accuracy (R^2):   {r2*100:.4f} %")
    print(f"C-Engine End-to-End Avg Latency:     {np.mean(latencies):.6f} ms per frame")
    print(f"Successfully generated physical DM commands for {N_ACT} actuators per frame.")
    print(f"{'':->60}")

if __name__ == '__main__': main()
