"""
export_gplus.py
---------------
Generates calibration matrices required by the C-Engine:
  g_plus.csv      : pseudo-inverse interaction matrix (n_zernike x n_slopes)
  dm_coupling.csv : DM influence matrix on Zernike basis (n_actuators x n_zernike)
  valid_mask.csv  : binary subaperture validity mask
  ref_slopes.csv  : flat wavefront reference slopes in pixel units
"""
import numpy as np, os, ctypes as ct
import argparse

parser = argparse.ArgumentParser(description="Export calibration matrices.")
parser.add_argument('--rcond', type=float, default=1e-2, help="SVD regularization threshold for pinv (default: 1e-2).")
parser.add_argument('--resolution', type=int, default=400, help="Resolution of the telescope pupil in pixels.")
parser.add_argument('--n_subap', type=int, default=20, help="Number of 1D subapertures for WFS and DM.")
args = parser.parse_args()

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')
os.makedirs(DATA_DIR, exist_ok=True)
BASE = os.path.join(os.path.dirname(__file__), '..')

from OOPAO.Telescope import Telescope
from OOPAO.Source import Source
from OOPAO.ShackHartmann import ShackHartmann
from OOPAO.DeformableMirror import DeformableMirror
from OOPAO.Zernike import Zernike

print(f"Initializing OOPAO objects (Resolution = {args.resolution}, Subapertures = {args.n_subap})...")
tel  = Telescope(resolution=args.resolution, diameter=8.0)
src  = Source('K', magnitude=8); src * tel
dm   = DeformableMirror(tel, nSubap=args.n_subap, mechCoupling=0.35)
wfs  = ShackHartmann(nSubap=args.n_subap, telescope=tel, lightRatio=0.5)

# Reset main source to clear Tip/Tilt calibration mask left by wfs.set_slopes_units()
src.reset()
src * tel

n_zernike = 55
n_slopes = wfs.nSignal
n_valid = wfs.nValidSubaperture
sub_px = args.resolution // args.n_subap

# Load C-Engine
lib = ct.CDLL(os.path.join(BASE, 'build', 'c_engine.so'))
lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3
lib.compute_slopes.restype  = None

valid_mask = wfs.valid_subapertures_1D.astype(np.int32)

print("Computing reference slopes on flat wavefront using C-Engine...")
src_cal = Source('K', magnitude=8); src_cal * tel
src_cal.OPD_no_pupil = np.zeros((tel.resolution, tel.resolution))
src_cal * tel * wfs
ref_img = wfs.cam.frame.astype(np.float32)
ref_slopes = np.zeros(n_slopes, dtype=np.float32)

print(f"ref_img shape: {ref_img.shape}, len: {len(ref_img.flatten())}", flush=True)
print(f"n_valid: {n_valid}, sub_px: {sub_px}, res: {args.resolution}", flush=True)

lib.compute_slopes(
    ref_img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
    ref_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
    valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
    ct.c_int(args.n_subap * args.n_subap), ct.c_int(n_valid), ct.c_int(sub_px)
)

print("Computing Zernike Basis (remove_piston = 0)...")
Z = Zernike(tel, J=n_zernike)
Z.computeZernike(tel, remove_piston=0)

print("Computing Zernike Interaction Matrix in C-Engine pixel units...")
M_Zernike = np.zeros((n_slopes, n_zernike), dtype=np.float32)
amp = 1e-6
slopes_buf = np.zeros(n_slopes, dtype=np.float32)

for i in range(n_zernike):
    opd = np.zeros((tel.resolution, tel.resolution), dtype=np.float32)
    opd[tel.pupil > 0] = Z.modes[:, i] * amp
    src_cal.OPD_no_pupil = opd
    src_cal * tel * wfs
    poked_img = wfs.cam.frame.astype(np.float32)
    lib.compute_slopes(
        poked_img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
        slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
        valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
        ct.c_int(args.n_subap * args.n_subap), ct.c_int(n_valid), ct.c_int(sub_px)
    )
    M_Zernike[:, i] = (slopes_buf - ref_slopes) / amp

print("Inverting Zernike Interaction Matrix to obtain G+...")
g_plus = np.linalg.pinv(M_Zernike, rcond=args.rcond).astype(np.float32)

print("Computing DM Influence Matrix and mapping to Zernikes...")
pupil_mask = tel.pupil.flatten() > 0
F = dm.modes[pupil_mask, :]
C_DM, residuals, rank, s = np.linalg.lstsq(F, Z.modes, rcond=None)
C_DM = C_DM.astype(np.float32)

print("Saving matrices...")
np.savetxt(os.path.join(DATA_DIR, 'g_plus.csv'),      g_plus,      delimiter=',', fmt='%.8e')
np.savetxt(os.path.join(DATA_DIR, 'dm_coupling.csv'), C_DM,        delimiter=',', fmt='%.8e')
np.savetxt(os.path.join(DATA_DIR, 'valid_mask.csv'),  valid_mask,  delimiter=',', fmt='%d')
np.savetxt(os.path.join(DATA_DIR, 'valid_subapertures.csv'), valid_mask, delimiter=',', fmt='%d')
np.savetxt(os.path.join(DATA_DIR, 'ref_slopes.csv'),  ref_slopes,  delimiter=',', fmt='%.8e')

print(f"G+: {g_plus.shape}  DM: {C_DM.shape}  Valid: {n_valid}")
print("Done.")
