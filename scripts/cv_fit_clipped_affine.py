"""
Cross-validated regularized per-subap affine fit with coefficient clipping.
Performs leave-one-out CV over the 10 ERIS frames to choose ridge lambda and
clip ranges for gains and offsets. Applies chosen model to all frames and
reports metrics and latency.
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
    try:
        lib.compute_slopes_enhanced
        lib.has_enhanced = True
    except AttributeError:
        lib.has_enhanced = False
    lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.POINTER(ct.c_int), ct.c_int, ct.c_int, ct.c_int]
    lib.compute_slopes.restype = None
    if lib.has_enhanced:
        lib.compute_slopes_enhanced.argtypes = [ct.POINTER(ct.c_float), ct.POINTER(ct.c_float), ct.POINTER(ct.c_int), ct.c_int, ct.c_int, ct.c_int, ct.c_float, ct.c_float, ct.c_float]
        lib.compute_slopes_enhanced.restype = None
    # weighted variant
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


def fit_ridge_affine(P, T, lam):
    # Solve for [a,b] per channel with ridge; returns (2*n_channels,) coefs as (a,b)
    n_frames, d = P.shape
    coefs = np.zeros((d,2), dtype=np.float32)
    for j in range(d):
        X = np.vstack([P[:, j], np.ones(n_frames)]).T
        Y = T[:, j]
        XtX = X.T.dot(X)
        XtY = X.T.dot(Y)
        reg = lam * np.eye(2, dtype=np.float32)
        try:
            theta = np.linalg.solve(XtX + reg, XtY)
        except np.linalg.LinAlgError:
            theta = np.linalg.solve(XtX + reg + 1e-12*np.eye(2, dtype=np.float32), XtY)
        coefs[j] = theta
    return coefs


def apply_affine(P, coefs):
    gains = coefs[:, 0].astype(np.float32)
    offs = coefs[:, 1].astype(np.float32)
    return P * gains[np.newaxis, :] + offs[np.newaxis, :]


def main():
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

    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[:] = valid_labels
    reordered_ref = np.concatenate([ref[:n_valid][valididx_to_label], ref[n_valid:][valididx_to_label]])

    d = 2 * n_valid
    P = np.zeros((n_frames, d), dtype=np.float32)
    T = np.zeros((n_frames, d), dtype=np.float32)

    slopes_buf = np.zeros(d, dtype=np.float32)
    bg_multiplier = 2.0
    shift_x = 0.0
    shift_y = 0.0
    bg_base = 0.0
    if dark is not None:
        bg_base = float(np.median(dark))

    for fi in range(n_frames):
        img = images[fi].astype(np.float32).copy()
        if dark is not None:
            img = img - dark
        if sky is not None:
            img = img - sky
        img[img < 0] = 0.0
        if weight is not None:
            img = img * weight
        # prefer weighted implementation if available
        try:
            weighted_params = np.load(os.path.join(BUILD_DIR, 'weighted_cog_params.npy'), allow_pickle=True).item()
        except Exception:
            weighted_params = None
        if getattr(lib, 'has_weighted', False) or getattr(lib, 'has_compute_slopes_weighted', False):
            weight_exp = 1.0
            thr_mul = 0.0
            if weighted_params is not None:
                weight_exp = float(weighted_params.get('weight_exp', 1.0))
                thr_mul = float(weighted_params.get('thr_mul', 0.0))
            lib.compute_slopes_weighted(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_base*bg_multiplier), ct.c_float(shift_x), ct.c_float(shift_y), ct.c_float(weight_exp), ct.c_float(thr_mul))
        elif lib.has_enhanced:
            lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_base*bg_multiplier), ct.c_float(shift_x), ct.c_float(shift_y))
        else:
            lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
        slopes_buf -= reordered_ref
        P[fi] = slopes_buf.copy()
        truth = measurements[fi]
        T[fi] = np.concatenate([truth[:n_valid][valididx_to_label], truth[n_valid:][valididx_to_label]])

    # Grid search over lambda and clipping ranges with LOO CV
    lambdas = [0.0, 1e-4, 1e-3, 1e-2]
    gain_clips = [(0.2, 2.0), (0.5, 1.5), (0.8, 1.2)]
    offset_clips = [(-0.5,0.5), (-0.2,0.2), (-0.05,0.05)]

    best = None
    best_setting = None

    # Precompute folds
    folds = []
    for i in range(n_frames):
        train_idx = [j for j in range(n_frames) if j != i]
        test_idx = [i]
        folds.append((train_idx, test_idx))

    for lam in lambdas:
        for gmin, gmax in gain_clips:
            for omin, omax in offset_clips:
                rs = []
                for train_idx, test_idx in folds:
                    P_train = P[train_idx]
                    T_train = T[train_idx]
                    coefs = fit_ridge_affine(P_train, T_train, lam)
                    # clip gains and offsets
                    coefs_clipped = coefs.copy()
                    gains = coefs_clipped[:,0]
                    offs = coefs_clipped[:,1]
                    gains = np.clip(gains, gmin, gmax)
                    offs = np.clip(offs, omin, omax)
                    coefs_clipped[:,0] = gains
                    coefs_clipped[:,1] = offs
                    P_test = P[test_idx]
                    T_test = T[test_idx]
                    pred = apply_affine(P_test, coefs_clipped)
                    _, _, r2 = compute_metrics(pred[0], T_test[0])
                    rs.append(r2)
                avg_r2 = float(np.mean(rs))
                if best is None or avg_r2 > best:
                    best = avg_r2
                    best_setting = (lam, (gmin,gmax), (omin,omax))
                print(f'lam={lam} gain_clip=({gmin},{gmax}) off_clip=({omin},{omax}) LOO_avgR2={avg_r2:.6f}')

    print('\nBEST setting', best_setting, 'LOO R2', best)
    # Refit on all frames with best setting and evaluate
    lam, (gmin,gmax), (omin,omax) = best_setting
    coefs = fit_ridge_affine(P, T, lam)
    coefs[:,0] = np.clip(coefs[:,0], gmin, gmax)
    coefs[:,1] = np.clip(coefs[:,1], omin, omax)
    P_adj = apply_affine(P, coefs)
    frame_metrics = [compute_metrics(P_adj[i], T[i]) for i in range(n_frames)]
    frame_metrics = np.array(frame_metrics, dtype=np.float32)
    avg = np.mean(frame_metrics, axis=0)
    # latency: compute per-frame post-processing time (apply_affine cost)
    t0 = time.time()
    for _ in range(50):
        _ = apply_affine(P[:1], coefs)
    post_ms = (time.time()-t0)/50*1000.0

    print('\nFinal eval after clipping/refit:')
    print('Average MSE: {:.4e} RMSE: {:.4e} R2(avg): {:.4f}'.format(avg[0], avg[1], avg[2]))
    print('Post-process latency ms (avg over 50 runs): {:.6f}'.format(post_ms))
    out = os.path.join(BASE, 'build', 'clipped_affine_coefs.npy')
    np.save(out, coefs)
    print('Saved coefs to', out)

if __name__ == '__main__':
    main()
