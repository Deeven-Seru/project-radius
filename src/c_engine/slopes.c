#include <stdlib.h>
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
 *                         threshold multiplier to improve robustness.
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
    int img_cols = sub_px * N_1d;
    int valid_idx = 0;

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;
        float sum_I = 0.0f, sum_xI = 0.0f, sum_yI = 0.0f;
        float vals[2048];
        int idx = 0;
        float mean = 0.0f;
        for (int dy = 0; dy < sub_px; dy++) {
            for (int dx = 0; dx < sub_px; dx++) {
                float I = img_data[(row0+dy)*img_cols + (col0+dx)];
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
        slopes[valid_idx]           = cx - shift_x;
        slopes[valid_idx + n_valid] = cy - shift_y;
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
    int img_cols = sub_px * N_1d;
    int valid_idx = 0;

    __m256 zero_vec = _mm256_setzero_ps();
    __m256 bg_vec = _mm256_set1_ps(bg_threshold);
    __m256 max_val_vec = _mm256_set1_ps(10000.0f);
    __m256 dx_base = _mm256_set_ps(7.0f, 6.0f, 5.0f, 4.0f, 3.0f, 2.0f, 1.0f, 0.0f);

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        __m256 sum_I_vec = zero_vec;
        __m256 sum_xI_vec = zero_vec;
        __m256 sum_yI_vec = zero_vec;

        for (int dy = 0; dy < sub_px; dy++) {
            __m256 dy_vec = _mm256_set1_ps((float)dy);
            const float *row_ptr = img_data + (row0 + dy) * img_cols + col0;

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

        slopes[valid_idx]           = cx - shift_x;
        slopes[valid_idx + n_valid] = cy - shift_y;
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
    int img_cols = sub_px * N_1d;
    int valid_idx = 0;

    float32x4_t zero_vec = vdupq_n_f32(0.0f);
    float32x4_t bg_vec = vdupq_n_f32(bg_threshold);
    float32x4_t max_val_vec = vdupq_n_f32(10000.0f);
    float32x4_t dx_base = {0.0f, 1.0f, 2.0f, 3.0f};

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;

        float32x4_t sum_I_vec = zero_vec;
        float32x4_t sum_xI_vec = zero_vec;
        float32x4_t sum_yI_vec = zero_vec;

        for (int dy = 0; dy < sub_px; dy++) {
            float32x4_t dy_vec = vdupq_n_f32((float)dy);
            const float *row_ptr = img_data + (row0 + dy) * img_cols + col0;

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

        slopes[valid_idx]           = cx - shift_x;
        slopes[valid_idx + n_valid] = cy - shift_y;
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
        
        slopes[valid_idx]           = cx - shift_x;
        slopes[valid_idx + n_valid] = cy - shift_y;
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
    int img_cols = sub_px * N_1d;
    int valid_idx = 0;

    for (int k = 0; k < n_sub; k++) {
        if (!valid_mask[k]) continue;
        int row0 = (k / N_1d) * sub_px;
        int col0 = (k % N_1d) * sub_px;
        
        // Initial CoG (Thresholded)
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
                    float I = img_data[(row0+dy)*img_cols + (col0+dx)];
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
        
        slopes[valid_idx]           = cx - shift_x;
        slopes[valid_idx + n_valid] = cy - shift_y;
        valid_idx++;
    }
}


