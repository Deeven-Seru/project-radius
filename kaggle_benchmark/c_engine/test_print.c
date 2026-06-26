#include <stdio.h>
void debug_print(const float *slopes, const float *G_plus, float *zernikes, int n_zernike, int n_slopes) {
    printf("C Engine Debug:\n");
    printf("n_zernike = %d, n_slopes = %d\n", n_zernike, n_slopes);
    printf("slopes[0] = %f, slopes[1] = %f\n", slopes[0], slopes[1]);
    printf("G_plus[0] = %f, G_plus[1] = %f\n", G_plus[0], G_plus[1]);
}
