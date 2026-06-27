"""
Capture synchronized pixel frames paired with gradient frames.

Modes:
- simulate: use `data/ERIS_NGS.fits` to generate many synthetic captures by
  sampling/augmenting existing pixel frames and pairing them with gradient
  frames to create a training set for offline model development.
- live: listen for external gradient triggers (ZMQ SUB) and invoke a camera
  capture command on each trigger; saves timestamped pairs to `build/`.

Usage examples:
  # simulate 1000 pairs from ERIS file
  ./venv/bin/python scripts/capture_synchronized.py --mode simulate --n_pairs 1000

  # live mode (instrument): run capture server that listens on tcp://*:5555
  ./venv/bin/python scripts/capture_synchronized.py --mode live --zmq_addr tcp://0.0.0.0:5555 --camera_cmd './capture_camera.sh {out_path}'

The script is intentionally minimal: adapt the `--camera_cmd` to whatever
camera SDK/utility your instrument uses. It writes paired arrays to
`build/captured_pairs.npz` with fields `pixel_paths` (list of saved files),
`gradient_idx`, and `timestamps`.
"""
import os
import argparse
import time
import numpy as np
import ctypes as ct

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
DATA_DIR = os.path.join(BASE, 'data')
AOTPY_FITS = os.path.join(DATA_DIR, 'ERIS_NGS.fits')

os.makedirs(BUILD_DIR, exist_ok=True)


def simulate_capture(n_pairs=1000, augment=True):
    import aotpy
    from scipy.ndimage import shift
    import ctypes as ct

    system = aotpy.AOSystem.read_from_file(AOTPY_FITS)
    wfs = system.wavefront_sensors[0]
    images = wfs.detector.pixel_intensities.data.astype(np.float32)
    gradients = wfs.measurements.data.astype(np.float32)  # (n_grad,2,n_valid)
    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_mask = valid_flags.astype(np.int32).flatten()
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)
    n_sub = mask.size
    n_valid = int(valid_mask.sum())
    sub_px = images.shape[1] // mask.shape[0]
    n_imgs = images.shape[0]
    n_grad = gradients.shape[0]

    label_to_valididx = np.empty(n_valid, dtype=np.int32)
    label_to_valididx[valid_labels] = np.arange(n_valid, dtype=np.int32)
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    valididx_to_label[label_to_valididx] = np.arange(n_valid, dtype=np.int32)

    lib = ct.CDLL(os.path.join(BASE, 'build', 'c_engine.so'))
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

    ref = wfs.ref_measurements.data.astype(np.float32)
    ref_flat = np.concatenate([ref[0], ref[1]]).astype(np.float32)

    # compute canonical slopes for the 10 images
    P_images = np.zeros((n_imgs, 2*n_valid), dtype=np.float32)
    buf = np.zeros(2*n_valid, dtype=np.float32)
    for i in range(n_imgs):
        img = images[i].astype(np.float32).copy()
        if getattr(lib, 'has_enhanced', False):
            lib.compute_slopes_enhanced(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px), ct.c_float(0.0), ct.c_float(0.0), ct.c_float(0.0))
        else:
            lib.compute_slopes(img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)), buf.ctypes.data_as(ct.POINTER(ct.c_float)), valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)), ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px))
        P_images[i] = buf - ref_flat

    # map each gradient frame to its nearest original image by slope
    T_grad = np.zeros((n_grad, 2*n_valid), dtype=np.float32)
    for j in range(n_grad):
        meas = gradients[j]
        T_grad[j] = np.concatenate([meas[0][valididx_to_label], meas[1][valididx_to_label]]) - ref_flat
    dists = np.sqrt(np.mean((T_grad[:, None, :] - P_images[None, :, :])**2, axis=2))
    grad_to_img = np.argmin(dists, axis=1)
    img_to_grads = [np.where(grad_to_img == i)[0] for i in range(n_imgs)]

    pixel_paths = []
    grad_idx = []
    timestamps = []
    rng = np.random.RandomState(0)

    for i in range(n_pairs):
        img_idx = rng.randint(0, n_imgs)
        grads = img_to_grads[img_idx]
        if grads.size == 0:
            g = rng.randint(0, n_grad)
        else:
            g = int(rng.choice(grads))
        im = images[img_idx].copy()
        if augment:
            dx = rng.uniform(-0.5, 0.5)
            dy = rng.uniform(-0.5, 0.5)
            im = shift(im, shift=(dy, dx), order=1, mode='reflect')
            im = im * rng.uniform(0.98, 1.02) + rng.normal(0, 1.0, size=im.shape)
        fname = os.path.join(BUILD_DIR, f'captured_{i:06d}.npy')
        np.save(fname, im.astype(np.float32))
        pixel_paths.append(fname)
        grad_idx.append(int(g))
        timestamps.append(time.time())
        if (i+1) % 100 == 0:
            print(f'Generated {i+1}/{n_pairs} simulated captures')
    np.savez(os.path.join(BUILD_DIR, 'captured_pairs.npz'), pixel_paths=pixel_paths, gradient_idx=np.array(grad_idx, dtype=np.int32), timestamps=np.array(timestamps, dtype=np.float64))
    print('Saved simulated captured pairs to build/captured_pairs.npz')


