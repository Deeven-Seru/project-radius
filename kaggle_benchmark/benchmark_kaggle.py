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
                // Glitch-resistant input sanitization
                if (isnan(I) || isinf(I) || I < 0.0f || I > 10000.0f) {
                    I = 0.0f;
                }
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
 * compute_slopes_weighted - Weighted center-of-gravity with per-subap thresholding
 *                         and background subtraction. Adds weight exponent and
 *                         threshold multiplier to improve robustness. Dynamic window
 *                         shifting is applied to compensate for pixel grid shifts.
 */
void compute_slopes_weighted(const float *img_data,
                            float       *slopes,
                            const int   *valid_mask,
                            int          n_sub,
                            int          n_valid,
                            int          sub_px,
                            float        bg_threshold,
                            float        shift_x,
                            float        shift_y,
                            float        weight_exp,
                            float        thr_mul)
{
    int N_1d = (int)sqrt((double)n_sub);
    int img_size = sub_px * N_1d;
    int img_cols = img_size;
    int valid_idx = 0;

    int offset_x = (int)roundf(shift_x);
    int offset_y = (int)roundf(shift_y);

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        int row0_shifted = row0 + offset_y;
        int col0_shifted = col0 + offset_x;

        if (row0_shifted < 0) row0_shifted = 0;
        if (row0_shifted > img_size - sub_px) row0_shifted = img_size - sub_px;
        if (col0_shifted < 0) col0_shifted = 0;
        if (col0_shifted > img_size - sub_px) col0_shifted = img_size - sub_px;

        float local_shift_x = shift_x - (float)(col0_shifted - col0);
        float local_shift_y = shift_y - (float)(row0_shifted - row0);

        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        float vals[2048];
        int idx = 0;
        float mean = 0.0f;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float I = img_data[(row0_shifted+dy)*img_cols + (col0_shifted+dx)];
                float v = I - bg_threshold;
                if (v < 0.0f) v = 0.0f;
                vals[idx++] = v;
                mean += v;
            }
        }
        mean = mean / (float)idx;
        float var = 0.0f;
        for (int i = 0; i < idx; i++) {
            float d = vals[i] - mean;
            var += d*d;
        }
        float std = (idx > 1) ? sqrtf(var / (float)(idx-1)) : 0.0f;
        float thr = mean + thr_mul * std;

        idx = 0;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float v = vals[idx++];
                if (v < thr) v = 0.0f;
                float w;
                if (weight_exp == 1.0f) w = v;
                else if (weight_exp == 0.0f) w = (v > 0.0f) ? 1.0f : 0.0f;
                else w = powf(v, weight_exp);
                sum_I  += w;
                sum_xI += (float)dx * w;
                sum_yI += (float)dy * w;
            }
        }

        float cx = (sum_I > 0.0f) ? sum_xI/sum_I : (sub_px - 1.0f)*0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI/sum_I : (sub_px - 1.0f)*0.5f;
        slopes[valid_idx]           = cx - local_shift_x;
        slopes[valid_idx + n_valid] = cy - local_shift_y;
        valid_idx++;
    }
}

