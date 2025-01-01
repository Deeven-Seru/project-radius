#include <stdint.h>
#include <stdlib.h>

// Represents a 2D point (x, y)
typedef struct {
    float x;
    float y;
} Point2D;

/**
 * Calculates the intensity-weighted center of mass (centroid) for each sub-aperture.
 * 
 * @param image_data 1D array of 8-bit grayscale pixel values
 * @param width Image width in pixels
 * @param height Image height in pixels
 * @param lenslets_per_side Number of lenslets along one axis (assuming square grid)
 * @param out_centroids Pre-allocated array of size (lenslets_per_side^2) to hold results
 */
void calculate_centroids(const uint8_t* image_data, int width, int height, int lenslets_per_side, Point2D* out_centroids) {
    int step_x = width / lenslets_per_side;
    int step_y = height / lenslets_per_side;

    for (int i = 0; i < lenslets_per_side; i++) {
        for (int j = 0; j < lenslets_per_side; j++) {
            
            // Sub-aperture bounding box
            int start_x = j * step_x;
            int start_y = i * step_y;
            int end_x = start_x + step_x;
            int end_y = start_y + step_y;

            double sum_intensity = 0.0;
            double sum_x = 0.0;
            double sum_y = 0.0;

            // Center of mass calculation
            for (int y = start_y; y < end_y; y++) {
                for (int x = start_x; x < end_x; x++) {
                    // Assuming thresholding or dark subtraction is handled elsewhere,
                    // or we can add a basic threshold here to ignore noise.
                    uint8_t pixel_val = image_data[y * width + x];
                    
                    // Simple noise threshold: ignore pixels below 20 intensity
                    if (pixel_val > 20) { 
                        sum_intensity += pixel_val;
                        sum_x += (x * pixel_val);
                        sum_y += (y * pixel_val);
                    }
                }
            }

            int index = i * lenslets_per_side + j;
            if (sum_intensity > 0) {
                out_centroids[index].x = (float)(sum_x / sum_intensity);
                out_centroids[index].y = (float)(sum_y / sum_intensity);
            } else {
                // If sub-aperture is totally dark, fallback to geometric center
                out_centroids[index].x = (float)(start_x + step_x / 2.0);
                out_centroids[index].y = (float)(start_y + step_y / 2.0);
            }
        }
    }
}
