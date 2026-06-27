"""
Generate augmented pixel images (shifts + intensity scale + noise), compute
C-engine slopes for them, align gradient frames to the augmented images, and
save expanded training arrays for downstream training.
"""
import os
import ctypes as ct
import numpy as np
import aotpy
import math

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
AOTPY_FITS = os.path.join(BASE, 'data', 'ERIS_NGS.fits')

os.makedirs(BUILD_DIR, exist_ok=True)


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
    reference = wfs.ref_measurements.data.astype(np.float32)
    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_mask = valid_flags.astype(np.int32).flatten()
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)
    n_sub = mask.size
    n_valid = int(valid_mask.sum())
    sub_px = images.shape[1] // mask.shape[0]
    return images, measurements, reference, valid_mask, valid_labels, n_sub, n_valid, sub_px


def shift_image(img, dx, dy):
    # dx,dy fractional shifts. Use simple bilinear interpolation.
    h, w = img.shape
    x = np.arange(w)
    y = np.arange(h)
    # create mesh
    xx, yy = np.meshgrid(x, y)
    xq = xx - dx
    yq = yy - dy
    x0 = np.floor(xq).astype(int)
    y0 = np.floor(yq).astype(int)
    x1 = x0 + 1
    y1 = y0 + 1
    x0 = np.clip(x0, 0, w-1)
    x1 = np.clip(x1, 0, w-1)
    y0 = np.clip(y0, 0, h-1)
    y1 = np.clip(y1, 0, h-1)
    Ia = img[y0, x0]
    Ib = img[y1, x0]
    Ic = img[y0, x1]
    Id = img[y1, x1]
    wa = (x1 - xq) * (y1 - yq)
    wb = (x1 - xq) * (yq - y0)
    wc = (xq - x0) * (y1 - yq)
    wd = (xq - x0) * (yq - y0)
    out = wa*Ia + wb*Ib + wc*Ic + wd*Id
    return out


def compute_image_slopes(lib, images, reference, valid_mask, valididx_to_label, n_sub, n_valid, sub_px):
    n_imgs = images.shape[0]
    d = 2 * n_valid
    P = np.zeros((n_imgs, d), dtype=np.float32)
    buf = np.zeros(d, dtype=np.float32)
    ref_flat = np.concatenate([reference[0], reference[1]]).astype(np.float32)
    for i in range(n_imgs):
        img = images[i].astype(np.float32)
        if getattr(lib, 'has_weighted', False):
            bg_thresh = 0.0
            lib.compute_slopes_weighted(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_thresh), ct.c_float(0.0), ct.c_float(0.0), ct.c_float(1.0), ct.c_float(0.0))
        elif getattr(lib, 'has_enhanced', False):
            bg_thresh = 0.0
            lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(bg_thresh), ct.c_float(0.0), ct.c_float(0.0))
        else:
            lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
        buf -= ref_flat
        P[i] = buf.copy()
    return P


def main():
    images, measurements, reference, valid_mask, valid_labels, n_sub, n_valid, sub_px = load_data()
    lib = load_c_engine()
    # mapping
    label_to_valididx = np.empty(n_valid, dtype=np.int32)
    label_to_valididx[valid_labels] = np.arange(n_valid, dtype=np.int32)
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[label_to_valididx] = np.arange(n_valid, dtype=np.int32)

    base_n = images.shape[0]
    # augmentation parameters
    per_image = 50  # generate 50 variants per original image => 500 total
    rng = np.random.RandomState(0)
    aug_images = []
    for i in range(base_n):
        orig = images[i]
        for j in range(per_image):
            dx = rng.uniform(-0.8, 0.8)
            dy = rng.uniform(-0.8, 0.8)
            scale = rng.uniform(0.95, 1.05)
            noise_sigma = rng.uniform(0.0, 2.0)
            shifted = shift_image(orig, dx, dy)
            aug = shifted * scale + rng.normal(0.0, noise_sigma, size=shifted.shape)
            aug[aug < 0] = 0.0
            aug_images.append(aug.astype(np.float32))
    aug_images = np.stack(aug_images, axis=0)
    np.save(os.path.join(BUILD_DIR, 'augmented_images.npy'), aug_images)
    print('Generated', aug_images.shape[0], 'augmented images')

    # compute slopes for augmented images
    P_aug = compute_image_slopes(lib, aug_images, reference, valid_mask, valididx_to_label, n_sub, n_valid, sub_px)

    # reorder gradient measurements
    n_grad = measurements.shape[0]
    T_grad = np.zeros((n_grad, 2*n_valid), dtype=np.float32)
    ref_flat = np.concatenate([reference[0], reference[1]]).astype(np.float32)
    for i in range(n_grad):
        t = measurements[i]
        T_grad[i] = np.concatenate([t[0][valididx_to_label], t[1][valididx_to_label]]) - ref_flat

    # match each gradient frame to best augmented image
    diffs = T_grad[:, None, :] - P_aug[None, :, :]
    dists = np.sqrt(np.mean(diffs**2, axis=2))
    mapping = np.argmin(dists, axis=1).astype(np.int32)
    np.save(os.path.join(BUILD_DIR, 'frame_alignment_aug.npy'), mapping)
    P_exp = P_aug[mapping]
    T_exp = T_grad.copy()
    np.save(os.path.join(BUILD_DIR, 'expanded_P_aug.npy'), P_exp)
    np.save(os.path.join(BUILD_DIR, 'expanded_T_aug.npy'), T_exp)
    print('Saved augmented expanded P/T and alignment in build/')

if __name__ == '__main__':
    main()
