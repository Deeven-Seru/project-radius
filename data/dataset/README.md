# Dataset

Populated by running `scripts/generate_dataset.py` then `scripts/export_gplus.py`.

## Files (after generation)
| File | Description |
|:-----|:-----------|
| `frame_0000.bmp` ... `frame_0499.bmp` | 500 SH-WFS detector images (8-bit BMP) |
| `ground_truth.csv` | OOPAO Zernike coefficients (500 x 20) |
| `valid_mask.csv` | Binary subaperture validity mask (400 elements) |
| `g_plus.csv` | Pseudo-inverse interaction matrix (20 x 632) |
| `dm_coupling.csv` | DM influence function matrix (357 x 20) |