#if defined(__x86_64__) || defined(_M_X64)
#include <immintrin.h>
__attribute__((target("avx2,fma")))
void compute_slopes_enhanced_avx2(const float *img_data,
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
    int img_size = sub_px * N_1d;
    int img_cols = img_size;
    int valid_idx = 0;

    int offset_x = (int)roundf(shift_x);
    int offset_y = (int)roundf(shift_y);

    __m256 zero_vec = _mm256_setzero_ps();
    __m256 bg_vec = _mm256_set1_ps(bg_threshold);
    __m256 max_val_vec = _mm256_set1_ps(10000.0f);
    __m256 dx_base = _mm256_set_ps(7.0f, 6.0f, 5.0f, 4.0f, 3.0f, 2.0f, 1.0f, 0.0f);

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        int row0_shifted = row0 + offset_y;
        int col0_shifted = col0 + offset_x;

        if (row0_shifted < 0) row0_shifted = 0;
        if (row0_shifted > img_size - sub_px) row0_shifted = img_size - sub_px;
        if (col0_shifted < 0) col0_shifted = 0;
        if (col0_shifted > img_size - sub_px) col0_shifted = img_size - sub_px;

        float local_shift_x = shift_x - (float)(col0_shifted - col0);
        float local_shift_y = shift_y - (float)(row0_shifted - row0);

        __m256 sum_I_vec = zero_vec;
        __m256 sum_xI_vec = zero_vec;
        __m256 sum_yI_vec = zero_vec;

        for (int dy = 0; dy < sub_px; dy++) {
            __m256 dy_vec = _mm256_set1_ps((float)dy);
            const float *row_ptr = img_data + (row0_shifted + dy) * img_cols + col0_shifted;

            for (int dx = 0; dx < sub_px; dx += 8) {
                __m256 I = _mm256_loadu_ps(row_ptr + dx);

                // Sanitization mask: 0.0f <= I <= 10000.0f
                __m256 ge_zero = _mm256_cmp_ps(I, zero_vec, 29); // _CMP_GE_OQ
                __m256 le_max = _mm256_cmp_ps(I, max_val_vec, 18); // _CMP_LE_OQ
                __m256 valid_mask_vec = _mm256_and_ps(ge_zero, le_max);

                // Blend valid pixels with bg_threshold
                __m256 I_sanitized = _mm256_blendv_ps(bg_vec, I, valid_mask_vec);

                // Subtract threshold and clamp to 0
                __m256 val = _mm256_sub_ps(I_sanitized, bg_vec);
                val = _mm256_max_ps(val, zero_vec);

                sum_I_vec = _mm256_add_ps(sum_I_vec, val);

                __m256 dx_vec = _mm256_add_ps(dx_base, _mm256_set1_ps((float)dx));
                sum_xI_vec = _mm256_fmadd_ps(dx_vec, val, sum_xI_vec);
                sum_yI_vec = _mm256_fmadd_ps(dy_vec, val, sum_yI_vec);
            }
        }

        float temp_I[8], temp_xI[8], temp_yI[8];
        _mm256_storeu_ps(temp_I, sum_I_vec);
        _mm256_storeu_ps(temp_xI, sum_xI_vec);
        _mm256_storeu_ps(temp_yI, sum_yI_vec);

        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        for (int i = 0; i < 8; i++) {
            sum_I += temp_I[i];
            sum_xI += temp_xI[i];
            sum_yI += temp_yI[i];
        }

        float cx = (sum_I > 0.0f) ? sum_xI / sum_I : (sub_px - 1.0f) * 0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI / sum_I : (sub_px - 1.0f) * 0.5f;

        slopes[valid_idx]           = cx - local_shift_x;
        slopes[valid_idx + n_valid] = cy - local_shift_y;
        valid_idx++;
    }
}
#elif defined(__aarch64__) || defined(__ARM_NEON)
#include <arm_neon.h>
void compute_slopes_enhanced_neon(const float *img_data,
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
    int img_size = sub_px * N_1d;
    int img_cols = img_size;
    int valid_idx = 0;

    int offset_x = (int)roundf(shift_x);
    int offset_y = (int)roundf(shift_y);

    float32x4_t zero_vec = vdupq_n_f32(0.0f);
    float32x4_t bg_vec = vdupq_n_f32(bg_threshold);
    float32x4_t max_val_vec = vdupq_n_f32(10000.0f);
    float32x4_t dx_base = {0.0f, 1.0f, 2.0f, 3.0f};

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        int row0_shifted = row0 + offset_y;
        int col0_shifted = col0 + offset_x;

        if (row0_shifted < 0) row0_shifted = 0;
        if (row0_shifted > img_size - sub_px) row0_shifted = img_size - sub_px;
        if (col0_shifted < 0) col0_shifted = 0;
        if (col0_shifted > img_size - sub_px) col0_shifted = img_size - sub_px;

        float local_shift_x = shift_x - (float)(col0_shifted - col0);
        float local_shift_y = shift_y - (float)(row0_shifted - row0);

        float32x4_t sum_I_vec = zero_vec;
        float32x4_t sum_xI_vec = zero_vec;
        float32x4_t sum_yI_vec = zero_vec;

        for (int dy = 0; dy < sub_px; dy++) {
            float32x4_t dy_vec = vdupq_n_f32((float)dy);
            const float *row_ptr = img_data + (row0_shifted + dy) * img_cols + col0_shifted;

            for (int dx = 0; dx < sub_px; dx += 4) {
                float32x4_t I = vld1q_f32(row_ptr + dx);

                uint32x4_t ge_zero = vcgeq_f32(I, zero_vec);
                uint32x4_t le_max = vcleq_f32(I, max_val_vec);
                uint32x4_t is_nan = vceqq_f32(I, I);
                uint32x4_t valid_mask_vec = vandq_u32(vandq_u32(ge_zero, le_max), is_nan);

                float32x4_t I_sanitized = vbslq_f32(valid_mask_vec, I, bg_vec);
                float32x4_t val = vsubq_f32(I_sanitized, bg_vec);
                val = vmaxq_f32(val, zero_vec);

                sum_I_vec = vaddq_f32(sum_I_vec, val);

                float32x4_t dx_vec = vaddq_f32(dx_base, vdupq_n_f32((float)dx));
                sum_xI_vec = vmlaq_f32(sum_xI_vec, dx_vec, val);
                sum_yI_vec = vmlaq_f32(sum_yI_vec, dy_vec, val);
            }
        }

        float sum_I = vaddvq_f32(sum_I_vec);
        float sum_xI = vaddvq_f32(sum_xI_vec);
        float sum_yI = vaddvq_f32(sum_yI_vec);

        float cx = (sum_I > 0.0f) ? sum_xI / sum_I : (sub_px - 1.0f) * 0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI / sum_I : (sub_px - 1.0f) * 0.5f;

        slopes[valid_idx]           = cx - local_shift_x;
        slopes[valid_idx + n_valid] = cy - local_shift_y;
        valid_idx++;
    }
}
#endif

