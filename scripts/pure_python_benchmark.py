import time
import numpy as np
import scipy.ndimage as ndimage

n_lenslets = 80
sub_px = 10
img_size = n_lenslets * sub_px
n_sub = n_lenslets**2
n_valid = 5024
n_slopes = n_valid * 2
n_zernike = 1000
n_actuators = 200

# Synthetic Data
frame = np.random.rand(img_size, img_size).astype(np.float32)
slopes_ref = np.random.rand(n_slopes).astype(np.float32)
reconstructor = np.random.rand(n_zernike, n_slopes).astype(np.float32)
dm_map = np.random.rand(n_actuators, n_zernike).astype(np.float32)

# Subaperture bounding boxes (simulate what HCIPy estimator iterates over)
bboxes = []
for i in range(n_lenslets):
    for j in range(n_lenslets):
        bboxes.append((i*sub_px, (i+1)*sub_px, j*sub_px, (j+1)*sub_px))
# Only valid ones
bboxes = bboxes[:n_valid]

print("Benchmarking Pure Python (Numpy/Scipy) implementation...")
n_iters = 100

t0 = time.perf_counter()
times_cent = []
times_mvm = []

for _ in range(n_iters):
    # Centroiding (Center of Mass per subaperture)
    t_cent_start = time.perf_counter()
    slopes = np.zeros(n_slopes)
    for idx, (r1, r2, c1, c2) in enumerate(bboxes):
        sub_img = frame[r1:r2, c1:c2]
        # scipy center of mass or numpy equivalent
        # Using numpy manually since it's slightly faster than scipy for small arrays
        total_intensity = np.sum(sub_img)
        if total_intensity > 0:
            y_indices, x_indices = np.indices(sub_img.shape)
            cy = np.sum(y_indices * sub_img) / total_intensity
            cx = np.sum(x_indices * sub_img) / total_intensity
            slopes[2*idx] = cx
            slopes[2*idx+1] = cy
    t_cent_end = time.perf_counter()
    
    slopes_diff = slopes - slopes_ref
    
    # Vector-Matrix Multiplication (Numpy)
    t_mvm_start = time.perf_counter()
    zernike_coeffs = np.dot(reconstructor, slopes_diff)
    actuator_cmds = np.dot(dm_map, zernike_coeffs)
    t_mvm_end = time.perf_counter()
    
    times_cent.append(t_cent_end - t_cent_start)
    times_mvm.append(t_mvm_end - t_mvm_start)

t1 = time.perf_counter()
total_time = t1 - t0

print(f"\nTotal Time for {n_iters} iterations: {total_time:.4f} s")
print(f"Mean Centroiding Latency: {np.mean(times_cent)*1000:.4f} ms")
print(f"Mean MVM Latency: {np.mean(times_mvm)*1000:.4f} ms")
print(f"Total Mean Latency: {(total_time/n_iters)*1000:.4f} ms")
print(f"Max Frequency: {1.0/(total_time/n_iters):.2f} Hz")
