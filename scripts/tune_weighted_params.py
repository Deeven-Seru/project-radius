"""
Grid-search weighted centroid params: bg_multiplier, shift_x/y, weight_exp, thr_mul.
Saves best params to `build/weighted_cog_params.npy`.
"""
import os
import ctypes as ct
import numpy as np
import aotpy
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
AOTPY_FITS = os.path.join(BASE, 'data', 'ERIS_NGS.fits')


def load_lib():
    lib = ct.CDLL(os.path.join(BUILD_DIR, 'c_engine.so'))
    lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.POINTER(ct.c_int), ct.c_int, ct.c_int, ct.c_int]
    lib.compute_slopes.restype = None
    try:
        lib.compute_slopes_enhanced.argtypes = [ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.POINTER(ct.c_int), ct.c_int, ct.c_int, ct.c_int, ct.c_float, ct.c_float, ct.c_float]
        lib.compute_slopes_enhanced.restype = None
        lib.has_enhanced = True
    except AttributeError:
        lib.has_enhanced = False
    try:
        lib.compute_slopes_weighted.argtypes = [ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.POINTER(ct.c_int), ct.c_int, ct.c_int, ct.c_int, ct.c_float, ct.c_float, ct.c_float, ct.c_float, ct.c_float]
        lib.compute_slopes_weighted.restype = None
        lib.has_weighted = True
    except AttributeError:
        lib.has_weighted = False
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
    dark = None
    try:
        dark = wfs.detector.dark.data.astype(np.float32)
    except Exception:
        dark = None
    return images[:n_frames], measurements_flat, reference_slopes, valid_mask, valid_labels, n_sub, n_valid, sub_px, n_frames, dark


def compute_metrics(pred, truth):
    diff = pred - truth
    mse = np.mean(diff**2)
    rmse = np.sqrt(mse)
    ss_res = np.sum(diff**2)
    ss_tot = np.sum((truth - np.mean(truth))**2)
    r2 = 1.0 - (ss_res/ss_tot) if ss_tot > 0 else 1.0
    return mse, rmse, r2


def main():
    lib = load_lib()
    images, measurements, reference_slopes, valid_mask, valid_labels, n_sub, n_valid, sub_px, n_frames, dark = load_data()
    # mapping
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[:] = valid_labels

    reordered_ref = np.concatenate([reference_slopes[:n_valid][valididx_to_label], reference_slopes[n_valid:][valididx_to_label]])

    bg_multipliers = [0.0, 0.5, 1.0, 2.0]
    shifts = [-0.5, 0.0, 0.5]
    weight_exps = [0.0, 0.5, 1.0]
    thr_muls = [0.0, 0.25, 0.5]

    best = None
    best_params = None

    for bgm in bg_multipliers:
        for sx in shifts:
            for sy in shifts:
                for wexp in weight_exps:
                    for tm in thr_muls:
                        frame_rs = []
                        for fi in range(n_frames):
                            img = images[fi].astype(np.float32).copy()
                            if dark is not None:
                                img = img - dark
                            img[img < 0] = 0.0
                            slopes_buf = np.zeros(2*n_valid, dtype=np.float32)
                            if getattr(lib, 'has_weighted', False):
                                bg_thresh = 0.0 if dark is None else float(np.median(dark)) * bgm
                                lib.compute_slopes_weighted(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_thresh), ct.c_float(sx), ct.c_float(sy), ct.c_float(wexp), ct.c_float(tm))
                            elif getattr(lib, 'has_enhanced', False):
                                bg_thresh = 0.0 if dark is None else float(np.median(dark)) * bgm
                                lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_thresh), ct.c_float(sx), ct.c_float(sy))
                            else:
                                lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
                            slopes_buf -= reordered_ref
                            truth = measurements[fi]
                            truth = np.concatenate([
                                truth[:n_valid][valididx_to_label],
                                truth[n_valid:][valididx_to_label],
                            ])
                            _, _, r2 = compute_metrics(slopes_buf, truth)
                            frame_rs.append(r2)
                        avg_r2 = float(np.mean(frame_rs))
                        print(f'bg*{bgm} sx={sx} sy={sy} wexp={wexp} thr={tm} -> avgR2={avg_r2:.6f}')
                        if best is None or avg_r2 > best:
                            best = avg_r2
                            best_params = dict(bg_multiplier=bgm, shift_x=sx, shift_y=sy, weight_exp=wexp, thr_mul=tm)

    print('\nBEST params', best_params, 'LOO_R2', best)
    np.save(os.path.join(BUILD_DIR, 'weighted_cog_params.npy'), best_params)
    print('Saved params to build/weighted_cog_params.npy')

if __name__ == '__main__':
    main()
