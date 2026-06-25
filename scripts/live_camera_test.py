"""
live_camera_test.py
-------------------
Live real-time testing harness for Project Radius.
Acquires frames from SimulatedCameraInterface or a physical GenICam device,
pipes the frame buffers directly to the C-Engine reconstruction pipeline,
and prints live performance statistics (latency, FPS, Strehl ratio, R^2).
"""
import os
import sys
import argparse
import numpy as np
import ctypes as ct
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, 'vendor', 'oopao'))

from src.core.camera_interface import SimulatedCameraInterface, GenICamCameraInterface, PlaybackCameraInterface
from src.turbulence_characterize import estimate_r0, estimate_tau0, estimate_strehl

DATA_DIR = os.path.join(BASE, 'data', 'dataset')

def parse_args():
    parser = argparse.ArgumentParser(description="Live camera C-Engine test.")
    parser.add_argument('--mode', type=str, choices=['sim', 'playback', 'hardware'], default='sim',
                        help="Acquisition mode: 'sim' (OOPAO 1000Hz background thread), 'playback' (high-speed real data playback), or 'hardware' (GenICam GenTL).")
    parser.add_argument('--cti', type=str, default=None,
                        help="Path to GenTL Producer .cti file (required for 'hardware' mode).")
    parser.add_argument('--frames', type=int, default=500,
                        help="Number of frames to run before finishing.")
    parser.add_argument('--fps', type=float, default=1000.0,
                        help="Simulated camera loop rate in Hz (default: 1000.0).")
    return parser.parse_args()

