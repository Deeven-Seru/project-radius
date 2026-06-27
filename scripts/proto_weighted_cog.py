"""
Prototype weighted center-of-gravity centroiding in Python.
Per-subap background subtraction, thresholding, and weight exponent.
Performs LOO CV over the 10 images to choose parameters, reports metrics and latency.
"""
import os
import time
import ctypes as ct
import numpy as np
import aotpy

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')
AOTPY_FITS = os.path.join(BASE, 'data', 'ERIS_NGS.fits')


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
    return dict(images=images[:n_frames], measurements=measurements[:n_frames], ref=ref, mask=mask, valid_mask=valid_mask, valid_labels=valid_labels, n_sub=n_sub, n_valid=n_valid, sub_px=sub_px, n_frames=n_frames)


def get_subap_coords(mask, label):
    pos = np.argwhere(mask == label)
    if pos.size == 0:
        return None
    r, c = pos[0]
    return r, c


def compute_weighted_cog_frame(img, mask, valid_labels, sub_px, params):
    # params: dict(bg_mode='median'|'percentile', perc=10, thr_mul=0.0, weight_exp=1.0)
    n_valid = valid_labels.size
    out = np.zeros(2*n_valid, dtype=np.float32)
    for i, lab in enumerate(valid_labels):
        pos = np.argwhere(mask == lab)
        r, c = pos[0]
        rs = r*sub_px
        cs = c*sub_px
        sub = img[rs:rs+sub_px, cs:cs+sub_px].astype(np.float32)
        if params['bg_mode'] == 'median':
            bg = np.median(sub)
        else:
            bg = np.percentile(sub, params.get('perc', 10))
        sub0 = sub - bg
        sub0[sub0 < 0] = 0.0
        if params['thr_mul'] > 0.0:
            thr = np.mean(sub0) + params['thr_mul'] * np.std(sub0)
            mask_px = sub0 >= thr
            sub0 = sub0 * mask_px
        # weights
        w = np.power(sub0, params['weight_exp']) if params['weight_exp'] != 0.0 else (sub0 > 0).astype(np.float32)
        s = w.sum()
        if s <= 0:
            cx = 0.0
            cy = 0.0
        else:
            ys = np.arange(sub_px) - (sub_px-1)/2.0
            xs = np.arange(sub_px) - (sub_px-1)/2.0
            xx, yy = np.meshgrid(xs, ys)
            cx = np.sum(xx * w) / s
            cy = np.sum(yy * w) / s
        out[i] = cx
        out[i + n_valid] = cy
    return out


def compute_metrics(pred, truth):
    diff = pred - truth
    mse = np.mean(diff**2)
    rmse = np.sqrt(mse)
    ss_res = np.sum(diff**2)
    ss_tot = np.sum((truth - np.mean(truth))**2)
    r2 = 1.0 - (ss_res/ss_tot) if ss_tot > 0 else 1.0
    return mse, rmse, r2


def main():
    data = load_data()
    images = data['images']
    measurements = data['measurements']
    ref = data['ref']
    mask = data['mask']
    valid_labels = data['valid_labels']
    n_valid = data['n_valid']
    sub_px = data['sub_px']
    n_frames = data['n_frames']

    # reorder truths to valid-label row-major order
    valididx_to_label = np.empty(n_valid, dtype=np.int32)
    label_to_valididx = np.empty(n_valid, dtype=np.int32)
    label_to_valididx[valid_labels] = np.arange(n_valid, dtype=np.int32)
    valididx_to_label[label_to_valididx] = np.arange(n_valid, dtype=np.int32)
    ref_flat = np.concatenate([ref[0], ref[1]]).astype(np.float32)

    truths = np.zeros((n_frames, 2*n_valid), dtype=np.float32)
    for i in range(n_frames):
        t = measurements[i]
        truths[i] = np.concatenate([t[0][valididx_to_label], t[1][valididx_to_label]]) - ref_flat

    # grid
    bg_modes = ['median', 'percentile']
    percs = [5, 10]
    thr_muls = [0.0, 0.25, 0.5]
    w_exps = [0.0, 0.5, 1.0]

    best = None
    best_params = None

    # LOO CV
    for bg in bg_modes:
        for perc in percs:
            for thr in thr_muls:
                for wexp in w_exps:
                    params = dict(bg_mode=bg, perc=perc, thr_mul=thr, weight_exp=wexp)
                    r2s = []
                    for i in range(n_frames):
                        train_idx = [j for j in range(n_frames) if j != i]
                        # fit-free method; just evaluate on hold-out
                        img_test = images[i]
                        pred = compute_weighted_cog_frame(img_test, mask, valididx_to_label, sub_px, params)
                        _, _, r2 = compute_metrics(pred, truths[i])
                        r2s.append(r2)
                    avg_r2 = float(np.mean(r2s))
                    if best is None or avg_r2 > best:
                        best = avg_r2
                        best_params = params.copy()
                    print(f'bg={bg} perc={perc} thr={thr} wexp={wexp} LOO_R2={avg_r2:.6f}')

    print('\nBest params', best_params, 'LOO_R2', best)

    # evaluate chosen params and report per-frame and latency
    params = best_params
    frame_metrics = []
    t0 = time.time()
    for i in range(n_frames):
        st = time.time()
        pred = compute_weighted_cog_frame(images[i], mask, valididx_to_label, sub_px, params)
        mse, rmse, r2 = compute_metrics(pred, truths[i])
        frame_metrics.append((mse, rmse, r2))
        et = time.time() - st
        print(f'Frame {i+1:02d} R2={r2:.4f} latency={et*1000:.3f} ms')
    total = time.time() - t0
    avg = np.mean(np.array(frame_metrics), axis=0)
    print('\nPrototype summary:')
    print('Average MSE: {:.4e} RMSE: {:.4e} R2={:.4f}'.format(avg[0], avg[1], avg[2]))
    print('Avg per-frame python latency ms:', (total/n_frames)*1000.0)

    # save chosen params
    np.save(os.path.join(BUILD_DIR, 'weighted_cog_params.npy'), best_params)
    print('Saved params to build/')

if __name__ == '__main__':
    main()
