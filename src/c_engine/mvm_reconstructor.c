#include <stdlib.h>
#include <math.h>

#if defined(__x86_64__) || defined(_M_X64)
#include <immintrin.h>
#endif

void reconstruct_zernikes(const float *slopes,
                           const float *G_plus,
                           float       *zernikes,
                           int n_zernike, int n_slopes)
{
    for (int j = 0; j < n_zernike; j++) {
        const float *row = G_plus + j * n_slopes;
        
#if defined(__x86_64__) || defined(_M_X64)
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
#else
        // Fallback for ARM64 / Apple Silicon
        float acc = 0.0f;
        for (int k = 0; k < n_slopes; k++) {
            acc += row[k] * slopes[k];
        }
        zernikes[j] = acc;
#endif
    }
}

void compute_actuator_map(const float *zernikes,
                           const float *C_DM,
                           float       *actuators,
                           int n_actuators, int n_zernike,
                           float clip_min, float clip_max)
{
    for (int i = 0; i < n_actuators; i++) {
        const float *row = C_DM + i * n_zernike;
        
#if defined(__x86_64__) || defined(_M_X64)
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
#else
        float acc = 0.0f;
        for (int j = 0; j < n_zernike; j++) {
            acc += row[j] * zernikes[j];
        }
        acc = fmaxf(clip_min, fminf(clip_max, acc));
        actuators[i] = acc;
#endif
    }
}
