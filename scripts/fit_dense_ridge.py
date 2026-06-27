"""
Fit a dense ridge regression mapping from predicted slopes to truth slopes.
This allows cross-talk between all slope channels.
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
        P[fi] = slopes_buf.copy()
        truth = measurements[fi]
        T[fi] = np.concatenate([truth[:n_valid][valididx_to_label], truth[n_valid:][valididx_to_label]])
        times.append((time.time()-t0)*1000.0)

    # center columns to improve conditioning
    P_mean = np.mean(P, axis=0)
    T_mean = np.mean(T, axis=0)
    Pc = P - P_mean[np.newaxis, :]
    Tc = T - T_mean[np.newaxis, :]

    lambdas = [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0]
    best = None
    best_theta = None
    for lam in lambdas:
        print('Trying lambda', lam)
        # Theta = (P^T P + lam I)^{-1} P^T T
        PtP = Pc.T.dot(Pc)
        PtT = Pc.T.dot(Tc)
        reg = lam * np.eye(d, dtype=np.float32)
        try:
            Theta = np.linalg.solve(PtP + reg, PtT)
        except np.linalg.LinAlgError:
            Theta = np.linalg.solve(PtP + reg + 1e-12*np.eye(d, dtype=np.float32), PtT)
        # predict
        Tc_hat = Pc.dot(Theta)
        T_hat = Tc_hat + T_mean[np.newaxis, :]
        rs = [compute_metrics(T_hat[i], T[i])[2] for i in range(n_frames)]
        avg_r2 = float(np.mean(rs))
        print(' lambda', lam, 'avgR2', avg_r2)
        if best is None or avg_r2 > best:
            best = avg_r2
            best_theta = Theta.copy()
            best_lam = lam

    print('\nBEST dense ridge lambda', best_lam, 'avgR2', best)
    # final evaluate and save
    Theta = best_theta
    Tc_hat = Pc.dot(Theta)
    T_hat = Tc_hat + T_mean[np.newaxis, :]
    frame_metrics = [compute_metrics(T_hat[i], T[i]) for i in range(n_frames)]
    frame_metrics = np.array(frame_metrics, dtype=np.float32)
    avg = np.mean(frame_metrics, axis=0)
    print('Average MSE: {:.4e} RMSE: {:.4e} R2(avg): {:.4f}'.format(avg[0], avg[1], avg[2]))
    print('Latency (ms/frame) avg {:.2f} min {:.2f} max {:.2f}'.format(np.mean(times), np.min(times), np.max(times)))
    out = os.path.join(BASE, 'build', 'dense_theta.npy')
    np.save(out, Theta)
    print('Saved dense Theta to', out)


if __name__ == '__main__':
    main()
