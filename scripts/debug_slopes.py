"""debug_slopes.py - Slope vector field visualizer for centroiding verification."""
import numpy as np, matplotlib.pyplot as plt, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')

def plot_slopes(frame_idx=0, n_sub=20):
    gt   = np.loadtxt(os.path.join(DATA,'ground_truth.csv'), delimiter=',')
    mask = np.loadtxt(os.path.join(DATA,'valid_mask.csv'),   delimiter=',').reshape(n_sub,n_sub)
    n_valid = int(mask.sum())
    sx, sy  = gt[frame_idx,:n_valid], gt[frame_idx,n_valid:2*n_valid]
    ij = np.argwhere(mask)
    plt.figure(figsize=(7,7))
    for k,(i,j) in enumerate(ij): plt.quiver(j,i,sx[k],sy[k],color='cyan',scale=5,width=0.003)
    plt.imshow(mask, cmap='Greys', alpha=0.15, extent=[0,n_sub,n_sub,0])
    plt.title(f"Slopes frame {frame_idx:04d}", fontsize=13)
    out = os.path.join(DATA, f'slopes_debug_{frame_idx:04d}.png')
    plt.savefig(out, dpi=120); plt.close(); print(f"Saved {out}")

if __name__ == '__main__': plot_slopes(0)
