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


