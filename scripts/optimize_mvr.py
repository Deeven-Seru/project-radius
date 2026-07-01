import os
import sys
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

CAL_DATA_DIR = os.path.join(BASE, 'data', 'dataset')
VAL_DATA_DIR = os.path.join(BASE, 'data', 'dataset_validation')

def load_csv_robust(filepath, dtype):
    try:
        return np.loadtxt(filepath, delimiter=',').astype(dtype)
    except ValueError:
        return np.loadtxt(filepath).astype(dtype)

def main():
    print("="*80)
    print("MINIMUM VARIANCE RECONSTRUCTOR (MVR) OPTIMIZATION")
    print("="*80)
    
    # 1. Load Calibration Matrices
    g_plus      = load_csv_robust(os.path.join(CAL_DATA_DIR, 'g_plus.csv'),      np.float32)
    valid_mask  = load_csv_robust(os.path.join(CAL_DATA_DIR, 'valid_mask.csv'),  np.int32)
    
    n_valid = int(valid_mask.sum())
    n_slopes = 2 * n_valid
    n_zernike = g_plus.shape[0]
    
    # Derive the forward interaction matrix M by taking the pseudo-inverse of G+ with regularized threshold
    print("Deriving forward interaction matrix M from G+ with rcond=1e-3...")
    M = np.linalg.pinv(g_plus, rcond=1e-3).astype(np.float32)
    
    # 2. Load Ground Truth Zernikes from training dataset to compute covariance
    print("Loading training ground truth Zernikes to calculate covariance C_phi...")
    gt_train = load_csv_robust(os.path.join(CAL_DATA_DIR, 'ground_truth.csv'), np.float32)
    
    # Compute empirical Zernike covariance matrix
    # Add a tiny diagonal regularizer to ensure invertibility
    C_phi = np.cov(gt_train, rowvar=False).astype(np.float32)
    C_phi += np.eye(n_zernike, dtype=np.float32) * 1e-15
    
    # 3. Optimize the regularization parameter alpha (Noise Covariance Cn = alpha * I)
    print("Optimizing noise regularization parameter alpha...")
    
    # Search range from 1e-6 to 1.0 (since slopes are order 0.1, noise is order 0.05, variance is ~0.0025)
    alphas = [1e-6, 1e-5, 1e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2, 5e-2, 1e-1, 5e-1, 1.0]
    best_r2 = -np.inf
    best_alpha = None
    best_g_mvr = None
    
    # Load validation ground truth to test the reconstructor
    gt_val = load_csv_robust(os.path.join(VAL_DATA_DIR, 'ground_truth.csv'), np.float32)
    
    # Generate noisy validation slopes for the optimization test
    np.random.seed(42)
    val_slopes_clean = gt_val.dot(M.T)
    noise_std_slopes = 0.05
    val_slopes_noisy = val_slopes_clean + np.random.normal(0, noise_std_slopes, val_slopes_clean.shape)
    
    for alpha in alphas:
        # Compute MVR control matrix: G_MVR = (alpha * C_phi^-1 + M^T * M)^-1 * M^T
        try:
            inv_C_phi = np.linalg.inv(C_phi)
            term = alpha * inv_C_phi + M.T.dot(M)
            g_mvr = np.linalg.inv(term).dot(M.T)
        except np.linalg.LinAlgError:
            continue
            
        # Reconstruct validation Zernikes
        z_reconstructed = val_slopes_noisy.dot(g_mvr.T)
        
        # Calculate Temporal R2 score (excluding piston)
        ss_r = np.sum((z_reconstructed[:, 1:] - gt_val[:, 1:])**2)
        ss_t = np.sum((gt_val[:, 1:] - gt_val[:, 1:].mean(axis=0))**2)
        r2 = 1.0 - ss_r / ss_t if ss_t > 0 else 0.0
        
        print(f"  alpha = {alpha:.1e} | Validation R2 = {r2*100:.4f}%")
        
        if r2 > best_r2:
            best_r2 = r2
            best_alpha = alpha
            best_g_mvr = g_mvr
            
    print("—"*80)
    print(f"Optimal Alpha Found : {best_alpha:.1e}")
    print(f"Best Validation R2  : {best_r2*100:.4f}% (Noiseless ref: 98.70%)")
    
    # Save the optimized matrix
    mvr_path = os.path.join(CAL_DATA_DIR, 'g_plus_mvr.csv')
    np.savetxt(mvr_path, best_g_mvr, delimiter=',')
    print(f"Optimized MVR control matrix saved to: {mvr_path}")
    print("="*80)

if __name__ == '__main__':
    main()
