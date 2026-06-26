import os

with open("src/c_engine/slopes.c", "r") as f:
    slopes_c = f.read()

with open("src/c_engine/mvm_reconstructor.c", "r") as f:
    mvm_c = f.read()

with open("src/c_engine/geometry.h", "r") as f:
    geom_h = f.read()

python_code = f"""import os
import time
import ctypes
import numpy as np

geom_code = '''{geom_h}'''
slopes_code = '''{slopes_c}'''
mvm_code = '''{mvm_c}'''

with open('geometry.h', 'w') as f:
    f.write(geom_code)

with open('slopes.c', 'w') as f:
    f.write(slopes_code)

with open('mvm_reconstructor.c', 'w') as f:
    f.write(mvm_code)

print("Compiling C-Engine with AVX2 optimizations...")
ret = os.system("gcc -O3 -mavx2 -mfma -shared -fPIC -o c_engine.so slopes.c mvm_reconstructor.c -lm")
if ret != 0:
    print("Failed to compile C-engine!")
    exit(1)

print("Loading C-Engine...")
lib = ctypes.CDLL(os.path.abspath('c_engine.so'))

# Define signatures
lib.compute_slopes.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int
]

lib.reconstruct_zernikes.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_int,
    ctypes.c_int
]

lib.compute_actuator_map.argtypes = [
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.POINTER(ctypes.c_float),
    ctypes.c_int,
    ctypes.c_int
]

# Set up parameters for 80x80 grid
n_sub = 6400
sub_px = 10
img_size = n_sub * sub_px * sub_px
n_valid = 5024
n_slopes = n_valid * 2
n_zernike = 1000
n_actuators = 200

# Allocate memory (synthetic data)
frame = np.random.rand(img_size).astype(np.float32) * 255.0
slopes = np.zeros(n_slopes, dtype=np.float32)
ref_slopes = np.random.rand(n_slopes).astype(np.float32)

# Make a realistic valid_mask with 5024 ones and the rest 0s
valid_mask = np.zeros(n_sub, dtype=np.int32)
valid_mask[:n_valid] = 1

g_plus = np.random.rand(n_zernike, n_slopes).astype(np.float32)
zernikes_out = np.zeros(n_zernike, dtype=np.float32)

c_dm = np.random.rand(n_actuators, n_zernike).astype(np.float32)
actuators_out = np.zeros(n_actuators, dtype=np.float32)

print(f"Benchmarking extreme parameters: {{n_sub}} lenslets, {{n_zernike}} Zernikes, {{n_actuators}} Actuators")
N_ITERS = 1000

# Warmup
lib.compute_slopes(
    frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
    slopes.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
    valid_mask.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
    n_sub, n_valid, sub_px
)

print("Starting latency test (1000 iterations)...")
t0 = time.perf_counter()

for i in range(N_ITERS):
    # Step 1: Centroiding
    lib.compute_slopes(
        frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        slopes.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        valid_mask.ctypes.data_as(ctypes.POINTER(ctypes.c_int)),
        n_sub, n_valid, sub_px
    )
    
    slopes_diff = slopes - ref_slopes
    
    # Step 2: Zernike Reconstruction
    lib.reconstruct_zernikes(
        slopes_diff.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        g_plus.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        zernikes_out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        n_zernike, n_slopes
    )
    
    # Step 3: Actuator mapping
    lib.compute_actuator_map(
        zernikes_out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        c_dm.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        actuators_out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
        n_actuators, n_zernike
    )

t1 = time.perf_counter()
total_time = t1 - t0
per_frame = total_time / N_ITERS

print(f"\\nTotal Time for 1000 iterations: {{total_time:.4f}} s")
print(f"Mean Latency per Frame: {{per_frame*1000:.4f}} ms")
print(f"Max Frequency: {{1.0/per_frame:.2f}} Hz")

if per_frame*1000 < 10.0:
    print("\\nSUCCESS: AVX2 Optimization beat the 10ms ISRO deadline!")
else:
    print("\\nWARNING: Latency exceeded 10ms deadline.")

"""

with open("kaggle_benchmark/benchmark_kaggle.py", "w") as f:
    f.write(python_code)
