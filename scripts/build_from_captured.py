"""
Build expanded_P.npy and expanded_T.npy from `build/captured_pairs.npz`.

For each saved pixel frame in `captured_pairs.npz` we compute C-engine slopes,
subtract the reference slopes from the AOTPy FITS, and save paired matrices
`build/expanded_P.npy` and `build/expanded_T.npy` suitable for training.
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


def load_aotpy():
    system = aotpy.AOSystem.read_from_file(AOTPY_FITS)
    wfs = system.wavefront_sensors[0]
    measurements = wfs.measurements.data.astype(np.float32)  # (n_grad,2,n_valid)
    reference = wfs.ref_measurements.data.astype(np.float32)
    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_mask = valid_flags.astype(np.int32).flatten()
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)
    n_sub = mask.size
    n_valid = int(valid_mask.sum())
    sub_px = wfs.detector.pixel_intensities.data.shape[1] // mask.shape[0]
    return {
        'measurements': measurements,
        'reference': reference,
        'valid_mask': valid_mask,
        'valid_labels': valid_labels,
        'n_sub': n_sub,
        'n_valid': n_valid,
        'sub_px': sub_px,
    }


def compute_slopes_for_image(lib, img, valid_mask, valididx_to_label, n_sub, n_valid, sub_px, reference):
    d = 2 * n_valid
    buf = np.zeros(d, dtype=np.float32)
    # choose enhanced if available
    if getattr(lib, 'has_weighted', False):
        bg = 0.0
        lib.compute_slopes_weighted(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg), ct.c_float(0.0), ct.c_float(0.0), ct.c_float(1.0), ct.c_float(0.0))
    elif getattr(lib, 'has_enhanced', False):
        bg = 0.0
        lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg), ct.c_float(0.0), ct.c_float(0.0))
    else:
        lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
    ref_flat = np.concatenate([reference[0], reference[1]]).astype(np.float32)
    buf -= ref_flat
    return buf


def main():
    os.makedirs(BUILD_DIR, exist_ok=True)
    captured_path = os.path.join(BUILD_DIR, 'captured_pairs.npz')
    if not os.path.exists(captured_path):
        raise FileNotFoundError('Please run scripts/capture_synchronized.py first to create build/captured_pairs.npz')
    data = np.load(captured_path, allow_pickle=True)
    pixel_paths = list(data['pixel_paths'])
    grad_idx = np.array(data['gradient_idx'], dtype=np.int32)

    lib = load_c_engine()
    aot = load_aotpy()
    valid_mask = aot['valid_mask']
    valid_labels = aot['valid_labels']
    n_sub = aot['n_sub']
    n_valid = aot['n_valid']
    sub_px = aot['sub_px']
    measurements = aot['measurements']
    reference = aot['reference']

    # derive mapping arrays
    label_to_valididx = np.empty(n_valid, dtype=np.int32)
    label_to_valididx[valid_labels] = np.arange(n_valid, dtype=np.int32)
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[label_to_valididx] = np.arange(n_valid, dtype=np.int32)

    n_samples = len(pixel_paths)
    d = 2 * n_valid
    P = np.zeros((n_samples, d), dtype=np.float32)
    T = np.zeros((n_samples, d), dtype=np.float32)

    for i, (p, gidx) in enumerate(zip(pixel_paths, grad_idx)):
        img = np.load(p).astype(np.float32)
        slopes = compute_slopes_for_image(lib, img, valid_mask, valididx_to_label, n_sub, n_valid, sub_px, reference)
        P[i] = slopes
        # get gradient truth (flattened & reordered)
        meas = measurements[int(gidx)]
        # meas shape (2, n_valid) already ordered by label -> need reorder
        T[i] = np.concatenate([meas[0][valididx_to_label], meas[1][valididx_to_label]]) - np.concatenate([reference[0], reference[1]])
        if (i+1) % 200 == 0 or (i+1) == n_samples:
            print(f'Processed {i+1}/{n_samples} captured frames')

    np.save(os.path.join(BUILD_DIR, 'expanded_P.npy'), P)
    np.save(os.path.join(BUILD_DIR, 'expanded_T.npy'), T)
    print('Saved expanded_P.npy and expanded_T.npy to build/')


if __name__ == '__main__':
    main()
