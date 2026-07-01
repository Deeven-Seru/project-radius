#include <stdlib.h>
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