/**
 * compute_slopes_enhanced - Center of Gravity centroiding with background thresholding
 *                           and sub-pixel grid shift compensation. Utilizes runtime
 *                           dynamic dispatching for vectorized execution.
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
#if defined(__x86_64__) || defined(_M_X64)
    if (__builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma")) {
        compute_slopes_enhanced_avx2(img_data, slopes, valid_mask, n_sub, n_valid, sub_px, bg_threshold, shift_x, shift_y);
        return;
    }
#elif defined(__aarch64__) || defined(__ARM_NEON)
    if (sub_px % 4 == 0) {
        compute_slopes_enhanced_neon(img_data, slopes, valid_mask, n_sub, n_valid, sub_px, bg_threshold, shift_x, shift_y);
        return;
    }
#endif

    // Fallback: Scalar Implementation
    int N_1d = (int)sqrt((double)n_sub);
    int img_size = sub_px * N_1d;
    int img_cols = img_size;
    int valid_idx = 0;

    int offset_x = (int)roundf(shift_x);
    int offset_y = (int)roundf(shift_y);

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        int row0_shifted = row0 + offset_y;
        int col0_shifted = col0 + offset_x;

        if (row0_shifted < 0) row0_shifted = 0;
        if (row0_shifted > img_size - sub_px) row0_shifted = img_size - sub_px;
        if (col0_shifted < 0) col0_shifted = 0;
        if (col0_shifted > img_size - sub_px) col0_shifted = img_size - sub_px;

        float local_shift_x = shift_x - (float)(col0_shifted - col0);
        float local_shift_y = shift_y - (float)(row0_shifted - row0);

        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float I = img_data[(row0_shifted+dy)*img_cols + (col0_shifted+dx)];
                // Glitch-resistant input sanitization
                if (isnan(I) || isinf(I) || I < 0.0f || I > 10000.0f) {
                    I = bg_threshold;
                }
                float val = I - bg_threshold;
                if (val < 0.0f) val = 0.0f;
                sum_I  += val;
                sum_xI += (float)dx * val;
                sum_yI += (float)dy * val;
            }
        }
        float cx = (sum_I > 0.0f) ? sum_xI/sum_I : (sub_px - 1.0f)*0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI/sum_I : (sub_px - 1.0f)*0.5f;
        
        slopes[valid_idx]           = cx - local_shift_x;
        slopes[valid_idx + n_valid] = cy - local_shift_y;
        valid_idx++;
    }
}

/**
 * compute_slopes_iwcog - Iteratively Weighted Center of Gravity (IWCoG)
 *                        Highly robust to noise and sub-pixel misalignment.
 */
