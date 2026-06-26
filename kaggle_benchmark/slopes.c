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