def live_capture(zmq_addr, camera_cmd, max_pairs=None, timeout=60.0):
    try:
        import zmq
    except Exception:
        raise RuntimeError('zmq required for live mode: pip install pyzmq')
    ctx = zmq.Context()
    sub = ctx.socket(zmq.SUB)
    sub.bind(zmq_addr)
    sub.setsockopt_string(zmq.SUBSCRIBE, '')

    pixel_paths = []
    grad_idx = []
    timestamps = []
    count = 0
    start = time.time()
    print('Live capture listening on', zmq_addr)
    try:
        while True:
            if max_pairs is not None and count >= max_pairs:
                break
            if time.time() - start > timeout and max_pairs is None:
                break
            try:
                msg = sub.recv_string(flags=zmq.NOBLOCK)
            except zmq.Again:
                time.sleep(0.001)
                continue
            # expect messages like: GRADIENT <idx> <timestamp>
            parts = msg.split()
            if len(parts) < 2:
                continue
            if parts[0].upper() != 'GRADIENT':
                continue
            gidx = int(parts[1])
            ts = float(parts[2]) if len(parts) >= 3 else time.time()
            out_path = os.path.join(BUILD_DIR, f'captured_live_{count:06d}.npy')
            cmd = camera_cmd.format(out_path=out_path, grad_idx=gidx, ts=ts)
            print('Running camera command:', cmd)
            r = os.system(cmd)
            if r != 0:
                print('Warning: camera command failed with code', r)
            pixel_paths.append(out_path)
            grad_idx.append(gidx)
            timestamps.append(ts)
            count += 1
    finally:
        sub.close()
        ctx.term()
    np.savez(os.path.join(BUILD_DIR, 'captured_pairs.npz'), pixel_paths=pixel_paths, gradient_idx=np.array(grad_idx, dtype=np.int32), timestamps=np.array(timestamps, dtype=np.float64))
    print('Saved live captured pairs to build/captured_pairs.npz')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['simulate', 'live'], default='simulate')
    p.add_argument('--n_pairs', type=int, default=1000)
    p.add_argument('--augment', action='store_true')
    p.add_argument('--zmq_addr', type=str, default='tcp://0.0.0.0:5555')
    p.add_argument('--camera_cmd', type=str, default="./capture_camera.sh {out_path}")
    p.add_argument('--max_pairs', type=int, default=None)
    p.add_argument('--timeout', type=float, default=60.0)
    args = p.parse_args()

    if args.mode == 'simulate':
        simulate_capture(args.n_pairs, augment=args.augment)
    else:
        live_capture(args.zmq_addr, args.camera_cmd, max_pairs=args.max_pairs, timeout=args.timeout)

if __name__ == '__main__':
    main()
