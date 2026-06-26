import os
import sys

print("Installing hcipy...")
os.system("pip install hcipy")

import numpy as np
import hcipy as hp

DATA_DIR = '/kaggle/working/hcipy_dataset'
os.makedirs(DATA_DIR, exist_ok=True)

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

detector_lenslet_grid = hp.make_pupil_grid(num_lenslets, pupil_diameter)
lenslet_illumination = hp.make_circular_aperture(pupil_diameter)(detector_lenslet_grid)
valid_mask = (lenslet_illumination > 0.5).astype(np.int32)
n_valid = np.sum(valid_mask)
n_slopes = n_valid * 2

print(f"Number of valid subapertures: {n_valid}")

def compute_slopes_py(img_data_flat):
    N_1d = int(np.sqrt(n_sub))
    img_data_2d = img_data_flat.reshape((sub_px*N_1d, sub_px*N_1d))
    cx, cy = [], []
    for k in range(n_sub):
        if not valid_mask[k]: continue
        row0 = (k // N_1d) * sub_px
        col0 = (k % N_1d) * sub_px
        sub_img = img_data_2d[row0:row0+sub_px, col0:col0+sub_px]
        sum_I = sub_img.sum()
        if sum_I > 0:
            y, x = np.indices((sub_px, sub_px))
            cx.append(np.sum(x * sub_img) / sum_I)
            cy.append(np.sum(y * sub_img) / sum_I)
        else:
            cx.append((sub_px - 1.0) / 2.0)
            cy.append((sub_px - 1.0) / 2.0)
    return np.array(cx + cy, dtype=np.float32)

print("Computing reference slopes on flat wavefront...")
wf_flat = hp.Wavefront(aperture, wavelength)
shwfs_focal = shwfs_optics(wf_flat)
detector = hp.NoiselessDetector(shwfs_focal.grid)
detector.integrate(shwfs_focal, 1)
ref_img = detector.read_out().shaped
ref_img = (ref_img / ref_img.max() * 255).astype(np.float32)

ref_slopes = compute_slopes_py(ref_img.flatten())

print("Computing Zernike Basis...")
zernike_basis = hp.make_zernike_basis(n_zernike, pupil_diameter, pupil_grid, starting_mode=1)

print("Building Interaction Matrix (1000 modes)...")
M_Zernike = np.zeros((n_slopes, n_zernike), dtype=np.float32)
amp = 1e-7

for i in range(n_zernike):
    phase = zernike_basis[i] * amp * (2 * np.pi / wavelength)
    wf_poked = hp.Wavefront(aperture * np.exp(1j * phase), wavelength)
    
    shwfs_focal = shwfs_optics(wf_poked)
    detector = hp.NoiselessDetector(shwfs_focal.grid)
    detector.integrate(shwfs_focal, 1)
    poked_img = detector.read_out().shaped
    poked_img = (poked_img / poked_img.max() * 255).astype(np.float32)
    
    slopes_buf = compute_slopes_py(poked_img.flatten())
    M_Zernike[:, i] = (slopes_buf - ref_slopes) / amp

print("Inverting Zernike Interaction Matrix to obtain G+...")
g_plus = np.linalg.pinv(M_Zernike, rcond=1e-4).astype(np.float32)

print("Saving matrices...")
np.savetxt(os.path.join(DATA_DIR, 'g_plus.csv'),      g_plus,      delimiter=',', fmt='%.8e')
np.savetxt(os.path.join(DATA_DIR, 'valid_mask.csv'),  valid_mask,  delimiter=',', fmt='%d')
np.savetxt(os.path.join(DATA_DIR, 'ref_slopes.csv'),  ref_slopes,  delimiter=',', fmt='%.8e')

# Generate atmospheric frames
N_FRAMES = 10000

print("Generating Atmospheric layers...")
fried_parameter = 0.15
outer_scale = 25.0
velocity = 10.0
layer = hp.InfiniteAtmosphericLayer(pupil_grid, Cn_squared=hp.Cn_squared_from_fried_parameter(fried_parameter, 500e-9), L0=outer_scale, velocity=np.array([velocity, 0]))

transformation_matrix = zernike_basis.transformation_matrix
AtA = transformation_matrix.T @ transformation_matrix
AtA_inv = np.linalg.inv(AtA)
zernike_inverse = AtA_inv @ transformation_matrix.T
gt = []

print(f"Generating {N_FRAMES} Telemetry Frames...")
for i in range(N_FRAMES):
    layer.t = i * 0.001 
    wf = hp.Wavefront(aperture, wavelength)
    wf = layer(wf)
    
    opd = layer.phase_for(wavelength) * (wavelength / (2 * np.pi))
    opd_valid = opd * aperture
    true_z = zernike_inverse.dot(opd_valid)
    gt.append(true_z)
    
    shwfs_focal = shwfs_optics(wf)
    detector = hp.NoiselessDetector(shwfs_focal.grid)
    detector.integrate(shwfs_focal, 1)
    img = detector.read_out().shaped
    
    frame = (img / img.max() * 255).astype(np.float32)
    np.save(os.path.join(DATA_DIR, f'frame_{i:04d}.npy'), frame)
    
    if (i+1) % 50 == 0:
        print(f"  {i+1}/{N_FRAMES}")

np.savetxt(os.path.join(DATA_DIR, 'ground_truth.csv'), np.array(gt), delimiter=',', fmt='%.8e')

print("Zipping the dataset...")
os.system(f"cd /kaggle/working && zip -r hcipy_dataset.zip hcipy_dataset/")
print("Done.")
