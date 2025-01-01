#ifndef GEOMETRY_H
#define GEOMETRY_H

/**
 * LensletConfig - complete description of the SH-WFS microlens geometry.
 *
 * Typical ISRO 20x20 values:
 *   n_sub=400, n_valid=316, sub_px=8, pixel_scale=0.5
 */
typedef struct {
    int   n_sub;
    int   n_valid;
    int   sub_px;
    float pixel_scale;
    int  *valid_mask;
} LensletConfig;

#endif /* GEOMETRY_H */
