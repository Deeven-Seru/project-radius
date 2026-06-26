#include <stdlib.h>

void reconstruct_zernikes(const float *slopes,
                           const float *G_plus,
                           float       *zernikes,
                           int n_zernike, int n_slopes)
{
    for (int j = 0; j < n_zernike; j++) {
        float acc = 0.0f;
        const float *row = G_plus + j * n_slopes;
        for (int k = 0; k < n_slopes; k++) acc += row[k] * slopes[k];
        zernikes[j] = acc;
    }
}

void compute_actuator_map(const float *zernikes,
                           const float *C_DM,
                           float       *actuators,
                           int n_actuators, int n_zernike)
{
    for (int i = 0; i < n_actuators; i++) {
        float acc = 0.0f;
        const float *row = C_DM + i * n_zernike;
        for (int j = 0; j < n_zernike; j++) acc += row[j] * zernikes[j];
        actuators[i] = acc;
    }
}
