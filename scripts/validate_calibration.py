"""
validate_calibration.py
------------------------
Sanity checks for calibration matrices: shape, valid mask sum.
"""
import numpy as np, os, sys

DATA = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')
N_ZERNIKE, N_ACT, N_VALID = 20, 357, 316

def validate():
    errors = []
    g  = np.loadtxt(os.path.join(DATA,'g_plus.csv'),      delimiter=',')
    dm = np.loadtxt(os.path.join(DATA,'dm_coupling.csv'), delimiter=',')
    mk = np.loadtxt(os.path.join(DATA,'valid_mask.csv'),  delimiter=',')
    if g.shape  != (N_ZERNIKE, N_VALID*2): errors.append(f"G+ shape {g.shape}")
    if dm.shape != (N_ACT, N_ZERNIKE):     errors.append(f"DM shape {dm.shape}")
    if int(mk.sum()) != N_VALID:            errors.append(f"Mask sum {int(mk.sum())}")
    if errors:
        print("VALIDATION FAILED:"); [print(f"  - {e}") for e in errors]; sys.exit(1)
    else:
        print("All calibration matrices validated successfully.")

if __name__ == '__main__': validate()
