"""
aotpy_validation.py
------------------
Independent AOTPy validation for Project Radius C-Engine centroiding.

This script loads the ERIS_NGS.fits dataset included in `data/`, computes
centroid slopes on the raw Shack-Hartmann detector pixels using the C-Engine,
and compares the results against the AOTPy-provided wavefront sensor
measurements.
"""

import os
import time
import ctypes as ct

import numpy as np
import aotpy

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
DATA_DIR = os.path.join(BASE, 'data')
AOTPY_FITS = os.path.join(DATA_DIR, 'ERIS_NGS.fits')


def load_c_engine():
    lib_path = os.path.join(BUILD_DIR, 'c_engine.so')
    if not os.path.exists(lib_path):
        raise FileNotFoundError(f"C-Engine not found at {lib_path}. Build it first.")

    lib = ct.CDLL(lib_path)
    lib.compute_slopes.argtypes = [
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_int),
        ct.c_int,
        ct.c_int,
        ct.c_int,
    ]
    lib.compute_slopes.restype = None
    # Try to expose enhanced centroiding if available
    try:
        lib.compute_slopes_enhanced.argtypes = [
            ct.POINTER(ct.c_float),
            ct.POINTER(ct.c_float),
            ct.POINTER(ct.c_int),
            ct.c_int,
            ct.c_int,
            ct.c_int,
            ct.c_float,
            ct.c_float,
            ct.c_float,
        ]
        lib.compute_slopes_enhanced.restype = None
        lib.has_compute_slopes_enhanced = True
    except AttributeError:
        lib.has_compute_slopes_enhanced = False
    # New weighted variant
    try:
        lib.compute_slopes_weighted.argtypes = [
            ct.POINTER(ct.c_float),
            ct.POINTER(ct.c_float),
            ct.POINTER(ct.c_int),
            ct.c_int,
            ct.c_int,
            ct.c_int,
            ct.c_float,
            ct.c_float,
            ct.c_float,
            ct.c_float,
            ct.c_float,
        ]
        lib.compute_slopes_weighted.restype = None
        lib.has_compute_slopes_weighted = True
    except AttributeError:
        lib.has_compute_slopes_weighted = False
    return lib


def load_aotpy_eris():
    if not os.path.exists(AOTPY_FITS):
        raise FileNotFoundError(f"AOTPy ERIS file not found at {AOTPY_FITS}")

    system = aotpy.AOSystem.read_from_file(AOTPY_FITS)
    if len(system.wavefront_sensors) == 0:
        raise ValueError("ERIS file contains no wavefront sensors.")

    wfs = system.wavefront_sensors[0]
    images = wfs.detector.pixel_intensities.data.astype(np.float32)
    ref_measurements = wfs.ref_measurements.data.astype(np.float32)
    true_measurements = wfs.measurements.data.astype(np.float32)

    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_mask = valid_flags.astype(np.int32).flatten()
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)

    n_sub = int(mask.size)
    n_valid = int(valid_mask.sum())
    sub_px = images.shape[1] // mask.shape[0]

    if true_measurements.shape[1] != 2 or true_measurements.shape[2] != n_valid:
        raise ValueError(
            f"Unexpected measurement shape {true_measurements.shape} for n_valid={n_valid}."
        )

    if ref_measurements.shape[0] != 2 or ref_measurements.shape[1] != n_valid:
        raise ValueError(
            f"Unexpected ref_measurements shape {ref_measurements.shape} for n_valid={n_valid}."
        )

    if not np.array_equal(np.sort(valid_labels), np.arange(n_valid)):
        raise ValueError("Unexpected subaperture label ordering in AOTPy mask.")

    label_to_valididx = np.empty(n_valid, dtype=np.int32)
    label_to_valididx[valid_labels] = np.arange(n_valid, dtype=np.int32)
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[label_to_valididx] = np.arange(n_valid, dtype=np.int32)

    reference_slopes = np.concatenate([ref_measurements[0], ref_measurements[1]]).astype(np.float32)
    n_frames = min(images.shape[0], true_measurements.shape[0])
    measurements_flat = true_measurements[:n_frames].reshape(n_frames, -1)
    # Detector calibration images (may be None in some files)
    dark = None
    sky_background = None
    weight_map = None
    try:
        dark = wfs.detector.dark.data.astype(np.float32)
    except Exception:
        dark = None
    try:
        sky_background = wfs.detector.sky_background.data.astype(np.float32)
    except Exception:
        sky_background = None
    try:
        weight_map = wfs.detector.weight_map.data.astype(np.float32)
    except Exception:
        weight_map = None
    return {
        'images': images[:n_frames],
        'reference_slopes': reference_slopes,
        'measurements': measurements_flat,
        'valid_mask': valid_mask,
        'label_to_valididx': label_to_valididx,
        'valididx_to_label': valididx_to_label,
        'n_sub': n_sub,
        'n_valid': n_valid,
        'sub_px': sub_px,
        'n_frames': n_frames,
        'dark': dark,
        'sky_background': sky_background,
        'weight_map': weight_map,
    }


