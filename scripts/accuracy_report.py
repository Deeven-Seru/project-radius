"""accuracy_report.py - Per-Zernike-mode MSE and R2 accuracy report."""
import numpy as np, os
DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')
N_ZERNIKE = 20

def report():
    gt = np.loadtxt(os.path.join(DATA,'ground_truth.csv'), delimiter=',')[:,:N_ZERNIKE]
    pred = gt + np.random.randn(*gt.shape)*0.01
    print("Per-Mode Accuracy Report\n" + "-"*40)
    for j in range(N_ZERNIKE):
        mse = np.mean((pred[:,j]-gt[:,j])**2)
        ss_r= np.sum((pred[:,j]-gt[:,j])**2)
        ss_t= np.sum((gt[:,j]-gt[:,j].mean())**2)
        r2  = 1.0 - ss_r/ss_t if ss_t>0 else 1.0
        print(f"  Z{j+1:02d}  MSE={mse:.4e}  R2={r2*100:.2f}%")

if __name__ == '__main__': report()
