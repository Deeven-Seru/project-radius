#include <math.h>

/**
 * Calculates the variance of an array of values (e.g., a specific Zernike mode over time).
 */
float calculate_variance(const float* values, int num_samples) {
    if (num_samples <= 1) return 0.0f;
    
    float sum = 0.0f;
    for (int i = 0; i < num_samples; i++) {
        sum += values[i];
    }
    float mean = sum / num_samples;
    
    float variance_sum = 0.0f;
    for (int i = 0; i < num_samples; i++) {
        float diff = values[i] - mean;
        variance_sum += (diff * diff);
    }
    return variance_sum / (num_samples - 1);
}

/**
 * Estimates the Fried parameter (r0) using the variance of the Zernike coefficients.
 * Based on Noll's theory of atmospheric turbulence:
 * variance(a_j) = c_j * (D / r0)^(5/3)
 * where c_j is the Noll covariance coefficient for mode j, and D is aperture diameter.
 * 
 * @param zernike_variances Array of variances for each Zernike mode
 * @param noll_coefficients Pre-computed constants for each mode (c_j)
 * @param num_modes Number of modes evaluated
 * @param aperture_diameter Telescope/Pupil diameter (D) in meters
 * @return Estimated Fried parameter r0 in meters
 */
float estimate_fried_parameter(const float* zernike_variances, const float* noll_coefficients, 
                               int num_modes, float aperture_diameter) {
    float sum_r0 = 0.0f;
    int valid_modes = 0;
    
    // Skip mode 0, 1, 2 (Piston, Tip, Tilt) as they are often corrupted by tracking errors/vibration.
    // Start from mode 3 (Defocus)
    for (int i = 3; i < num_modes; i++) {
        if (zernike_variances[i] > 0.0f && noll_coefficients[i] > 0.0f) {
            // (D/r0)^(5/3) = var / c_j
            // r0 = D / (var / c_j)^(3/5)
            float ratio = zernike_variances[i] / noll_coefficients[i];
            float r0_mode = aperture_diameter / powf(ratio, 0.6f); 
            sum_r0 += r0_mode;
            valid_modes++;
        }
    }
    
    if (valid_modes > 0) {
        return sum_r0 / valid_modes; // Average r0 estimation across modes
    }
    return 0.1f; // Default typical r0 (10 cm)
}

/**
 * Estimates coherence time (tau_0) using temporal autocorrelation 
 * This is a highly simplified proxy function for real-time benchmarking.
 */
float estimate_coherence_time(const float* frame_variances, int num_samples, float frame_interval_ms) {
    // In a full system, this involves an FFT to find the Greenwood frequency (f_G).
    // tau_0 = 0.314 / f_G
    // For benchmark purposes, we simulate the O(N) reduction step.
    float mean_var = calculate_variance(frame_variances, num_samples);
    return mean_var * 0.001f + frame_interval_ms; // Mock math placeholder
}
