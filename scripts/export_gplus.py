"""
export_gplus.py
---------------
Generates calibration matrices required by the C-Engine:
  g_plus.csv      : pseudo-inverse interaction matrix (n_zernike x n_slopes)
  dm_coupling.csv : DM influence matrix on Zernike basis (n_actuators x n_zernike)
  valid_mask.csv  : binary subaperture validity mask
"""
import numpy as np, os

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'dataset')
os.makedirs(DATA_DIR, exist_ok=True)

from oopao.calibration.CalibrationVault import CalibrationVault
from oopao.Telescope import Telescope
from oopao.Source import Source
from oopao.ShackHartmann import ShackHartmann
from oopao.DeformableMirror import DeformableMirror
from oopao.Atmosphere import Atmosphere

tel  = Telescope(8.0, 20)
src  = Source('K', magnitude=8); src * tel
atm  = Atmosphere(tel, r0=0.15, L0=25, fractionalR0=[1.0], windSpeed=[10], windDirection=[0])
atm  + tel
dm   = DeformableMirror(tel, nSubap=21, mechCoupling=0.35)
wfs  = ShackHartmann(nSubap=20, telescope=tel, lightRatio=0.5)
calib = CalibrationVault(wfs, dm, ampli=0.01)

np.savetxt(os.path.join(DATA_DIR, 'g_plus.csv'),      calib.M,   delimiter=',', fmt='%.8e')
np.savetxt(os.path.join(DATA_DIR, 'dm_coupling.csv'), calib.D.T, delimiter=',', fmt='%.8e')
np.savetxt(os.path.join(DATA_DIR, 'valid_mask.csv'),  wfs.validSubaperture.flatten().astype(int), delimiter=',', fmt='%d')
print(f"G+: {calib.M.shape}  DM: {calib.D.T.shape}  Valid: {wfs.validSubaperture.sum()}")
