"""
export_gplus_hcipy.py
---------------------
Generates calibration matrices required by the C-Engine using HCIPy:
  g_plus.csv      : pseudo-inverse interaction matrix
  valid_mask.csv  : binary subaperture validity mask
  ref_slopes.csv  : flat wavefront reference slopes in pixel units
"""
import numpy as np, os, ctypes as ct
import hcipy as hp
import argparse

parser = argparse.ArgumentParser(description="Export HCIPy calibration matrices.")
parser.add_argument('--rcond', type=float, default=1e-4, help="SVD regularization threshold for pinv (default: 1e-4).")
args = parser.parse_args()

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'hcipy_dataset')
os.makedirs(DATA_DIR, exist_ok=True)
BASE = os.path.join(os.path.dirname(__file__), '..')

print("Initializing HCIPy objects (Resolution = 800)...")
wavelength = 2.2e-6
pupil_diameter = 8.0
pupil_grid = hp.make_pupil_grid(800, pupil_diameter)
aperture = hp.make_circular_aperture(pupil_diameter)(pupil_grid)

num_lenslets = 80
shwfs_optics = hp.SquareShackHartmannWavefrontSensorOptics(pupil_grid, f_number=7500, num_lenslets=num_lenslets, pupil_diameter=pupil_diameter)

n_zernike = 1000
sub_px = 10
n_sub = num_lenslets**2

# Create mask of valid subapertures (fully illuminated)
# In HCIPy, the mla_grid tells us the centers of lenslets
# Evaluate aperture on the mla_grid
lenslet_illumination = hp.make_circular_aperture(pupil_diameter)(shwfs_optics.mla_grid)
valid_mask = (lenslet_illumination > 0.5).astype(np.int32)
n_valid = np.sum(valid_mask)
n_slopes = n_valid * 2

print(f"Number of valid subapertures: {n_valid}")

# Load C-Engine
lib = ct.CDLL(os.path.join(BASE, 'build', 'c_engine.so'))
lib.compute_slopes.argtypes = [ct.POINTER(ct.c_float)]*2 + [ct.POINTER(ct.c_int)] + [ct.c_int]*3
lib.compute_slopes.restype  = None

print("Computing reference slopes on flat wavefront using C-Engine...")
wf_flat = hp.Wavefront(aperture, wavelength)
shwfs_focal = shwfs_optics(wf_flat)
detector = hp.NoiselessDetector(shwfs_focal.grid)
detector.integrate(shwfs_focal, 1)
ref_img = detector.read_out().shaped
ref_img = (ref_img / ref_img.max() * 255).astype(np.float32)

ref_slopes = np.zeros(n_slopes, dtype=np.float32)
lib.compute_slopes(
    ref_img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
    ref_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
    valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
    ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px)
)

print("Computing Zernike Basis...")
zernike_basis = hp.make_zernike_basis(n_zernike, pupil_diameter, pupil_grid, starting_mode=1)

print("Building Interaction Matrix (1000 modes)...")
M_Zernike = np.zeros((n_slopes, n_zernike), dtype=np.float32)
amp = 1e-7 # small amplitude in meters
slopes_buf = np.zeros(n_slopes, dtype=np.float32)

for i in range(n_zernike):
    # Apply phase = mode * amp * (2pi/lambda)
    phase = zernike_basis[i] * amp * (2 * np.pi / wavelength)
    wf_poked = hp.Wavefront(aperture * np.exp(1j * phase), wavelength)
    
    shwfs_focal = shwfs_optics(wf_poked)
    detector = hp.NoiselessDetector(shwfs_focal.grid)
    detector.integrate(shwfs_focal, 1)
    poked_img = detector.read_out().shaped
    poked_img = (poked_img / poked_img.max() * 255).astype(np.float32)
    
    lib.compute_slopes(
        poked_img.flatten().ctypes.data_as(ct.POINTER(ct.c_float)),
        slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
        valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
        ct.c_int(n_sub), ct.c_int(n_valid), ct.c_int(sub_px)
    )
    M_Zernike[:, i] = (slopes_buf - ref_slopes) / amp

print("Inverting Zernike Interaction Matrix to obtain G+...")
g_plus = np.linalg.pinv(M_Zernike, rcond=args.rcond).astype(np.float32)

print("Saving matrices...")
np.savetxt(os.path.join(DATA_DIR, 'g_plus.csv'),      g_plus,      delimiter=',', fmt='%.8e')
np.savetxt(os.path.join(DATA_DIR, 'valid_mask.csv'),  valid_mask,  delimiter=',', fmt='%d')
np.savetxt(os.path.join(DATA_DIR, 'ref_slopes.csv'),  ref_slopes,  delimiter=',', fmt='%.8e')

# Copy dm_coupling from standard dataset just so the stress test doesn't crash
try:
    dm_c = np.loadtxt(os.path.join(DATA_DIR, '..', 'dataset', 'dm_coupling.csv'), delimiter=',')
    np.savetxt(os.path.join(DATA_DIR, 'dm_coupling.csv'), dm_c, delimiter=',', fmt='%.8e')
except Exception as e:
    print("Could not copy dm_coupling.csv:", e)

print(f"G+: {g_plus.shape} Valid: {n_valid}")
print("Done.")
