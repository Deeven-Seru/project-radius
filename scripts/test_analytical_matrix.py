import numpy as np
import hcipy as hp

pupil_diameter = 8.0
num_lenslets = 80
n_zernike = 10

# Dense grid for analytical derivatives
dense_res = 3200 # 40 pixels per lenslet
dense_grid = hp.make_pupil_grid(dense_res, pupil_diameter)
z_basis = hp.make_zernike_basis(n_zernike, pupil_diameter, dense_grid, starting_mode=1)

dx = pupil_diameter / dense_res
dy = pupil_diameter / dense_res

# Subaperture centers
lenslet_grid = hp.make_pupil_grid(num_lenslets, pupil_diameter)
valid_mask = hp.make_circular_aperture(pupil_diameter)(lenslet_grid).astype(bool)
n_valid = np.sum(valid_mask)

analytical_M = np.zeros((n_valid * 2, n_zernike))

# Calculate lenslet bounds on the dense grid
# The dense grid goes from -4.0 to +4.0
# The lenslet grid is 80x80
pixels_per_lenslet = dense_res // num_lenslets

valid_idx = np.where(valid_mask)[0]

for i in range(n_zernike):
    mode_2d = z_basis[i].shaped
    # Gradient in physical units
    grad_y, grad_x = np.gradient(mode_2d, dy, dx)
    
    # Average over each valid lenslet
    for k, v_idx in enumerate(valid_idx):
        ly = v_idx // num_lenslets
        lx = v_idx % num_lenslets
        
        # Pixel bounds in the dense grid
        y0 = ly * pixels_per_lenslet
        y1 = y0 + pixels_per_lenslet
        x0 = lx * pixels_per_lenslet
        x1 = x0 + pixels_per_lenslet
        
        mean_grad_x = np.mean(grad_x[y0:y1, x0:x1])
        mean_grad_y = np.mean(grad_y[y0:y1, x0:x1])
        
        analytical_M[k, i] = mean_grad_x
        analytical_M[n_valid + k, i] = mean_grad_y

print(f"Analytical matrix shape: {analytical_M.shape}")
print(f"Tip x-slope max: {np.max(analytical_M[:, 0])}")