void compute_slopes_iwcog(const float *img_data,
                          float       *slopes,
                          const int   *valid_mask,
                          int          n_sub,
                          int          n_valid,
                          int          sub_px,
                          float        bg_threshold,
                          float        sigma,
                          int          max_iters,
                          float        shift_x,
                          float        shift_y)
{
    int N_1d = (int)sqrt((double)n_sub);
    int img_size = sub_px * N_1d;
    int img_cols = img_size;
    int valid_idx = 0;

    int offset_x = (int)roundf(shift_x);
    int offset_y = (int)roundf(shift_y);

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        int row0_shifted = row0 + offset_y;
        int col0_shifted = col0 + offset_x;

        if (row0_shifted < 0) row0_shifted = 0;
        if (row0_shifted > img_size - sub_px) row0_shifted = img_size - sub_px;
        if (col0_shifted < 0) col0_shifted = 0;
        if (col0_shifted > img_size - sub_px) col0_shifted = img_size - sub_px;

        float local_shift_x = shift_x - (float)(col0_shifted - col0);
        float local_shift_y = shift_y - (float)(row0_shifted - row0);
        
        // Initial CoG (Thresholded)
        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float I = img_data[(row0_shifted+dy)*img_cols + (col0_shifted+dx)];
                float val = I - bg_threshold;
                if (val < 0.0f) val = 0.0f;
                sum_I  += val;
                sum_xI += (float)dx * val;
                sum_yI += (float)dy * val;
            }
        }
        
        float cx = (sum_I > 0.0f) ? sum_xI/sum_I : (sub_px - 1.0f)*0.5f;
        float cy = (sum_I > 0.0f) ? sum_yI/sum_I : (sub_px - 1.0f)*0.5f;
        
        float inv_2sig2 = 1.0f / (2.0f * sigma * sigma);
        
        // Iterative updates
        for (int iter = 0; iter < max_iters; iter++) {
            float w_sum_I = 0.0f;
            float w_sum_xI = 0.0f;
            float w_sum_yI = 0.0f;
            
            int min_x = (int)(cx - 3.0f * sigma);
            if (min_x < 0) min_x = 0;
            int max_x = (int)(cx + 3.0f * sigma) + 1;
            if (max_x > sub_px) max_x = sub_px;
            
            int min_y = (int)(cy - 3.0f * sigma);
            if (min_y < 0) min_y = 0;
            int max_y = (int)(cy + 3.0f * sigma) + 1;
            if (max_y > sub_px) max_y = sub_px;

            for (int dy = min_y; dy < max_y; dy++) {
                for (int dx = min_x; dx < max_x; dx++) {
                    float I = img_data[(row0_shifted+dy)*img_cols + (col0_shifted+dx)];
                    float v = I - bg_threshold;
                    if (v < 0.0f) v = 0.0f;
                    
                    // Gaussian weight
                    float dist_sq = (dx - cx)*(dx - cx) + (dy - cy)*(dy - cy);
                    float weight = expf(-dist_sq * inv_2sig2);
                    
                    float W_val = v * weight;
                    w_sum_I  += W_val;
                    w_sum_xI += (float)dx * W_val;
                    w_sum_yI += (float)dy * W_val;
                }
            }
            
            if (w_sum_I > 0.0f) {
                float new_cx = w_sum_xI / w_sum_I;
                float new_cy = w_sum_yI / w_sum_I;
                
                // Check convergence
                float diff = (new_cx - cx)*(new_cx - cx) + (new_cy - cy)*(new_cy - cy);
                cx = new_cx;
                cy = new_cy;
                if (diff < 1e-4f) break;
            } else {
                break;
            }
        }
        
        slopes[valid_idx]           = cx - local_shift_x;
        slopes[valid_idx + n_valid] = cy - local_shift_y;
        valid_idx++;
    }
}



