import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import hcipy as hp
import ctypes as ct
import os

def main():
    # Load C-Engine
    lib = ct.CDLL('./build/c_engine.so')
    
    # 1. Hardware Setup
    D = 8.0
    wavelength = 2.2e-6
    num_lenslets = 20
    n_zernike = 20
    
    pupil_grid = hp.make_pupil_grid(400, D)
    aperture = hp.make_circular_aperture(D)(pupil_grid)
    zernike_basis = hp.make_zernike_basis(n_zernike, D, pupil_grid, starting_mode=1)
    
    shwfs = hp.SquareShackHartmannWavefrontSensorOptics(
        pupil_grid, f_number=40, num_lenslets=num_lenslets, pupil_diameter=D
    )
    
    wf = hp.Wavefront(aperture, wavelength)
    img_wf = shwfs(wf)
    camera = hp.NoiselessDetector(img_wf.grid)
    camera.integrate(img_wf, 1.0)
    ref_image = camera.read_out()
    
    sub_px = int(np.sqrt(img_wf.grid.size) / num_lenslets)
    ref_2d = ref_image.shaped
    valid_mask = np.zeros((num_lenslets, num_lenslets), dtype=np.int32)
    for i in range(num_lenslets):
        for j in range(num_lenslets):
            patch = ref_2d[i*sub_px:(i+1)*sub_px, j*sub_px:(j+1)*sub_px]
            if np.sum(patch) > 0.1 * np.max(ref_2d):
                valid_mask[i, j] = 1
                
    valid_mask = valid_mask.flatten()
    n_valid = int(np.sum(valid_mask))
    n_slopes = n_valid * 2
    
    # Calibrate M
    amp = 1e-6
    ref_slopes = np.zeros(n_slopes, dtype=np.float32)
    lib.compute_slopes(
        ref_image.astype(np.float32).ctypes.data_as(ct.POINTER(ct.c_float)),
        ref_slopes.ctypes.data_as(ct.POINTER(ct.c_float)),
        valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
        ct.c_int(num_lenslets**2), ct.c_int(n_valid), ct.c_int(sub_px)
    )
    
    M = np.zeros((n_slopes, n_zernike), dtype=np.float32)
    slopes_buf = np.zeros(n_slopes, dtype=np.float32)
    for i in range(n_zernike):
        phase = zernike_basis[i] * amp
        wf = hp.Wavefront(aperture * np.exp(1j * phase * 2 * np.pi / wavelength), wavelength)
        camera.integrate(shwfs(wf), 1.0)
        img = camera.read_out().astype(np.float32)
        lib.compute_slopes(
            img.ctypes.data_as(ct.POINTER(ct.c_float)),
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            ct.c_int(num_lenslets**2), ct.c_int(n_valid), ct.c_int(sub_px)
        )
        M[:, i] = (slopes_buf - ref_slopes) / amp
    g_plus = np.linalg.pinv(M, rcond=1e-2).astype(np.float32)
    
    # Turbulence Setup
    fried_parameter = 0.15
    L0 = 25.0
    velocity = 15.0
    Cn2 = hp.Cn_squared_from_fried_parameter(fried_parameter, 500e-9)
    layer = hp.InfiniteAtmosphericLayer(pupil_grid, Cn2, L0, velocity)
    
    # Plotting setup
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), facecolor='black')
    
    im0 = axes[0].imshow(np.zeros((400, 400)), cmap='inferno', origin='lower')
    axes[0].set_title("Shack-Hartmann WFS Camera", color='white')
    axes[0].axis('off')
    
    # Create a colormap that renders NaN (outside the pupil) as pitch black
    cmap_phase = plt.get_cmap('RdBu_r').copy()
    cmap_phase.set_bad(color='black')
    
    init_phase = hp.Field(np.zeros(pupil_grid.size), pupil_grid)
    init_phase[aperture == 0] = np.nan
    
    im1 = hp.imshow_field(init_phase, cmap=cmap_phase, ax=axes[1], vmin=-3, vmax=3)
    axes[1].set_title("True Atmospheric Phase", color='white')
    axes[1].axis('off')
    
    im2 = hp.imshow_field(init_phase, cmap=cmap_phase, ax=axes[2], vmin=-3, vmax=3)
    axes[2].set_title("C-Engine Reconstructed Phase", color='white')
    axes[2].axis('off')
    
    pred_zernikes = np.zeros(n_zernike, dtype=np.float32)
    
    print("Pre-computing atmospheric phase screens for seamless loop...")
    N = 60
    fade_frames = 15
    total_sim = fade_frames + N
    
    raw_phase = []
    for f in range(total_sim):
        layer.t = f * 0.01
        raw_phase.append(layer.phase_for(wavelength))

    phase_layers = []
    for i in range(N):
        if i < N - fade_frames:
            phase_layers.append(raw_phase[fade_frames + i])
        else:
            fade_idx = i - (N - fade_frames)
            alpha = (fade_idx + 1) / (fade_frames + 1)
            frame_out = raw_phase[fade_frames + i]
            frame_in = raw_phase[fade_idx]
            blended = (1 - alpha) * frame_out + alpha * frame_in
            phase_layers.append(blended)
    
    def update(frame):
        phase_layer = phase_layers[frame]
        wf = hp.Wavefront(aperture * np.exp(1j * phase_layer), wavelength)
        
        # WFS Image
        camera.integrate(shwfs(wf), 1.0)
        img = camera.read_out().astype(np.float32)
        
        # C-Engine inference
        lib.compute_slopes(
            img.ctypes.data_as(ct.POINTER(ct.c_float)),
            slopes_buf.ctypes.data_as(ct.POINTER(ct.c_float)),
            valid_mask.ctypes.data_as(ct.POINTER(ct.c_int)),
            ct.c_int(num_lenslets**2), ct.c_int(n_valid), ct.c_int(sub_px)
        )
        s_diff = slopes_buf - ref_slopes
        lib.reconstruct_zernikes(
            s_diff.ctypes.data_as(ct.POINTER(ct.c_float)),
            g_plus.ctypes.data_as(ct.POINTER(ct.c_float)),
            pred_zernikes.ctypes.data_as(ct.POINTER(ct.c_float)),
            ct.c_int(n_zernike), ct.c_int(n_slopes)
        )
        
        pred_phase_field = zernike_basis.transformation_matrix.dot(pred_zernikes)
        # Convert predicted phase from meters to radians for plotting!
        pred_phase_rad = pred_phase_field * (2 * np.pi / wavelength)
        
        plot_img = img.shaped ** 4
        im0.set_data(plot_img)
        # Set contrast so the spots glow brightly but keep the background black
        im0.set_clim(0, plot_img.max() * 0.8)
        
        # We need to manually update hp.imshow_field which isn't standard imshow.
        axes[1].clear()
        axes[2].clear()
        
        phase_plot = phase_layer.copy()
        phase_plot[aperture == 0] = np.nan
        hp.imshow_field(phase_plot, cmap=cmap_phase, ax=axes[1], vmin=-5, vmax=5)
        axes[1].set_title("True Atmospheric Phase", color='white')
        axes[1].axis('off')
        
        pred_plot = hp.Field(pred_phase_rad, pupil_grid)
        pred_plot[aperture == 0] = np.nan
        hp.imshow_field(pred_plot, cmap=cmap_phase, ax=axes[2], vmin=-5, vmax=5)
        axes[2].set_title("C-Engine Reconstructed Phase", color='white')
        axes[2].axis('off')
        
        return [axes[0], axes[1], axes[2]]

    print("Generating animation...")
    ani = animation.FuncAnimation(fig, update, frames=N, blit=False)
    ani.save('assets/ao_reconstruction.gif', writer='pillow', fps=10, savefig_kwargs={'facecolor': 'black'})
    print("Saved assets/ao_reconstruction.gif")

if __name__ == "__main__":
    os.makedirs('assets', exist_ok=True)
    main()
