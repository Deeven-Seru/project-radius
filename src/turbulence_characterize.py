"""
turbulence_characterize.py
--------------------------
Estimates r0 (Fried parameter) and tau0 (coherence time) from
a time series of Zernike Tip/Tilt coefficients.
"""
import numpy as np

def estimate_r0(zernike_series, D=8.0, tip_idx=1, tilt_idx=2):
    sigma_tt_sq = np.var(zernike_series[:, tip_idx]) + np.var(zernike_series[:, tilt_idx])
    if sigma_tt_sq <= 0: return np.nan
    return D * (0.448 / sigma_tt_sq) ** (3.0/5.0)

def estimate_tau0(zernike_series, fps=100.0, tip_idx=1, tilt_idx=2):
    tt = zernike_series[:, tip_idx] + zernike_series[:, tilt_idx]
    tt -= tt.mean()
    acf = np.correlate(tt, tt, mode='full')[len(tt)-1:]
    acf /= acf[0]
    crossings = np.where(acf < np.exp(-1))[0]
    return crossings[0]/fps if len(crossings) > 0 else np.nan

def estimate_strehl(residual_rms_rad):
    return float(np.exp(-(2*np.pi*residual_rms_rad)**2))
