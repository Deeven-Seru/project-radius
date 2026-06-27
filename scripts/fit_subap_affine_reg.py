"""
Fit per-subaperture regularized affine transforms (scale + offset) to map
C-engine predictions to AOTPy truths. Searches over ridge lambda to avoid
extreme coefficients and reports final accuracy and latency.
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

    # mapping for label order
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[:] = valid_labels
    reordered_ref = np.concatenate([ref[:n_valid][valididx_to_label], ref[n_valid:][valididx_to_label]])

    # compute raw preds
    preds = np.zeros((n_frames, 2*n_valid), dtype=np.float32)
    truths = np.zeros_like(preds)
    slopes_buf = np.zeros(2*n_valid, dtype=np.float32)

    bg_multiplier = 2.0
    shift_x = 0.0
    shift_y = 0.0
    bg_base = 0.0
    if dark is not None:
        bg_base = float(np.median(dark))

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
            lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_base*bg_multiplier), ct.c_float(shift_x), ct.c_float(shift_y))
        else:
            lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
        slopes_buf -= reordered_ref
        preds[fi] = slopes_buf.copy()
        truth = measurements[fi]
        truths[fi] = np.concatenate([truth[:n_valid][valididx_to_label], truth[n_valid:][valididx_to_label]])
        times.append((time.time()-t0)*1000.0)

    # Fit per-subap affine using ridge regularization across frames
    lambdas = [0.0, 1e-4, 1e-3, 1e-2, 1e-1, 1.0]
    best = None
    best_params = None
    for lam in lambdas:
        A = np.zeros((n_frames, 2), dtype=np.float32)
        coefs = np.zeros((2*n_valid, 2), dtype=np.float32)  # [a,b] per channel
        preds_trans = np.zeros_like(preds)
        for j in range(2*n_valid):
            X = np.vstack([preds[:, j], np.ones(n_frames)]).T  # (n_frames,2)
            Y = truths[:, j]
            # ridge: (X^T X + lam*I)^{-1} X^T Y
            XtX = X.T.dot(X)
            XtY = X.T.dot(Y)
            reg = lam * np.eye(2, dtype=np.float32)
            try:
                theta = np.linalg.solve(XtX + reg, XtY)
            except np.linalg.LinAlgError:
                # numerical fallback: add tiny jitter
                jitter = 1e-12
                theta = np.linalg.solve(XtX + reg + jitter * np.eye(2, dtype=np.float32), XtY)
            coefs[j] = theta
            preds_trans[:, j] = X.dot(theta)
        # evaluate
        rs = [compute_metrics(preds_trans[i], truths[i])[2] for i in range(n_frames)]
        avg_r2 = float(np.mean(rs))
        print(f'lambda={lam} avgR2={avg_r2:.6f}')
        if best is None or avg_r2 > best:
            best = avg_r2
            best_params = (lam, coefs.copy(), preds_trans.copy())

    lam, coefs, preds_trans = best_params
    frame_metrics = [compute_metrics(preds_trans[i], truths[i]) for i in range(n_frames)]
    frame_metrics = np.array(frame_metrics, dtype=np.float32)
    avg = np.mean(frame_metrics, axis=0)

    print('\nBEST lambda', lam)
    print('Average MSE: {:.4e}  RMSE: {:.4e}  R2(avg): {:.4f}'.format(avg[0], avg[1], avg[2]))
    print('Latency (ms/frame) avg {:.2f} min {:.2f} max {:.2f}'.format(np.mean(times), np.min(times), np.max(times)))

    # Save coefs
    out = os.path.join(BASE, 'build', 'subap_affine_coefs.npy')
    np.save(out, coefs)
    print('Saved coefficients to', out)


if __name__ == '__main__':
    main()
