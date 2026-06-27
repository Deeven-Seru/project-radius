"""
Train PCA-based low-rank ridge regressor mapping P -> T with CV.
Loads `build/expanded_P.npy` and `build/expanded_T.npy` produced by `align_frames.py`.
Saves `build/lowrank_theta.npz` containing PCA components, mean, and ridge weights.
"""
import os
import numpy as np
from math import isfinite

def pca_reduce(X, n_components):
    # center
    mean = np.mean(X, axis=0)
    Xc = X - mean
    # SVD
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    components = Vt[:n_components]
    Xred = np.dot(Xc, components.T)
    return Xred, components, mean

def ridge_fit(X, Y, alpha):
    # X: n x k, Y: n x m
    n, k = X.shape
    XtX = X.T.dot(X)
    reg = alpha * np.eye(k, dtype=X.dtype)
    A = XtX + reg
    XtY = X.T.dot(Y)
    try:
        W = np.linalg.solve(A, XtY)
    except np.linalg.LinAlgError:
        W = np.linalg.lstsq(A + 1e-12*np.eye(k), XtY, rcond=None)[0]
    return W

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

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE, 'build')


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
        raise FileNotFoundError('Run scripts/align_frames.py first to produce expanded datasets.')
    P = np.load(P_path)
    T = np.load(T_path)
    n_samples = P.shape[0]
    # use 5-fold CV
    kf_splits = kfold_indices(n_samples, n_splits=5, seed=0)

    components_grid = [5, 10, 20, 50, 100]
    alpha_grid = [0.0, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1]

    best = None
    best_setting = None

    for n_comp in components_grid:
        # PCA on full P; we'll re-fit PCA inside CV to avoid leakage? here we fit on train in each fold
        for alpha in alpha_grid:
            r2s = []
            for train_idx, test_idx in kf_splits:
                P_tr = P[train_idx]
                P_te = P[test_idx]
                T_tr = T[train_idx]
                T_te = T[test_idx]
                P_tr_red, comps, meanP = pca_reduce(P_tr, n_comp)
                P_te_red = (P_te - meanP).dot(comps.T)
                W = ridge_fit(P_tr_red, T_tr, alpha)
                pred = P_te_red.dot(W)
                _, _, r2 = compute_metrics(pred, T_te)
                r2s.append(r2)
            avg_r2 = float(np.mean(r2s))
            print(f'PCA={n_comp} alpha={alpha} CV_R2={avg_r2:.6f}')
            if best is None or avg_r2 > best:
                best = avg_r2
                best_setting = (n_comp, alpha)
    print('\nBest setting', best_setting, 'CV_R2', best)

    # Refit on all data using best setting
    n_comp, alpha = best_setting
    P_reduced, comps, meanP = pca_reduce(P, n_comp)
    W = ridge_fit(P_reduced, T, alpha)
    intercept = np.mean(T, axis=0)  # since P_reduced is zero-mean
    out_path = os.path.join(BUILD_DIR, 'lowrank_theta.npz')
    np.savez(out_path, pca_components=comps, pca_mean=meanP, ridge_W=W, ridge_intercept=intercept)
    print('Saved lowrank model to', out_path)

    pred_full = P_reduced.dot(W)
    mse, rmse, r2 = compute_metrics(pred_full, T)
    print('Train-fit metrics: MSE={:.4e} RMSE={:.4e} R2={:.6f}'.format(mse, rmse, r2))

if __name__ == '__main__':
    main()
