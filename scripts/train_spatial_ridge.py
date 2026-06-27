"""
Train PCA + spatial-regularized ridge regressor mapping P -> T.
Penalty: ||XW - Y||^2 + alpha ||W||_F^2 + beta trace(W^T L_m W)
where L_m is block-diagonal Laplacian for the x/y outputs built from subap positions.

Saves `build/spatial_theta.npz` with PCA components, mean, and W.
"""
import os
import numpy as np
from math import isfinite
import aotpy

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')


def kfold_indices(n, n_splits=5, seed=0):
    idx = np.arange(n)
    rng = np.random.RandomState(seed)
    rng.shuffle(idx)
    sizes = [(n // n_splits) + (1 if i < (n % n_splits) else 0) for i in range(n_splits)]
    splits = []
    cur = 0
    for s in sizes:
        test = idx[cur:cur+s]
        train = np.setdiff1d(idx, test)
        splits.append((train, test))
        cur += s
    return splits


def pca_reduce(X, n_components):
    mean = np.mean(X, axis=0)
    Xc = X - mean
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = Vt[:n_components]
    Xred = Xc.dot(comps.T)
    return Xred, comps, mean


def build_subap_laplacian():
    # load mask from AOTPy to compute subap center positions
    system = aotpy.AOSystem.read_from_file(os.path.join(BASE, 'data', 'ERIS_NGS.fits'))
    wfs = system.wavefront_sensors[0]
    mask = wfs.subaperture_mask.data
    valid_flags = (mask >= 0)
    valid_labels = mask.flatten()[valid_flags.flatten()].astype(np.int32)
    n_valid = valid_labels.size
    # compute centroid of pixels for each valid label to get coordinates
    h, w = mask.shape
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
    centers = np.zeros((n_valid, 2), dtype=np.float32)
    for i, lab in enumerate(valid_labels):
        ys = yy.flatten()[mask.flatten() == lab]
        xs = xx.flatten()[mask.flatten() == lab]
        centers[i, 0] = np.mean(ys) if ys.size else 0.0
        centers[i, 1] = np.mean(xs) if xs.size else 0.0

    # build adjacency weights via RBF of distances; then Laplacian
    from scipy.spatial.distance import cdist
    D = cdist(centers, centers)
    sigma = np.median(D[D > 0])
    if sigma <= 0:
        sigma = 1.0
    W = np.exp(-(D**2) / (2 * sigma**2))
    np.fill_diagonal(W, 0.0)
    deg = np.sum(W, axis=1)
    L = np.diag(deg) - W
    return L


def solve_spatial_ridge(X, Y, alpha, beta, L_subap):
    # X: n x k, Y: n x m (m = 2*n_valid), L_subap: n_valid x n_valid
    n, k = X.shape
    m = Y.shape[1]
    A = X.T.dot(X) + alpha * np.eye(k, dtype=X.dtype)
    # build L_m = block_diag(L_subap, L_subap)
    L_m = np.block([[L_subap, np.zeros_like(L_subap)], [np.zeros_like(L_subap), L_subap]])
    # eigendecompose L_m
    eigvals, U = np.linalg.eigh(L_m)
    # precompute B = X^T Y
    B = X.T.dot(Y)
    # compute B' = B U
    Bp = B.dot(U)
    # for each eigencomponent solve (A + beta * eigval * I) w'_j = b'_j
    Wp = np.zeros_like(Bp)
    for j in range(m):
        Aj = A + beta * eigvals[j] * np.eye(k, dtype=A.dtype)
        try:
            Wp[:, j] = np.linalg.solve(Aj, Bp[:, j])
        except np.linalg.LinAlgError:
            Wp[:, j] = np.linalg.lstsq(Aj + 1e-12*np.eye(k), Bp[:, j], rcond=None)[0]
    # recover W = Wp * U^T
    W = Wp.dot(U.T)
    return W


def compute_metrics(pred, truth):
    diff = pred - truth
    mse = np.mean(diff**2)
    rmse = np.sqrt(mse)
    ss_res = np.sum(diff**2)
    ss_tot = np.sum((truth - np.mean(truth))**2)
    r2 = 1.0 - (ss_res/ss_tot) if ss_tot > 0 else 1.0
    return mse, rmse, r2


def main():
    P_path = os.path.join(BUILD_DIR, 'expanded_P.npy')
    T_path = os.path.join(BUILD_DIR, 'expanded_T.npy')
    if not os.path.exists(P_path) or not os.path.exists(T_path):
        raise FileNotFoundError('Run scripts/build_from_captured.py first to produce expanded_P/expanded_T')
    P = np.load(P_path)
    T = np.load(T_path)
    n_samples = P.shape[0]

    kf = kfold_indices(n_samples, n_splits=5, seed=0)

    comps_grid = [10, 20, 50]
    alpha_grid = [1e-6, 1e-4, 1e-2]
    beta_grid = [0.0, 1e-3, 1e-2, 1e-1]

    L_subap = build_subap_laplacian()

    best = None
    best_setting = None

    for n_comp in comps_grid:
        for alpha in alpha_grid:
            for beta in beta_grid:
                r2s = []
                for train_idx, test_idx in kf:
                    P_tr = P[train_idx]
                    P_te = P[test_idx]
                    T_tr = T[train_idx]
                    T_te = T[test_idx]
                    P_tr_red, comps, meanP = pca_reduce(P_tr, n_comp)
                    P_te_red = (P_te - meanP).dot(comps.T)
                    # solve spatial ridge
                    W = solve_spatial_ridge(P_tr_red, T_tr, alpha, beta, L_subap)
                    pred = P_te_red.dot(W)
                    _, _, r2 = compute_metrics(pred, T_te)
                    r2s.append(r2)
                avg_r2 = float(np.mean(r2s))
                print(f'comp={n_comp} alpha={alpha} beta={beta} CV_R2={avg_r2:.6f}')
                if best is None or avg_r2 > best:
                    best = avg_r2
                    best_setting = (n_comp, alpha, beta)

    print('Best setting', best_setting, 'CV_R2', best)
    n_comp, alpha, beta = best_setting
    P_red, comps, meanP = pca_reduce(P, n_comp)
    W = solve_spatial_ridge(P_red, T, alpha, beta, L_subap)
    out_path = os.path.join(BUILD_DIR, 'spatial_theta.npz')
    np.savez(out_path, pca_components=comps, pca_mean=meanP, W=W)
    print('Saved spatial model to', out_path)
    pred_full = P_red.dot(W)
    mse, rmse, r2 = compute_metrics(pred_full, T)
    print('Train-fit metrics: MSE={:.4e} RMSE={:.4e} R2={:.6f}'.format(mse, rmse, r2))


if __name__ == '__main__':
    main()
