import os
import time
import ctypes
import numpy as np

geom_code = '''#ifndef GEOMETRY_H
#define GEOMETRY_H

/**
 * LensletConfig - complete description of the SH-WFS microlens geometry.
 *
 * Typical ISRO 20x20 values:
 *   n_sub=400, n_valid=316, sub_px=8, pixel_scale=0.5
 */
typedef struct {
    int   n_sub;
    int   n_valid;
    int   sub_px;
    float pixel_scale;
    int  *valid_mask;
} LensletConfig;

#endif /* GEOMETRY_H */
'''
slopes_code = '''#include <stdlib.h>
#include "geometry.h"

#include <math.h>

/**
 * compute_slopes - Center of Gravity centroiding over valid subapertures.
 */
void compute_slopes(const float *img_data,
                    float       *slopes,
                    const int   *valid_mask,
                    int          n_sub,
                    int          n_valid,
                    int          sub_px)
{
    int N_1d = (int)sqrt((double)n_sub);
    int img_cols = sub_px * N_1d;
    int valid_idx = 0;

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;
        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float I = img_data[(row0+dy)*img_cols + (col0+dx)];
                sum_I  += I;
                sum_xI += (float)dx * I;
                sum_yI += (float)dy * I;
            }
        }
        float cx = (sum_I > 0.0f) ? sum_xI/sum_I : (sub_px - 1.0f)*0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI/sum_I : (sub_px - 1.0f)*0.5f;
        slopes[valid_idx]           = cx;
        slopes[valid_idx + n_valid] = cy;
        valid_idx++;
    }
}

/**
 * compute_slopes_enhanced - Center of Gravity centroiding with background thresholding
 *                           and sub-pixel grid shift compensation.
 */
void compute_slopes_enhanced(const float *img_data,
                             float       *slopes,
                             const int   *valid_mask,
                             int          n_sub,
                             int          n_valid,
                             int          sub_px,
                             float        bg_threshold,
                             float        shift_x,
                             float        shift_y)
{
    int N_1d = (int)sqrt((double)n_sub);
    int img_cols = sub_px * N_1d;
    int valid_idx = 0;

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;
        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float I = img_data[(row0+dy)*img_cols + (col0+dx)];
                float val = I - bg_threshold;
                if (val < 0.0f) val = 0.0f;
                sum_I  += val;
                sum_xI += (float)dx * val;
                sum_yI += (float)dy * val;
            }
        }
        float cx = (sum_I > 0.0f) ? sum_xI/sum_I : (sub_px - 1.0f)*0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI/sum_I : (sub_px - 1.0f)*0.5f;
        
        // Subtract shift_x and shift_y to correct for alignment drift
        slopes[valid_idx]           = cx - shift_x;
        slopes[valid_idx + n_valid] = cy - shift_y;
        valid_idx++;
    }
}

'''
mvm_code = '''#include <stdlib.h>
#include <immintrin.h>

void reconstruct_zernikes(const float *slopes,
                           const float *G_plus,
                           float       *zernikes,
                           int n_zernike, int n_slopes)
{
    for (int j = 0; j < n_zernike; j++) {
        __m256 acc_v = _mm256_setzero_ps();
        const float *row = G_plus + j * n_slopes;
        int k = 0;
        
        // Process 8 floats at a time
        for (; k <= n_slopes - 8; k += 8) {
            __m256 r_v = _mm256_loadu_ps(&row[k]);
            __m256 s_v = _mm256_loadu_ps(&slopes[k]);
            acc_v = _mm256_fmadd_ps(r_v, s_v, acc_v);
        }
        
        // Horizontal add of the 8 vector elements
        float acc_arr[8];
        _mm256_storeu_ps(acc_arr, acc_v);
        float acc = acc_arr[0] + acc_arr[1] + acc_arr[2] + acc_arr[3] + 
                    acc_arr[4] + acc_arr[5] + acc_arr[6] + acc_arr[7];
        
        // Tail loop for remaining elements
        for (; k < n_slopes; k++) {
            acc += row[k] * slopes[k];
        }
        zernikes[j] = acc;
    }
}

void compute_actuator_map(const float *zernikes,
                           const float *C_DM,
                           float       *actuators,
                           int n_actuators, int n_zernike)
{
    for (int i = 0; i < n_actuators; i++) {
        __m256 acc_v = _mm256_setzero_ps();
        const float *row = C_DM + i * n_zernike;
        int j = 0;
        
        for (; j <= n_zernike - 8; j += 8) {
            __m256 r_v = _mm256_loadu_ps(&row[j]);
            __m256 z_v = _mm256_loadu_ps(&zernikes[j]);
            acc_v = _mm256_fmadd_ps(r_v, z_v, acc_v);
        }
        
        float acc_arr[8];
        _mm256_storeu_ps(acc_arr, acc_v);
        float acc = acc_arr[0] + acc_arr[1] + acc_arr[2] + acc_arr[3] + 
                    acc_arr[4] + acc_arr[5] + acc_arr[6] + acc_arr[7];
                    
        for (; j < n_zernike; j++) {
            acc += row[j] * zernikes[j];
        }
        actuators[i] = acc;
    }
}
'''

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

print(f"Benchmarking extreme parameters: {n_sub} lenslets, {n_zernike} Zernikes, {n_actuators} Actuators")
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

print(f"\nTotal Time for 1000 iterations: {total_time:.4f} s")
print(f"Mean Latency per Frame: {per_frame*1000:.4f} ms")
print(f"Max Frequency: {1.0/per_frame:.2f} Hz")

if per_frame*1000 < 10.0:
    print("\nSUCCESS: AVX2 Optimization beat the 10ms ISRO deadline!")
else:
    print("\nWARNING: Latency exceeded 10ms deadline.")

