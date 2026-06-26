import time
import numpy as np
import hcipy as hp

# Benchmark Configuration
n_lenslets = 20
sub_px = 10
pixels_across = n_lenslets * sub_px
pupil_diameter = 8.0
num_zernikes = 1000
n_iters = 10

print(f"Setting up HCIPy {n_lenslets}x{n_lenslets} SH-WFS Configuration...")
print("1. Constructing Grids...")
pupil_grid = hp.make_pupil_grid(pixels_across, pupil_diameter)
aperture = hp.make_circular_aperture(pupil_diameter)(pupil_grid)

# Setting up WFS
print("2. Constructing Optics...")
f_number = 15000
shwfs_optics = hp.SquareShackHartmannWavefrontSensorOptics(
    pupil_grid, f_number=f_number, num_lenslets=n_lenslets, pupil_diameter=pupil_diameter
)

# Reference Image
print("3. Capturing Reference Image...")
wf_ref = hp.Wavefront(aperture, 2.2e-6)
img_ref = shwfs_optics(wf_ref).intensity

shwfs_estimator = hp.ShackHartmannWavefrontSensorEstimator(
    shwfs_optics.mla_grid, img_ref.grid
)

slopes_ref = shwfs_estimator.estimate(img_ref)

print("4. Building Zernike Modes & Interaction Matrix... (This might take a while)")
t_start_calib = time.time()

# Use synthetic interaction matrix to skip massive build time
print("Using synthetic matrices to isolate inference latency...")
# We only care about runtime latency, not initialization latency
synthetic_img = img_ref
synthetic_slopes = slopes_ref
reconstructor = np.random.randn(num_zernikes, len(slopes_ref)).astype(np.float32)

print(f"\nStarting benchmark over {n_iters} iterations...")
times_propagation = []
times_centroiding = []
times_mvm = []
times_total = []

for i in range(n_iters):
    wf_dist = hp.Wavefront(aperture, 2.2e-6)
    
    t0 = time.perf_counter()
    
    # HCIPy pipeline execution
    t_prop_start = time.perf_counter()
    img_dist = shwfs_optics(wf_dist).intensity
    t_prop_end = time.perf_counter()
    
    t_cent_start = time.perf_counter()
    slopes_dist = shwfs_estimator.estimate(img_dist)
    slopes_diff = slopes_dist - slopes_ref
    t_cent_end = time.perf_counter()
    
    t_mvm_start = time.perf_counter()
    rec_coeffs = reconstructor.dot(slopes_diff)
    t_mvm_end = time.perf_counter()
    
    t1 = time.perf_counter()
    
    times_propagation.append(t_prop_end - t_prop_start)
    times_centroiding.append(t_cent_end - t_cent_start)
    times_mvm.append(t_mvm_end - t_mvm_start)
    times_total.append(t1 - t0)

# Results
print("\n--- HCIPy Benchmark Results ---")
print(f"Total Framework Pipeline Latency : {np.mean(times_total)*1000:.2f} ms")
print(f"  -> Optics Propagation & Det    : {np.mean(times_propagation)*1000:.2f} ms")
print(f"  -> Centroiding (Estimator)     : {np.mean(times_centroiding)*1000:.2f} ms")
print(f"  -> Zernike Reconstruction (MVM): {np.mean(times_mvm)*1000:.2f} ms")
print(f"Max Frequency: {1.0 / np.mean(times_total):.2f} Hz")
