"""
compare_oopao.py
----------------
Independent verification: compares C-Engine Zernike output against
OOPAO ground truth to validate the MVM reconstructor numerically.
"""
import numpy as np, ctypes as ct, os

BASE = os.path.join(os.path.dirname(__file__), '..')

def compare(n_frames=50):
    DATA  = os.path.join(BASE, 'data', 'dataset')
    BUILD = os.path.join(BASE, 'build')
    g_plus = np.loadtxt(os.path.join(DATA, 'g_plus.csv'), delimiter=',').astype(np.float32)
    gt     = np.loadtxt(os.path.join(DATA, 'ground_truth.csv'), delimiter=',').astype(np.float32)
    lib    = ct.CDLL(os.path.join(BUILD, 'c_engine.so'))
    lib.reconstruct_zernikes.argtypes = [ct.POINTER(ct.c_float)]*3 + [ct.c_int, ct.c_int]
    lib.reconstruct_zernikes.restype  = None
    n_zernike, n_slopes = g_plus.shape
    mse = []
    for i in range(min(n_frames, len(gt))):
        z = np.zeros(n_zernike, dtype=np.float32)
        lib.reconstruct_zernikes(gt[i].astype(np.float32).ctypes.data_as(ct.POINTER(ct.c_float)),
                                  g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  z.ctypes.data_as(ct.POINTER(ct.c_float)),
                                  ct.c_int(n_zernike), ct.c_int(n_slopes))
        mse.append(np.mean((z - gt[i, :n_zernike])**2))
    print(f"Mean MSE ({len(mse)} frames): {np.mean(mse):.4e}")

if __name__ == '__main__': compare()