'''
mvm_code = '''#include <stdlib.h>
#include <math.h>

#if defined(__x86_64__) || defined(_M_X64)
#include <immintrin.h>

/**
 * AVX2 + FMA Vectorized Reconstruction (x86_64 specific)
 */
__attribute__((target("avx2,fma")))
void reconstruct_zernikes_avx2(const float *slopes,
                               const float *G_plus,
                               float       *zernikes,
                               int n_zernike, int n_slopes)
{
    for (int j = 0; j < n_zernike; j++) {
        const float *row = G_plus + j * n_slopes;
        __m256 acc_v = _mm256_setzero_ps();
        int k = 0;
        for (; k <= n_slopes - 8; k += 8) {
            __m256 r_v = _mm256_loadu_ps(&row[k]);
            __m256 s_v = _mm256_loadu_ps(&slopes[k]);
            acc_v = _mm256_fmadd_ps(r_v, s_v, acc_v);
        }
        float acc_arr[8];
        _mm256_storeu_ps(acc_arr, acc_v);
        float acc = acc_arr[0] + acc_arr[1] + acc_arr[2] + acc_arr[3] + 
                    acc_arr[4] + acc_arr[5] + acc_arr[6] + acc_arr[7];
        for (; k < n_slopes; k++) {
            acc += row[k] * slopes[k];
        }
        zernikes[j] = acc;
    }
}

/**
 * AVX2 + FMA Vectorized DM Mapping (x86_64 specific)
 */
__attribute__((target("avx2,fma")))
void compute_actuator_map_avx2(const float *zernikes,
                               const float *C_DM,
                               float       *actuators,
                               int n_actuators, int n_zernike,
                               float clip_min, float clip_max)
{
    for (int i = 0; i < n_actuators; i++) {
        const float *row = C_DM + i * n_zernike;
        __m256 acc_v = _mm256_setzero_ps();
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
        acc = fmaxf(clip_min, fminf(clip_max, acc));
        actuators[i] = acc;
    }
}
#endif

#if defined(__ARM_NEON) || defined(__aarch64__)
#include <arm_neon.h>

/**
 * ARM NEON Vectorized Reconstruction (ARM64 specific)
 */
void reconstruct_zernikes_neon(const float *slopes,
                               const float *G_plus,
                               float       *zernikes,
                               int n_zernike, int n_slopes)
{
    for (int j = 0; j < n_zernike; j++) {
        const float *row = G_plus + j * n_slopes;
        float32x4_t acc_v = vdupq_n_f32(0.0f);
        int k = 0;
        for (; k <= n_slopes - 4; k += 4) {
            float32x4_t r_v = vld1q_f32(&row[k]);
            float32x4_t s_v = vld1q_f32(&slopes[k]);
            acc_v = vmlaq_f32(acc_v, r_v, s_v);
        }
        float acc = vaddvq_f32(acc_v);
        for (; k < n_slopes; k++) {
            acc += row[k] * slopes[k];
        }
        zernikes[j] = acc;
    }
}

/**
 * ARM NEON Vectorized DM Mapping (ARM64 specific)
 */
void compute_actuator_map_neon(const float *zernikes,
                               const float *C_DM,
                               float       *actuators,
                               int n_actuators, int n_zernike,
                               float clip_min, float clip_max)
{
    for (int i = 0; i < n_actuators; i++) {
        const float *row = C_DM + i * n_zernike;
        float32x4_t acc_v = vdupq_n_f32(0.0f);
        int j = 0;
        for (; j <= n_zernike - 4; j += 4) {
            float32x4_t r_v = vld1q_f32(&row[j]);
            float32x4_t z_v = vld1q_f32(&zernikes[j]);
            acc_v = vmlaq_f32(acc_v, r_v, z_v);
        }
        float acc = vaddvq_f32(acc_v);
        for (; j < n_zernike; j++) {
            acc += row[j] * zernikes[j];
        }
        acc = fmaxf(clip_min, fminf(clip_max, acc));
        actuators[i] = acc;
    }
}
#endif

/**
 * Scalar Fallback - Reconstruction
 */
