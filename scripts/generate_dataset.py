"""
generate_dataset.py
-------------------
Simulates 500 frames of SH-WFS telemetry using OOPAO under Von Karman turbulence.
Output: 500 .bmp frames + ground_truth.csv (500 x 20 Zernike coefficients).
"""
import numpy as np, os
from PIL import Image
from OOPAO.Telescope import Telescope
from OOPAO.Source import Source
from OOPAO.ShackHartmann import ShackHartmann
from OOPAO.DeformableMirror import DeformableMirror
from OOPAO.Atmosphere import Atmosphere
from OOPAO.Zernike import Zernike

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')
os.makedirs(DATA_DIR, exist_ok=True)
N_FRAMES = 500

print("Initializing OOPAO objects (Resolution = 400)...")
tel  = Telescope(resolution=400, diameter=8.0)
src  = Source('K', magnitude=8); src * tel
atm  = Atmosphere(telescope=tel, r0=0.15, L0=25, fractionalR0=[1.0, 0.5], windSpeed=[10, 5], windDirection=[0, 45], altitude=[0, 1000], src=src)

atm.initializeAtmosphere(tel)
tel + atm


dm   = DeformableMirror(tel, nSubap=20, mechCoupling=0.35)
wfs  = ShackHartmann(nSubap=20, telescope=tel, lightRatio=0.5)

# Reset main source to clear Tip/Tilt calibration mask left by wfs.set_slopes_units()
src.reset()
src * tel

n_zernike = 55
Z = Zernike(tel, J=n_zernike)
Z.computeZernike(tel, remove_piston=0)
z_norm = np.sum(Z.modes**2, axis=0)

gt = []

print("Generating 500 Telemetry Frames...")
for i in range(N_FRAMES):
    atm.update()
    src * tel * wfs
    
    # Save camera frame as BMP
    frame = (wfs.cam.frame / wfs.cam.frame.max() * 255).astype(np.uint8)
    Image.fromarray(frame).save(os.path.join(DATA_DIR, f'frame_{i:04d}.bmp'))
    
    # Compute true Zernike coefficients of the atmosphere phase in meters (keep piston)
    true_phase = src.OPD[tel.pupil > 0]
    true_z = np.sum(true_phase[:, None] * Z.modes, axis=0) / z_norm
    gt.append(true_z)
    
    if (i+1) % 50 == 0:
        print(f"  {i+1}/{N_FRAMES}")

np.savetxt(os.path.join(DATA_DIR, 'ground_truth.csv'), np.array(gt), delimiter=',', fmt='%.8e')
print("Done.")
