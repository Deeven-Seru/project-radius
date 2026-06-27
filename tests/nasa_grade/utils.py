import numpy as np

def generate_spot_field(n_sub=100, sub_px=10, photon_count=1000, noise_std=5.0, shift_x=0.0, shift_y=0.0):
    """
    Generates a simulated Shack-Hartmann spot field.
    
    Args:
        n_sub: Total number of sub-apertures (must be a perfect square).
        sub_px: Pixels per sub-aperture side.
        photon_count: Average photons per sub-aperture spot.
        noise_std: Standard deviation of background read noise.
        shift_x, shift_y: Global shift of all spots from center.
    """
    N_1d = int(np.sqrt(n_sub))
    img_size = N_1d * sub_px
    img = np.zeros((img_size, img_size), dtype=np.float32)
    
    # Generate Gaussian spots
    for i in range(N_1d):
        for j in range(N_1d):
            center_y = i * sub_px + sub_px / 2.0 + shift_y
            center_x = j * sub_px + sub_px / 2.0 + shift_x
            
            y, x = np.mgrid[0:img_size, 0:img_size]
            
            # Restrict to current sub-aperture to speed up computation
            mask = (y >= i * sub_px) & (y < (i + 1) * sub_px) & \
                   (x >= j * sub_px) & (x < (j + 1) * sub_px)
                   
            # Gaussian spot width (sigma)
            sigma = sub_px / 4.0
            
            spot = np.exp(-((x[mask] - center_x)**2 + (y[mask] - center_y)**2) / (2 * sigma**2))
            # Normalize and scale by photon_count
            if spot.sum() > 0:
                spot = spot / spot.sum() * photon_count
            
            img[mask] += spot.flatten()

    # Add Poisson noise (shot noise)
    # np.random.poisson takes lambda (expectation). If photon_count is 0, this is 0.
    img = np.random.poisson(np.clip(img, 0, None)).astype(np.float32)
    
    # Add Gaussian read noise
    if noise_std > 0:
        read_noise = np.random.normal(0, noise_std, img.shape).astype(np.float32)
        img += read_noise
        
    return img.flatten()

def generate_valid_mask(n_sub, geometry="circular"):
    """
    Generates a valid mask for sub-apertures.
    """
    N_1d = int(np.sqrt(n_sub))
    mask = np.zeros(n_sub, dtype=np.int32)
    
    if geometry == "circular":
        center = N_1d / 2.0
        radius = N_1d / 2.0
        for i in range(N_1d):
            for j in range(N_1d):
                y = i + 0.5 - center
                x = j + 0.5 - center
                if np.sqrt(x**2 + y**2) <= radius:
                    mask[i * N_1d + j] = 1
    else:
        mask[:] = 1 # Square geometry, all valid
        
    return mask