void reconstruct_zernikes_scalar(const float *slopes,
                                 const float *G_plus,
                                 float       *zernikes,
                                 int n_zernike, int n_slopes)
{
    for (int j = 0; j < n_zernike; j++) {
        const float *row = G_plus + j * n_slopes;
        float acc = 0.0f;
        for (int k = 0; k < n_slopes; k++) {
            acc += row[k] * slopes[k];
        }
        zernikes[j] = acc;
    }
}

/**
 * Scalar Fallback - DM Mapping
 */
void compute_actuator_map_scalar(const float *zernikes,
                                 const float *C_DM,
                                 float       *actuators,
                                 int n_actuators, int n_zernike,
                                 float clip_min, float clip_max)
{
    for (int i = 0; i < n_actuators; i++) {
        const float *row = C_DM + i * n_zernike;
        float acc = 0.0f;
        for (int j = 0; j < n_zernike; j++) {
            acc += row[j] * zernikes[j];
        }
        acc = fmaxf(clip_min, fminf(clip_max, acc));
        actuators[i] = acc;
    }
}

/**
 * Public Entry Point: Zernike Reconstruction
 * Performs runtime dynamic dispatch checking CPU capabilities.
 */
void reconstruct_zernikes(const float *slopes,
                           const float *G_plus,
                           float       *zernikes,
                           int n_zernike, int n_slopes)
{
#if defined(__x86_64__) || defined(_M_X64)
    if (__builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma")) {
        reconstruct_zernikes_avx2(slopes, G_plus, zernikes, n_zernike, n_slopes);
        return;
    }
#elif defined(__aarch64__) || defined(__ARM_NEON)
    reconstruct_zernikes_neon(slopes, G_plus, zernikes, n_zernike, n_slopes);
    return;
#endif
    reconstruct_zernikes_scalar(slopes, G_plus, zernikes, n_zernike, n_slopes);
}

/**
 * Public Entry Point: DM Actuator Stroke Mapping
 * Performs runtime dynamic dispatch checking CPU capabilities.
 */
void compute_actuator_map(const float *zernikes,
                           const float *C_DM,
                           float       *actuators,
                           int n_actuators, int n_zernike,
                           float clip_min, float clip_max)
{
#if defined(__x86_64__) || defined(_M_X64)
    if (__builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma")) {
        compute_actuator_map_avx2(zernikes, C_DM, actuators, n_actuators, n_zernike, clip_min, clip_max);
        return;
    }
#elif defined(__aarch64__) || defined(__ARM_NEON)
    compute_actuator_map_neon(zernikes, C_DM, actuators, n_actuators, n_zernike, clip_min, clip_max);
    return;
#endif
    compute_actuator_map_scalar(zernikes, C_DM, actuators, n_actuators, n_zernike, clip_min, clip_max);
}

/**
 * Zernike Decoupled Kalman Filter (Z-DKF)
 * Performs optimal temporal filtering and one-step predictive estimation.
 */
void apply_kalman_filter(const float *zernikes_in,
                         float       *zernikes_out,
                         float       *predicted_zernikes,
                         const float *a_coeffs,
                         const float *w_vars,
                         const float *v_vars,
                         float       *x_est,
                         float       *P,
                         int          n_zernike)
{
    for (int j = 0; j < n_zernike; j++) {
        // Skip modes that are insensitive or inactive (represented by extremely tiny measurement noise)
        if (v_vars[j] < 1e-25f) {
            zernikes_out[j] = zernikes_in[j];
            predicted_zernikes[j] = zernikes_in[j];
            continue;
        }

        // A. Time Update (Predict)
        float x_pred = a_coeffs[j] * x_est[j];
        float P_pred = a_coeffs[j] * a_coeffs[j] * P[j] + w_vars[j];

        // B. Measurement Update (Correct)
        float K = P_pred / (P_pred + v_vars[j]);
        x_est[j] = x_pred + K * (zernikes_in[j] - x_pred);
        P[j] = (1.0f - K) * P_pred;

        zernikes_out[j] = x_est[j];
        
        // C. One-Step Prediction (Predict t+1 state for deformable mirror)
        predicted_zernikes[j] = a_coeffs[j] * x_est[j];
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

