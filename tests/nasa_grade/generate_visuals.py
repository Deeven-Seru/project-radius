import os
import ctypes
import numpy as np
import imageio.v3 as iio
import matplotlib.pyplot as plt
import hcipy
from io import BytesIO

def run_visuals():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "dataset")
    assets_dir = os.path.join(project_root, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    # 1. Load C-Engine
    lib_path = os.path.join(project_root, "build", "c_engine.so")
    if not os.path.exists(lib_path):
        lib_path = os.path.join(project_root, "c_engine.so")
    lib = ctypes.CDLL(lib_path)
    
    lib.compute_slopes_weighted.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.uint8, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_float
    ]
    
    lib.reconstruct_zernikes.argtypes = [
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
        ctypes.c_int, ctypes.c_int
    ]
    
    # 2. Setup Variables
    n_sub = 400
    n_valid = 316
    sub_px = 20
    n_zernike = 55
    frames_to_process = 50
    
    # Load valid mask and g_plus
    valid_mask = np.loadtxt(os.path.join(data_dir, "valid_mask.csv"), delimiter=",").astype(np.int32).flatten()
    g_plus = np.loadtxt(os.path.join(data_dir, "g_plus.csv"), delimiter=",").astype(np.float32)
    ref_slopes = np.loadtxt(os.path.join(data_dir, "ref_slopes.csv"), delimiter=",").astype(np.float32).flatten()
    
    # 3. HCIPy Setup for 2D Rendering
    print("Setting up HCIPy basis for rendering...")
    grid = hcipy.make_pupil_grid(200)
    basis = hcipy.make_zernike_basis(n_zernike, 1, grid, starting_mode=1)
    transformation = basis.transformation_matrix
    
    input_frames = []
    output_frames = []
    
    print(f"Processing {frames_to_process} frames...")
    
    for i in range(frames_to_process):
        # Read BMP
        frame_path = os.path.join(data_dir, f"frame_{i:04d}.bmp")
        if not os.path.exists(frame_path):
            break
        
        img = iio.imread(frame_path)
        input_frames.append(img)
        
        # C-Engine processing
        img_flat = img.flatten()
        raw_slopes = np.zeros(n_valid * 2, dtype=np.float32)
        zernikes = np.zeros(n_zernike, dtype=np.float32)
        
        # Centroiding (CoG)
        lib.compute_slopes_weighted(img_flat, raw_slopes, valid_mask, n_sub, n_valid, sub_px, 400, 1.0, 0.0)
        
        # Subtract reference slopes to get Delta Slopes
        slopes = raw_slopes - ref_slopes
        
        # Reconstruct (MVM)
        lib.reconstruct_zernikes(slopes, g_plus.flatten(), zernikes, n_zernike, n_valid * 2)
        
        # 4. Render 2D Wavefront
        # HCIPy uses 1D arrays for fields, we can reshape it to 2D
        phase_1d = transformation.dot(zernikes)
        phase_2d = phase_1d.reshape((200, 200))
        
        # Set pixels outside the circular pupil to NaN so they render as black
        r = np.sqrt((np.arange(200)-100)**2 + (np.arange(200)[:,None]-100)**2)
        phase_2d[r > 100] = np.nan
        
        # Plot using matplotlib
        fig, ax = plt.subplots(figsize=(5, 5))
        # Use RdBu colormap to show positive/negative phase properly. Automatically scale.
        ax.imshow(phase_2d, cmap='RdBu', origin='lower')
        ax.axis('off')
        ax.set_title(f"Reconstructed Wavefront (T={i*10}ms)", color='white')
        fig.patch.set_facecolor('black')
        
        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', facecolor='black', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        buf.seek(0)
        
        out_img = iio.imread(buf)
        output_frames.append(out_img)
        
        if (i+1) % 10 == 0:
            print(f"Processed {i+1}/{frames_to_process} frames")

    # 5. Save GIFs
    input_gif_path = os.path.join(assets_dir, "input_shwfs.gif")
    output_gif_path = os.path.join(assets_dir, "output_wavefront.gif")
    
    print("Saving Input GIF...")
    iio.imwrite(input_gif_path, input_frames, duration=100, loop=0)
    
    print("Saving Output GIF...")
    iio.imwrite(output_gif_path, output_frames, duration=100, loop=0)
    
    print("Done!")

if __name__ == "__main__":
    run_visuals()
