"""
Tune centroiding parameters for the C-Engine against AOTPy ERIS gradients.
Performs a small grid search over background-threshold multiplier and sub-pixel
shifts (x/y) and reports the best parameter set by average R2 across frames.
"""
import os
import ctypes as ct
import numpy as np
import aotpy
from astropy.io import fits

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
AOTPY_FITS = os.path.join(BASE, 'data', 'ERIS_NGS.fits')


def load_lib():
    lib = ct.CDLL(os.path.join(BUILD_DIR, 'c_engine.so'))
    lib.compute_slopes.argtypes = [
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_float),
        ct.POINTER(ct.c_int),
        ct.c_int,
        ct.c_int,
        ct.c_int,
    ]
    lib.compute_slopes.restype = None
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
        lib.has_enhanced = True
    except AttributeError:
        lib.has_enhanced = False
    return lib


def load_data():
    system = aotpy.AOSystem.read_from_file(AOTPY_FITS)
    wfs = system.wavefront_sensors[0]
    images = wfs.detector.pixel_intensities.data.astype(np.float32)
    measurements = wfs.measurements.data.astype(np.float32)
    ref = wfs.ref_measurements.data.astype(np.float32)
    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_mask = valid_flags.astype(np.int32).flatten()
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)
    n_sub = mask.size
    n_valid = int(valid_mask.sum())
    sub_px = images.shape[1] // mask.shape[0]
    n_frames = min(images.shape[0], measurements.shape[0])
    reference_slopes = np.concatenate([ref[0], ref[1]]).astype(np.float32)
    measurements_flat = measurements[:n_frames].reshape(n_frames, -1)
    dark = getattr(wfs.detector, 'dark', None)
    sky = getattr(wfs.detector, 'sky_background', None)
    weight = getattr(wfs.detector, 'weight_map', None)
    dark_arr = dark.data.astype(np.float32) if dark is not None else None
    sky_arr = sky.data.astype(np.float32) if sky is not None else None
    weight_arr = weight.data.astype(np.float32) if weight is not None else None
    return {
        'images': images[:n_frames],
        'measurements': measurements_flat,
        'reference': reference_slopes,
        'valid_mask': valid_mask,
        'valid_labels': valid_labels,
        'n_sub': n_sub,
        'n_valid': n_valid,
        'sub_px': sub_px,
        'n_frames': n_frames,
        'dark': dark_arr,
        'sky': sky_arr,
        'weight': weight_arr,
    }


def compute_metrics(pred, truth):
    diff = pred - truth
    mse = np.mean(diff**2)
    rmse = np.sqrt(mse)
    ss_res = np.sum(diff**2)
    ss_tot = np.sum((truth - np.mean(truth))**2)
    r2 = 1.0 - (ss_res/ss_tot) if ss_tot > 0 else 1.0
    return mse, rmse, r2


def run_grid():
    lib = load_lib()
    data = load_data()
    images = data['images']
    measurements = data['measurements']
    ref = data['reference']
    valid_mask = data['valid_mask']
    valid_labels = data['valid_labels']
    n_sub = data['n_sub']
    n_valid = data['n_valid']
    sub_px = data['sub_px']
    n_frames = data['n_frames']
    dark = data['dark']
    sky = data['sky']
    weight = data['weight']

    # reorder ref into compute order (valididx_to_label mapping)
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    # valid_labels maps flattened valid positions -> label
    valididx_to_label[:] = valid_labels
    reordered_ref = np.concatenate([ref[:n_valid][valididx_to_label], ref[n_valid:][valididx_to_label]])

    bg_multipliers = [0.0, 0.1, 0.25, 0.5, 1.0, 2.0]
    shifts = [-0.5, 0.0, 0.5]

    best = None

    for bgm in bg_multipliers:
        for sx in shifts:
            for sy in shifts:
                slopes_buf = np.zeros(2*n_valid, dtype=np.float32)
                frame_rs = []
                for fi in range(n_frames):
                    img = images[fi].astype(np.float32).copy()
                    if dark is not None:
                        img = img - dark
                    if sky is not None:
                        img = img - sky
                    img[img < 0] = 0.0
                    if weight is not None:
                        img = img * weight
                    if lib.has_enhanced:
                        bg_thresh = 0.0
                        if dark is not None:
                            bg_thresh = float(np.median(dark)) * bgm
                        lib.compute_slopes_enhanced(
                            img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                            ct.c_int(n_sub),
                            ct.c_int(n_valid),
                            ct.c_int(sub_px),
                            ct.c_float(bg_thresh),
                            ct.c_float(sx),
                            ct.c_float(sy),
                        )
                    else:
                        lib.compute_slopes(
                            img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                            ct.c_int(n_sub),
                            ct.c_int(n_valid),
                            ct.c_int(sub_px),
                        )
                    slopes_buf -= reordered_ref
                    truth = measurements[fi]
                    truth = np.concatenate([
                        truth[:n_valid][valididx_to_label],
                        truth[n_valid:][valididx_to_label],
                    ])
                    _, _, r2 = compute_metrics(slopes_buf, truth)
                    frame_rs.append(r2)
                avg_r2 = float(np.mean(frame_rs))
                print(f'bg*{bgm:0.2f} sx={sx:0.2f} sy={sy:0.2f} -> avgR2={avg_r2:.4f}')
                if best is None or avg_r2 > best[0]:
                    best = (avg_r2, bgm, sx, sy)
    print('BEST:', best)
    # Re-evaluate best parameters with full metrics and timing
    _, best_bgm, best_sx, best_sy = best
    slopes_buf = np.zeros(2*n_valid, dtype=np.float32)
    frame_metrics = []
    import time
    times = []
    for fi in range(n_frames):
        t0 = time.time()
        img = images[fi].astype(np.float32).copy()
        if dark is not None:
            img = img - dark
        if sky is not None:
            img = img - sky
        img[img < 0] = 0.0
        if weight is not None:
            img = img * weight
        if lib.has_enhanced:
            bg_thresh = 0.0
            if dark is not None:
                bg_thresh = float(np.median(dark)) * best_bgm
            lib.compute_slopes_enhanced(
                img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                ct.c_int(n_sub),
                ct.c_int(n_valid),
                ct.c_int(sub_px),
                ct.c_float(bg_thresh),
                ct.c_float(best_sx),
                ct.c_float(best_sy),
            )
        else:
            lib.compute_slopes(
                img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
                slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
                valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
                ct.c_int(n_sub),
                ct.c_int(n_valid),
                ct.c_int(sub_px),
            )
        slopes_buf -= np.concatenate([ref[:n_valid][valididx_to_label], ref[n_valid:][valididx_to_label]])
        truth = measurements[fi]
        truth = np.concatenate([
            truth[:n_valid][valididx_to_label],
            truth[n_valid:][valididx_to_label],
        ])
        mse, rmse, r2 = compute_metrics(slopes_buf, truth)
        frame_metrics.append((mse, rmse, r2))
        times.append((time.time() - t0) * 1000.0)

    frame_metrics = np.array(frame_metrics, dtype=np.float32)
    avg = np.mean(frame_metrics, axis=0)
    print('\nFINAL EVAL WITH BEST PARAMETERS:')
    print(f'bg_multiplier={best_bgm} shift_x={best_sx} shift_y={best_sy}')
    print(f'Average MSE: {avg[0]:.4e}  RMSE: {avg[1]:.4e}  R2(avg)={avg[2]:.4f}')
    print(f'Average latency (ms/frame): {np.mean(times):.2f}  min {np.min(times):.2f}  max {np.max(times):.2f}')
    return best


if __name__ == '__main__':
    run_grid()
