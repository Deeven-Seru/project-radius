import time
import numpy as np
import hcipy as hp

# Benchmark Configuration
n_lenslets = 80
sub_px = 10
pixels_across = n_lenslets * sub_px
pupil_diameter = 8.0

print(f"Setting up HCIPy {n_lenslets}x{n_lenslets} SH-WFS Configuration...")
pupil_grid = hp.make_pupil_grid(pixels_across, pupil_diameter)
aperture = hp.make_circular_aperture(pupil_diameter)(pupil_grid)

f_number = 15000
shwfs_optics = hp.SquareShackHartmannWavefrontSensorOptics(
    pupil_grid, f_number=f_number, num_lenslets=n_lenslets, pupil_diameter=pupil_diameter
)

wf_ref = hp.Wavefront(aperture, 2.2e-6)
# Get the image as a Field
img_ref = shwfs_optics(wf_ref).intensity

shwfs_estimator = hp.ShackHartmannWavefrontSensorEstimator(
    shwfs_optics.mla_grid, img_ref.grid
)

print("Starting 10 iterations of HCIPy Estimator Centroiding...")
t0 = time.time()
for i in range(10):
    slopes = shwfs_estimator.estimate(img_ref)
t1 = time.time()

print(f"HCIPy Estimator Latency (80x80): {(t1-t0)/10 * 1000:.2f} ms")
