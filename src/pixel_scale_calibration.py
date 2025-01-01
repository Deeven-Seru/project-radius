"""
pixel_scale_calibration.py
--------------------------
Derives the pixel-to-phase scaling factor from sensor parameters.
"""
import numpy as np

def compute_pixel_scale(lambda_m=0.5e-6, f_lens_m=2.5e-3, sub_px=8, d_sub_m=8.0/20):
    pixel_pitch = d_sub_m / sub_px
    return f_lens_m / (lambda_m * d_sub_m) * pixel_pitch

if __name__ == '__main__':
    print(f"Pixel-to-phase scale: {compute_pixel_scale():.6e} rad/pixel")
