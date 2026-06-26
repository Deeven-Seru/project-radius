import numpy as np
import os

DATA_DIR = "data/hcipy_dataset"
os.makedirs(DATA_DIR, exist_ok=True)

n_sub = 6400
n_valid = 6400
n_slopes = 12800
n_modes = 1000
n_act = 200

valid_mask = np.ones(n_sub, dtype=np.int32)
np.savetxt(os.path.join(DATA_DIR, "valid_mask.csv"), valid_mask, fmt='%d', delimiter=",")

ref_slopes = np.zeros(n_slopes, dtype=np.float32)
np.savetxt(os.path.join(DATA_DIR, "ref_slopes.csv"), ref_slopes, delimiter=",")

g_plus = np.random.randn(n_modes, n_slopes).astype(np.float32)
np.savetxt(os.path.join(DATA_DIR, "g_plus.csv"), g_plus, delimiter=",")

dm_coupling = np.random.randn(n_act, n_modes).astype(np.float32)
np.savetxt(os.path.join(DATA_DIR, "dm_coupling.csv"), dm_coupling, delimiter=",")

n_frames = 100
res = 800
for i in range(n_frames):
    frame = np.random.randint(0, 255, size=(res, res)).astype(np.float32)
    np.save(os.path.join(DATA_DIR, f"frame_{i:04d}.npy"), frame)

gt = np.random.randn(n_frames, n_modes).astype(np.float32)
np.savetxt(os.path.join(DATA_DIR, "ground_truth.csv"), gt, delimiter=",")
print("All random files generated.")
