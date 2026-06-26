"""
generate_hcipy_dataset.py
-------------------------
Simulates 500 frames of SH-WFS telemetry using HCIPy under Von Karman turbulence.
Output: 500 .bmp frames + ground_truth.csv (500 x 55 Zernike coefficients).
"""
import numpy as np, os
import hcipy as hp
from PIL import Image

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'hcipy_dataset')
os.makedirs(DATA_DIR, exist_ok=True)
N_FRAMES = 500

print("Initializing HCIPy objects (Resolution = 800)...")
wavelength = 2.2e-6
pupil_diameter = 8.0
pupil_grid = hp.make_pupil_grid(800, pupil_diameter)
aperture = hp.make_circular_aperture(pupil_diameter)(pupil_grid)

# Shack-Hartmann WFS
# 80x80 lenslets
num_lenslets = 80
shwfs_optics = hp.SquareShackHartmannWavefrontSensorOptics(pupil_grid, f_number=7500, num_lenslets=num_lenslets, pupil_diameter=pupil_diameter)

# Atmosphere
print("Generating Atmospheric layers...")
fried_parameter = 0.15
outer_scale = 25.0
velocity = 10.0
layer = hp.InfiniteAtmosphericLayer(pupil_grid, Cn_squared=hp.Cn_squared_from_fried_parameter(fried_parameter, 500e-9), L0=outer_scale, velocity=np.array([velocity, 0]))

# Zernike Basis (1000 modes)
N_ZERNIKES = 1000
print("Computing Zernike basis...")
# HCIPy starting_mode=1 is Piston, 2 is Tip, 3 is Tilt...
# OOPAO uses a specific ordering. We will project onto HCIPy's standard Noll ordering.
zernike_basis = hp.make_zernike_basis(N_ZERNIKES, pupil_diameter, pupil_grid, starting_mode=1)
# Create a transformation matrix to project phase onto Zernikes
transformation_matrix = zernike_basis.transformation_matrix
print("Precomputing projection matrix using normal equations...")
# A.T @ A is small (1000x1000), so inversion is fast
AtA = transformation_matrix.T @ transformation_matrix
AtA_inv = np.linalg.inv(AtA)
zernike_inverse = AtA_inv @ transformation_matrix.T
gt = []

print("Generating 500 Telemetry Frames...")
for i in range(N_FRAMES):
    # Evolve atmosphere
    layer.t = i * 0.001 # 1 ms per frame (1000 Hz)
    
    # Generate Wavefront
    wf = hp.Wavefront(aperture, wavelength)
    wf = layer(wf)
    
    # Extract phase and compute Zernikes
    # Use layer.phase_for to get UNWRAPPED phase! wf.phase returns wrapped phase in [-pi, pi]
    opd = layer.phase_for(wavelength) * (wavelength / (2 * np.pi))
    # Project OPD onto Zernikes
    # Only evaluate inside the aperture
    opd_valid = opd * aperture
    true_z = zernike_inverse.dot(opd_valid)
    gt.append(true_z)
    
    # Propagate through SH-WFS
    shwfs_focal = shwfs_optics(wf)
    detector = hp.NoiselessDetector(shwfs_focal.grid)
    detector.integrate(shwfs_focal, 1)
    img = detector.read_out().shaped
    
    # Save camera frame as NPY (float32, 0-255 scaled)
    frame = (img / img.max() * 255).astype(np.float32)
    np.save(os.path.join(DATA_DIR, f'frame_{i:04d}.npy'), frame)
    
    if (i+1) % 50 == 0:
        print(f"  {i+1}/{N_FRAMES}")

np.savetxt(os.path.join(DATA_DIR, 'ground_truth.csv'), np.array(gt), delimiter=',', fmt='%.8e')
print("Done.")
