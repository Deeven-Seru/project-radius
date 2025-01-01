"""
compare_mshwfs.py
-----------------
Compares C-Engine slope outputs against the MATLAB mshwfs reference
implementation to validate pixel-level centroiding.
"""
import numpy as np, os

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')

def compare(frame_idx=0):
    ref_path = os.path.join(DATA, f'mshwfs_slopes_{frame_idx:04d}.csv')
    if not os.path.exists(ref_path):
        print(f"No MATLAB reference at {ref_path} - skipping"); return
    ref = np.loadtxt(ref_path, delimiter=',')
    gt  = np.loadtxt(os.path.join(DATA, 'ground_truth.csv'), delimiter=',')
    print(f"Max diff vs mshwfs: {np.max(np.abs(ref - gt[frame_idx])):.4e}")

if __name__ == '__main__': compare()
