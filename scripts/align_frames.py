"""
Align gradient frames to pixel frames by slope similarity.
Produces `build/frame_alignment.npy`, `build/expanded_P.npy`, `build/expanded_T.npy`.
"""
import os
import ctypes as ct
import numpy as np
import aotpy

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
AOTPY_FITS = os.path.join(BASE, 'data', 'ERIS_NGS.fits')


def load_c_engine():
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
    measurements = wfs.measurements.data.astype(np.float32)  # shape (n_grad,2,n_valid)
    ref = wfs.ref_measurements.data.astype(np.float32)
    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_mask = valid_flags.astype(np.int32).flatten()
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)
    n_sub = mask.size
    n_valid = int(valid_mask.sum())
    sub_px = images.shape[1] // mask.shape[0]
    return {
        'images': images,
        'measurements': measurements,
        'reference': ref,
        'valid_mask': valid_mask,
        'valid_labels': valid_labels,
        'n_sub': n_sub,
        'n_valid': n_valid,
        'sub_px': sub_px,
    }


def reorder_measurements_flat(meas2d, valididx_to_label):
    # meas2d: (..., 2, n_valid)
    n_frames = meas2d.shape[0]
    n_valid = valididx_to_label.shape[0]
    out = np.zeros((n_frames, 2*n_valid), dtype=np.float32)
    for i in range(n_frames):
        t = meas2d[i]
        out[i] = np.concatenate([t[0][valididx_to_label], t[1][valididx_to_label]])
    return out


def compute_image_slopes(lib, images, reference_slopes, valid_mask, valididx_to_label, n_sub, n_valid, sub_px):
    n_imgs = images.shape[0]
    d = 2 * n_valid
    P = np.zeros((n_imgs, d), dtype=np.float32)
    buf = np.zeros(d, dtype=np.float32)
    reordered_ref = np.concatenate([reference_slopes[0], reference_slopes[1]]).astype(np.float32)
    for i in range(n_imgs):
        img = images[i].astype(np.float32).copy()
        if getattr(lib, 'has_weighted', False) or getattr(lib, 'has_compute_slopes_weighted', False):
            bg_thresh = 0.0
            lib.compute_slopes_weighted(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_thresh), ct.c_float(0.0), ct.c_float(0.0), ct.c_float(1.0), ct.c_float(0.0))
        elif getattr(lib, 'has_enhanced', False):
            bg_thresh = 0.0
            lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_thresh), ct.c_float(0.0), ct.c_float(0.0))
        else:
            lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
        buf -= reordered_ref
        P[i] = buf.copy()
    return P


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    lib = load_c_engine()
    data = load_data()
    images = data['images']
    measurements = data['measurements']
    reference = data['reference']
    valid_mask = data['valid_mask']
    valid_labels = data['valid_labels']
    n_sub = data['n_sub']
    n_valid = data['n_valid']
    sub_px = data['sub_px']

    # derive valididx<->label mapping
    label_to_valididx = np.empty(n_valid, dtype=np.int32)
    label_to_valididx[valid_labels] = np.arange(n_valid, dtype=np.int32)
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[label_to_valididx] = np.arange(n_valid, dtype=np.int32)

    # compute slopes from images (n_images x d)
    P_images = compute_image_slopes(lib, images, reference, valid_mask, valididx_to_label, n_sub, n_valid, sub_px)

    # reorder full gradient measurements (n_grad x d)
    n_grad = measurements.shape[0]
    T_grad = reorder_measurements_flat(measurements, valididx_to_label)
    # subtract reference from truths
    ref_flat = np.concatenate([reference[0], reference[1]]).astype(np.float32)
    T_grad = T_grad - ref_flat[np.newaxis, :]

    # For each gradient frame, find nearest image by RMSE
    # compute distances matrix (n_grad x n_images)
    # use efficient broadcasting
    diffs = T_grad[:, None, :] - P_images[None, :, :]
    dists = np.sqrt(np.mean(diffs**2, axis=2))
    mapping = np.argmin(dists, axis=1).astype(np.int32)

    np.save(os.path.join(BUILD_DIR, 'frame_alignment.npy'), mapping)
    # expanded datasets
    P_exp = P_images[mapping]
    T_exp = T_grad.copy()
    np.save(os.path.join(BUILD_DIR, 'expanded_P.npy'), P_exp)
    np.save(os.path.join(BUILD_DIR, 'expanded_T.npy'), T_exp)
    print('Saved frame_alignment (n_grad -> n_images), expanded P/T to build/')

if __name__ == '__main__':
    main()
