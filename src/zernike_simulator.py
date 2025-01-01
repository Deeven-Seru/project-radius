"""
zernike_simulator.py
--------------------
Standalone Zernike polynomial evaluator for verification and visualization.
"""
import numpy as np

def zernike_radial(n, m, rho):
    R = np.zeros_like(rho, dtype=float)
    for s in range((n - abs(m)) // 2 + 1):
        c = ((-1)**s * np.math.factorial(n-s)
             / (np.math.factorial(s)
                * np.math.factorial((n+abs(m))//2-s)
                * np.math.factorial((n-abs(m))//2-s)))
        R += c * rho**(n - 2*s)
    return R

def zernike(j, rho, theta):
    n = int(np.ceil((-3 + np.sqrt(9 + 8*j)) / 2))
    m = 2*j - n*(n+2)
    R = zernike_radial(n, abs(m), rho)
    if m > 0:   return R * np.cos(abs(m)*theta)
    elif m < 0: return R * np.sin(abs(m)*theta)
    else:       return R