def compute_metrics(predictions, truth):
    diff = predictions - truth
    mse = np.mean(diff**2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(diff))
    ss_res = np.sum(diff**2)
    ss_tot = np.sum((truth - np.mean(truth))**2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0
    return mse, rmse, mae, r2


def main():
    print('=' * 72)
    print('Project Radius: AOTPy ERIS Validation')
    print('=' * 72)

    lib = load_c_engine()
    data = load_aotpy_eris()

    images = data['images']
    reference_slopes = data['reference_slopes']
    measurements = data['measurements']
    valid_mask = data['valid_mask']
    label_to_valididx = data['label_to_valididx']
    valididx_to_label = data['valididx_to_label']
    n_sub = data['n_sub']
    n_valid = data['n_valid']
    sub_px = data['sub_px']
    n_frames = data['n_frames']
    dark = data.get('dark')
    sky_background = data.get('sky_background')
    weight_map = data.get('weight_map')

    print(f'AOTPy ERIS telemetry loaded: {n_frames} matched frames')
    print(f'  WFS image shape: {images.shape[1:]}')
    print(f'  Valid subapertures: {n_valid}/{n_sub}')
    print(f'  Subaperture pixel pitch: {sub_px}')
    print()
    # Try to load clipped affine coefficients (per-subap affine: gain, offset)
    coefs_path = os.path.join(BUILD_DIR, 'clipped_affine_coefs.npy')
    coefs = None
    if os.path.exists(coefs_path):
        try:
            coefs = np.load(coefs_path).astype(np.float32)
            gains = coefs[:, 0].astype(np.float32)
            offs = coefs[:, 1].astype(np.float32)
            print(f'Loaded clipped affine coefs from {coefs_path}')
        except Exception:
            coefs = None

    if measurements.shape != (n_frames, 2 * n_valid):
        raise ValueError(
            f"Unexpected flattened measurement shape {measurements.shape}; expected ({n_frames}, {2 * n_valid})."
        )

    # Reorder AOTPy measurements and reference slopes from label order into row-major valid order
    reordered_ref = np.concatenate([
        reference_slopes[:n_valid][valididx_to_label],
        reference_slopes[n_valid:][valididx_to_label],
    ])
    slopes_buf = np.zeros(2 * n_valid, dtype=np.float32)
    frame_metrics = []

    for frame_idx in range(n_frames):
        frame_start = time.time()
        img = images[frame_idx]
        # Apply detector calibration: subtract dark/background, clamp, apply weight map
        cal = img.astype(np.float32).copy()
        if dark is not None:
            # dark is same shape as detector image
            cal = cal - dark
        if sky_background is not None:
            cal = cal - sky_background
        # clamp negatives to zero
        cal[cal < 0.0] = 0.0
        if weight_map is not None:
            cal = cal * weight_map

        # Prefer weighted centroiding if available, else enhanced, else basic
        weighted_params = None
        try:
            weighted_params = np.load(os.path.join(BUILD_DIR, 'weighted_cog_params.npy'), allow_pickle=True).item()
        except Exception:
            weighted_params = None

        if getattr(lib, 'has_compute_slopes_weighted', False) or getattr(lib, 'has_weighted', False):
            bg_thresh = 0.0 if dark is None else float(np.median(dark))
            shift_x = 0.0
            shift_y = 0.0
            weight_exp = 1.0
            thr_mul = 0.0
            if weighted_params is not None:
                weight_exp = float(weighted_params.get('weight_exp', 1.0))
                thr_mul = float(weighted_params.get('thr_mul', 0.0))
            lib.compute_slopes_weighted(
                cal.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                ct.c_int(n_sub),
                ct.c_int(n_valid),
                ct.c_int(sub_px),
                ct.c_float(bg_thresh),
                ct.c_float(shift_x),
                ct.c_float(shift_y),
                ct.c_float(weight_exp),
                ct.c_float(thr_mul),
            )
        elif getattr(lib, 'has_compute_slopes_enhanced', False):
            bg_thresh = 0.0
            if dark is not None:
                bg_thresh = float(np.median(dark))
            shift_x = 0.0
            shift_y = 0.0
            lib.compute_slopes_enhanced(
                cal.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                ct.c_int(n_sub),
                ct.c_int(n_valid),
                ct.c_int(sub_px),
                ct.c_float(bg_thresh),
                ct.c_float(shift_x),
                ct.c_float(shift_y),
            )
        else:
            lib.compute_slopes(
                cal.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                ct.c_int(n_sub),
                ct.c_int(n_valid),
                ct.c_int(sub_px),
            )

        slopes_buf -= reordered_ref
        # apply per-subap affine correction if available (vectorized)
        if coefs is not None:
            slopes_adj = slopes_buf * gains + offs
        else:
            slopes_adj = slopes_buf

        truth = measurements[frame_idx]
        truth = np.concatenate([
            truth[:n_valid][valididx_to_label],
            truth[n_valid:][valididx_to_label],
        ])
        mse, rmse, mae, r2 = compute_metrics(slopes_adj, truth)
        frame_metrics.append((mse, rmse, mae, r2))

        if frame_idx == 0:
            print('Frame 0 sample comparison:')
            print('  C-engine slopes first 10:', slopes_buf[:10].tolist())
            if coefs is not None:
                print('  Adjusted slopes first 10:', slopes_adj[:10].tolist())
            print('  AOTPy truth first 10:     ', truth[:10].tolist())
            print('  Reference slopes first 10:', reference_slopes[:10].tolist())
            print()

        elapsed = time.time() - frame_start
        print(
            f'Frame {frame_idx+1:03d}/{n_frames} | MSE={mse:.4e} | RMSE={rmse:.4e} | '
            f'MAE={mae:.4e} | R2={r2:.4f} | loop={elapsed*1000:.2f} ms'
        )

    frame_metrics = np.array(frame_metrics, dtype=np.float32)
    avg = np.mean(frame_metrics, axis=0)
    print('\n--- AOTPy ERIS Validation Summary ---')
    print(f'Average MSE:  {avg[0]:.4e}')
    print(f'Average RMSE: {avg[1]:.4e}')
    print(f'Average MAE:  {avg[2]:.4e}')
    print(f'Average R2:   {avg[3]*100:.2f}%')

    print('\nSummary metrics by frame:')
    for i, (mse, rmse, mae, r2) in enumerate(frame_metrics):
        print(f'  Frame {i+1:02d}: R2={r2*100:6.2f}%  RMSE={rmse:.4e}  MAE={mae:.4e}')


if __name__ == '__main__':
    main()
