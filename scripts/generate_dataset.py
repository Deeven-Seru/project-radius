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

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')
os.makedirs(DATA_DIR, exist_ok=True)
N_FRAMES = 500

tel  = Telescope(8.0, 20); src = Source('K', magnitude=8); src * tel
atm  = Atmosphere(tel, r0=0.15, L0=25, fractionalR0=[1.0, 0.5], windSpeed=[10, 5], windDirection=[0, 45])
atm  + tel
dm   = DeformableMirror(tel, nSubap=21, mechCoupling=0.35)
wfs  = ShackHartmann(nSubap=20, telescope=tel, lightRatio=0.5)
gt   = []

for i in range(N_FRAMES):
    atm.update(); tel * src; wfs.measure(tel)
    frame = (wfs.cam.frame / wfs.cam.frame.max() * 255).astype(np.uint8)
    Image.fromarray(frame).save(os.path.join(DATA_DIR, f'frame_{i:04d}.bmp'))
    gt.append(wfs.SlopesMeasurement[:400])
    if (i+1) % 50 == 0: print(f"  {i+1}/{N_FRAMES}")

np.savetxt(os.path.join(DATA_DIR, 'ground_truth.csv'), np.array(gt), delimiter=',', fmt='%.8e')
print("Done.")
