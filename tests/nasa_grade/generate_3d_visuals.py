import os
import ctypes
import numpy as np
import imageio.v3 as iio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import hcipy
from io import BytesIO

def run_3d_visuals():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "dataset")
    assets_dir = os.path.join(project_root, "assets")
    
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
    
    n_sub = 400
    n_valid = 316
    sub_px = 20
    n_zernike = 55
    frames_to_process = 50
    
    valid_mask = np.loadtxt(os.path.join(data_dir, "valid_mask.csv"), delimiter=",").astype(np.int32).flatten()
    g_plus = np.loadtxt(os.path.join(data_dir, "g_plus.csv"), delimiter=",").astype(np.float32)
    ref_slopes = np.loadtxt(os.path.join(data_dir, "ref_slopes.csv"), delimiter=",").astype(np.float32).flatten()
    
    print("Setting up HCIPy basis for rendering...")
    grid = hcipy.make_pupil_grid(200)
    basis = hcipy.make_zernike_basis(n_zernike, 1, grid, starting_mode=1)
    transformation = basis.transformation_matrix
    
    output_frames = []
    
    print(f"Processing {frames_to_process} frames in 3D...")
    
    # Pre-calculate physical X, Y grid for 3D plot (20x20 downsampled)
    x_lin = np.linspace(-1, 1, 20)
    y_lin = np.linspace(-1, 1, 20)
    X, Y = np.meshgrid(x_lin, y_lin)
    R = np.sqrt(X**2 + Y**2)
    
    for i in range(frames_to_process):
        frame_path = os.path.join(data_dir, f"frame_{i:04d}.bmp")
        if not os.path.exists(frame_path):
            break
        
        img = iio.imread(frame_path)
        
        # C-Engine processing
        img_flat = img.flatten()
        raw_slopes = np.zeros(n_valid * 2, dtype=np.float32)
        zernikes = np.zeros(n_zernike, dtype=np.float32)
        
        lib.compute_slopes_weighted(img_flat, raw_slopes, valid_mask, n_sub, n_valid, sub_px, 400, 1.0, 0.0)
        slopes = raw_slopes - ref_slopes
        lib.reconstruct_zernikes(slopes, g_plus.flatten(), zernikes, n_zernike, n_valid * 2)
        
        # Render 200x200 Phase Map
        phase_1d = transformation.dot(zernikes)
        phase_200 = phase_1d.reshape((200, 200))
        
        # Downsample to 20x20 for the 3D Actuator Trampoline
        Z = phase_200[5::10, 5::10]
        
        # EXAGGERATE THE MOTION: Dynamically scale the wavefront so its peak is ALWAYS 1.5
        max_z = np.nanmax(np.abs(Z))
        print(f"Frame {i} - max_z: {max_z}")
        if max_z > 1e-9:
            Z = Z * (1.5 / max_z)
        
        # Mask out the corners to create a round mirror
        Z[R > 1.0] = np.nan
        
        print(f"Frame {i} - Plotting surface...")
        
        # 3D Matplotlib Plotting
        fig = plt.figure(figsize=(6, 6))
        ax = fig.add_subplot(111, projection='3d')
        
        # Draw the continuous face-sheet mirror
        surf = ax.plot_surface(X, Y, Z, cmap='coolwarm', edgecolor='white', linewidth=0.3, alpha=0.9, vmin=-1.5, vmax=1.5)
        
        # Draw physical pistons underneath using a memory-safe single Line3D object
        x_lines, y_lines, z_lines = [], [], []
        for j in range(20):
            for k in range(20):
                if R[j, k] <= 1.0:
                    x_lines.extend([X[j,k], X[j,k], np.nan])
                    y_lines.extend([Y[j,k], Y[j,k], np.nan])
                    z_lines.extend([-2.0, Z[j,k], np.nan])
                    
        ax.plot(x_lines, y_lines, z_lines, color='silver', alpha=0.7, linewidth=1.5)
        # Formatting to look kid-friendly and highly technical at the same time
        ax.set_zlim(-2.0, 2.0)
        ax.set_axis_off()
        ax.view_init(elev=35, azim=i*2) # Slowly rotate the camera over time
        ax.set_title(f"3D Deformable Mirror in Action! (T={i*10}ms)", color='white', y=0.95, fontsize=14)
        
        fig.patch.set_facecolor('#111111')
        ax.set_facecolor('#111111')
        
        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', facecolor='#111111', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        
        out_img = iio.imread(buf)
        output_frames.append(out_img)
        
        if (i+1) % 5 == 0:
            print(f"Rendered {i+1}/{frames_to_process} 3D frames")

    output_gif_path = os.path.join(assets_dir, "3d_mirror_trampoline.gif")
    print(f"Saving 3D GIF to {output_gif_path}...")
    iio.imwrite(output_gif_path, output_frames, duration=100, loop=0)
    print("Done!")

if __name__ == "__main__":
    run_3d_visuals()
