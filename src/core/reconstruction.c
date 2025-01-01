#include <stdint.h>
#include <stdlib.h>

typedef struct {
    float x;
    float y;
} Point2D;

/**
 * Calculates slopes (deviation from reference centroids).
 */
void calculate_slopes(const Point2D* measured_centroids, const Point2D* reference_centroids, 
                      int num_lenslets, float* out_slopes_x, float* out_slopes_y) {
    for (int i = 0; i < num_lenslets; i++) {
        out_slopes_x[i] = measured_centroids[i].x - reference_centroids[i].x;
        out_slopes_y[i] = measured_centroids[i].y - reference_centroids[i].y;
    }
}

/**
 * Real-time Wavefront Reconstruction (Matrix-Vector Multiplication).
 * 
 * In advanced AO systems, the inverse geometry matrix (G_plus) is pre-computed offline 
 * using our "Crosstalk-Free Analytical Method" (Method B). 
 * The real-time constraint (<10ms) only requires a fast Matrix-Vector multiply.
 * 
 * @param slopes_x Array of x slopes (size N)
 * @param slopes_y Array of y slopes (size N)
 * @param num_lenslets Number of valid subapertures (N)
 * @param G_plus Pre-computed reconstruction matrix (size M x 2N)
 * @param num_zernikes Number of Zernike modes to reconstruct (M)
 * @param out_coefficients Output array for Zernike coefficients (size M)
 */
void reconstruct_wavefront(const float* slopes_x, const float* slopes_y, int num_lenslets,
                           const float* G_plus, int num_zernikes, float* out_coefficients) {
    
    for (int i = 0; i < num_zernikes; i++) {
        float sum = 0.0f;
        // Multiply row i of G_plus with the concatenated slope vector [s_x, s_y]
        for (int j = 0; j < num_lenslets; j++) {
            // X slopes
            sum += G_plus[i * (2 * num_lenslets) + j] * slopes_x[j];
            // Y slopes (offset by num_lenslets)
            sum += G_plus[i * (2 * num_lenslets) + num_lenslets + j] * slopes_y[j];
        }
        out_coefficients[i] = sum;
    }
}

/**
 * Derives the Actuator Map for the Deformable Mirror.
 * MVM of the inverse coupling matrix and reconstructed wavefront phases.
 */
void calculate_actuator_map(const float* wavefront_phases, const float* inverse_coupling_matrix, 
                            int num_actuators, float* out_actuator_commands) {
    for (int i = 0; i < num_actuators; i++) {
        float sum = 0.0f;
        for (int j = 0; j < num_actuators; j++) {
            sum += inverse_coupling_matrix[i * num_actuators + j] * wavefront_phases[j];
        }
        out_actuator_commands[i] = sum; // Actuator stroke length
    }
}

/**
 * Generates a 2D Phase Map from Zernike coefficients.
 * Very simplified mockup: W(x,y) = sum(a_i * Z_i(x,y))
 */
void generate_phase_map(const float* coefficients, int num_zernikes, 
                        int width, int height, float* out_phase_map) {
    for (int y = 0; y < height; y++) {
        for (int x = 0; x < width; x++) {
            float phase = 0.0f;
            // Normalize coordinates to [-1, 1]
            float nx = (x - width/2.0f) / (width/2.0f);
            float ny = (y - height/2.0f) / (height/2.0f);
            
            // Mock evaluation of first few Zernike modes (Tilt, Defocus, Astigmatism)
            // In a real implementation, a recursive Zernike evaluator would be used.
            if (num_zernikes > 1) phase += coefficients[1] * nx; // Tip
            if (num_zernikes > 2) phase += coefficients[2] * ny; // Tilt
            if (num_zernikes > 3) phase += coefficients[3] * (2.0f*(nx*nx + ny*ny) - 1.0f); // Defocus
            if (num_zernikes > 4) phase += coefficients[4] * (2.0f*nx*ny); // Astigmatism
            
            // Fill the map
            out_phase_map[y * width + x] = phase;
        }
    }
}