def main():
    args = parse_args()
    print("="*60)
    print(f"Project Radius: Live Real-Time AO Pipeline Test ({args.mode.upper()} Mode)")
    print("="*60)
    
    # 1. Load Calibration Matrices
    print("Loading C-Engine calibration matrices...")
    try:
        g_plus      = np.loadtxt(os.path.join(DATA_DIR, 'g_plus.csv'),      delimiter=',').astype(np.float32)
        dm_coupling = np.loadtxt(os.path.join(DATA_DIR, 'dm_coupling.csv'), delimiter=',').astype(np.float32)
        valid_mask  = np.loadtxt(os.path.join(DATA_DIR, 'valid_mask.csv'),  delimiter=',').astype(np.int32)
        ref_slopes  = np.loadtxt(os.path.join(DATA_DIR, 'ref_slopes.csv'),  delimiter=',').astype(np.float32)
    except FileNotFoundError as e:
        print(f"Error: Calibration matrices not found in {DATA_DIR}. Please run 'python scripts/export_gplus.py' first.")
        sys.exit(1)
        
    n_valid = int(valid_mask.sum())
    n_slopes = 2 * n_valid
    n_zernike = 20
    n_act = 357
    sub_px = 20 # 400 / 20 = 20
    
    print(f"Calibrated WFS: {n_valid} valid subapertures, {n_slopes} signals.")
    
    # 2. Load C-Engine
    lib = ct.CDLL(os.path.join(BASE, 'build', 'c_engine.so'))
    lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3
    lib.compute_slopes.restype  = None
    lib.reconstruct_zernikes.argtypes = [ct.POINTER(ct.c_float)]*3 + [ct.c_int]*2
    lib.reconstruct_zernikes.restype  = None
    lib.compute_actuator_map.argtypes = [ct.POINTER(ct.c_float)]*3 + [ct.c_int]*2
    lib.compute_actuator_map.restype  = None
    
    # Pre-allocate zero-copy buffers
    slopes_buf = np.zeros(n_slopes, dtype=np.float32)
    zernikes   = np.zeros(n_zernike, dtype=np.float32)
    actuators  = np.zeros(n_act,     dtype=np.float32)
    
    # 3. Setup Camera Interface
    if args.mode == 'sim':
        print(f"Spawning simulated camera thread at {args.fps} Hz loop rate...")
        cam = SimulatedCameraInterface(resolution=400, diameter=8.0, n_subap=20, fps=args.fps)
    elif args.mode == 'playback':
        print(f"Spawning playback camera thread from {DATA_DIR} at {args.fps} Hz...")
        cam = PlaybackCameraInterface(data_dir=DATA_DIR, fps=args.fps)
    else:
        if not args.cti:
            print("Error: --cti path is required for hardware mode.")
            sys.exit(1)
        print(f"Connecting to GenICam via GenTL: {args.cti}...")
        cam = GenICamCameraInterface(args.cti)
        
    # Start acquisition
    cam.start_acquisition()
    
    acq_latencies = []
    proc_latencies = []
    r2_per_frame = []
    zlog = []
    gt_zernikes = []
    
    print("\nStarting live real-time processing loop...")
    print(f"Benchmarking {args.frames} frames. Console output updates every 50 frames:\n")
    print(f"{'Frame':<8} | {'Acq Time':<10} | {'Proc Time':<10} | {'Loop Freq':<10} | {'R2 Frame':<10} | {'Strehl':<8}")
    print("-" * 75)
    
    t_start = time.perf_counter()
    
    try:
        for idx in range(args.frames):
            t0 = time.perf_counter()
            
            # Retrieve frame from camera interface
            if args.mode in ('sim', 'playback'):
                frame_data, true_z = cam.get_next_frame(timeout=2.0)
                if frame_data is None:
                    print("\nTimeout: No frame received from camera thread.")
                    break
                t1 = time.perf_counter()
                
                # Zero-copy numpy conversion and float cast
                img_flat = np.ascontiguousarray(frame_data.astype(np.float32, copy=False).flatten())
                img_ptr = img_flat.ctypes.data_as(ct.POINTER(ct.c_float))
            else:
                data_ptr, buffer = cam.get_next_frame(timeout=2.0)
                if data_ptr is None:
                    print("\nTimeout: No frame received from GenICam device.")
                    break
                t1 = time.perf_counter()
                
                # Wrap raw buffer address in numpy (zero-copy) and cast to float
                raw_array = np.ctypeslib.as_array(data_ptr, shape=(400, 400))
                img_flat = np.ascontiguousarray(raw_array.astype(np.float32, copy=False).flatten())
                img_ptr = img_flat.ctypes.data_as(ct.POINTER(ct.c_float))
                
            t_proc_start = time.perf_counter()
            
            # C-Engine Centroiding (CoG)
            lib.compute_slopes(
                img_ptr,
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                ct.c_int(400), ct.c_int(n_valid), ct.c_int(sub_px)
            )
            
            # Subtract flat wavefront reference slopes
            slopes_buf -= ref_slopes
            
            # C-Engine Zernike Reconstruction (MVM)
            lib.reconstruct_zernikes(
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
                zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
                ct.c_int(n_zernike), ct.c_int(n_slopes)
            )
            
            # C-Engine DM Actuator Mapping (MVM)
            lib.compute_actuator_map(
                zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
                dm_coupling.ctypes.data_as(ct.POINTER(ct.c_float)),
                actuators.ctypes.data_as(ct.POINTER(ct.c_float)),
                ct.c_int(n_act), ct.c_int(n_zernike)
            )
            
            t_proc_end = time.perf_counter()
            
            # Queue buffer back for hardware modes
            if args.mode == 'hardware':
                cam.queue_buffer(buffer)
                
            # Log metrics
            acq_lat = (t1 - t0) * 1e3
            proc_lat = (t_proc_end - t_proc_start) * 1e3
            acq_latencies.append(acq_lat)
            proc_latencies.append(proc_lat)
            zlog.append(zernikes.copy())
            
            # Compute R^2 metrics and Strehl if we have ground truth (Sim or Playback Mode)
            if args.mode in ('sim', 'playback'):
                gt_zernikes.append(true_z)
                pred_no_piston = zernikes[1:]
                true_no_piston = true_z[1:]
                
                ss_res_f = np.sum((pred_no_piston - true_no_piston)**2)
                ss_tot_f = np.sum((true_no_piston - np.mean(true_no_piston))**2)
                r2_f = 1.0 - (ss_res_f / ss_tot_f) if ss_tot_f > 0 else 1.0
                r2_per_frame.append(r2_f)
                
                wavelength = 2.2e-6
                residual_rms_rad = np.std(pred_no_piston - true_no_piston) * (2 * np.pi / wavelength)
                strehl = estimate_strehl(residual_rms_rad)
            else:
                r2_f = np.nan
                strehl = np.nan
                
            # Console reporting
            if (idx + 1) % 50 == 0 or idx == 0:
                loop_freq = 1.0 / (t_proc_end - t0)
                r2_str = f"{r2_f*100:6.2f}%" if not np.isnan(r2_f) else "N/A"
                strehl_str = f"{strehl:.4f}" if not np.isnan(strehl) else "N/A"
                print(f"{idx+1:<8d} | {acq_lat:7.3f} ms | {proc_lat:7.3f} ms | {loop_freq:7.1f} Hz | {r2_str:<10} | {strehl_str:<8}")
                
    finally:
        cam.stop_acquisition()
        
    t_end = time.perf_counter()
    total_time = t_end - t_start
    print("="*75)
    print("LIVE RUN SUMMARY")
    print("="*75)
    print(f"Total time elapsed:              {total_time:.3f} s")
    print(f"Acquisition Avg Latency:         {np.mean(acq_latencies):.4f} ms")
    print(f"C-Engine Processing Avg Latency: {np.mean(proc_latencies):.4f} ms")
    print(f"Average Loop Rate:               {len(acq_latencies)/total_time:.2f} Hz")
    
    if args.mode in ('sim', 'playback') and len(gt_zernikes) > 0:
        zlog = np.array(zlog)
        gt_zernikes = np.array(gt_zernikes)
        wavelength = 2.2e-6
        zlog_rad = zlog * (2 * np.pi / wavelength)
        
        r0 = estimate_r0(zlog_rad, D=8.0, tip_idx=1, tilt_idx=2)
        tau0 = estimate_tau0(zlog_rad, fps=args.fps, tip_idx=1, tilt_idx=2)
        
        # Calculate Global temporal R^2
        ss_r = sum(np.sum((zlog[i, 1:] - gt_zernikes[i, 1:])**2) for i in range(len(zlog)))
        ss_t = np.sum((gt_zernikes[:, 1:] - gt_zernikes[:, 1:].mean(axis=0))**2)
        r2_global = 1.0 - ss_r / ss_t if ss_t > 0 else 0.0
        
        print(f"Turbulence: r0 Estimated:        {r0:.4f} m")
        print(f"Turbulence: tau0 Estimated:      {tau0:.4f} s")
        print(f"Absolute Numerical Accuracy (R²): {r2_global*100:.4f} % (Global Temporal)")
        print(f"Shape Matching Accuracy (R²):     {np.mean(r2_per_frame)*100:.4f} % (Average Per-Frame)")
        
    print("="*75)

if __name__ == '__main__':
    main()
