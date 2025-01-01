import ctypes
import time
import numpy as np
import os
import aotpy
import urllib.request

# 1. Download
print("Downloading ERIS_NGS.fits from Zenodo...")
url = 'https://zenodo.org/records/8192742/files/ERIS_NGS_20230331_012546.fits?download=1'
if not os.path.exists("ERIS_NGS.fits"):
    urllib.request.urlretrieve(url, "ERIS_NGS.fits")

# 2. Compile dynamic C code
print("Compiling dynamic C Engine...")
os.system("gcc -shared -o c_engine.so -fPIC slopes.c mvm_reconstructor.c -O3 -march=native")

# 3. Load
c_engine = ctypes.CDLL(os.path.abspath('./c_engine.so'))

print("Loading ERIS NGS Telemetry...")
system = aotpy.AOSystem.read_from_file("ERIS_NGS.fits")

wfs = system.wavefront_sensors[0]
slopes_data = wfs.measurements.data

num_frames = slopes_data.shape[0]
num_slopes = slopes_data.shape[1]
num_zernikes = 50

print(f"Loaded {num_frames} frames with {num_slopes} slopes each.")

G_plus = np.random.randn(num_zernikes, num_slopes).astype(np.float64)

c_reconstruct = c_engine.reconstruct_zernikes
c_reconstruct.argtypes = [
    np.ctypeslib.ndpointer(dtype=np.float64, ndim=2, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags='C_CONTIGUOUS'),
    np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags='C_CONTIGUOUS'),
    ctypes.c_int,
    ctypes.c_int
]

zernikes_out = np.zeros(num_zernikes, dtype=np.float64)

print("Executing C Engine MVM Reconstructor on REAL TELEMETRY...")
start_time = time.perf_counter()

for i in range(num_frames):
    frame_slopes = slopes_data[i].astype(np.float64).flatten()
    c_reconstruct(G_plus, frame_slopes, zernikes_out, num_zernikes, num_slopes)

end_time = time.perf_counter()
total_time = end_time - start_time
time_per_frame = (total_time / num_frames) * 1000

print(f"Total time for {num_frames} real frames: {total_time:.4f} seconds")
print(f"Average Latency per frame: {time_per_frame:.4f} milliseconds")

if time_per_frame < 10.0:
    print("\\nSUCCESS: The C Engine comfortably beats the 10ms real-time deadline for real ERIS telemetry!")
else:
    print("\\nFAIL: Latency exceeds limits.")
