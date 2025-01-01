# Changelog

## [1.0.0] - 2026-06-24

### Added
- C-Engine: CoG centroiding, Zernike MVM, DM actuator mapping (357 actuators)
- OOPAO 500-frame synthetic dataset generator (Von Karman turbulence, multi-layer)
- Calibration pipeline: interaction matrix recording, SVD pseudo-inverse, DM coupling
- Turbulence characterization: r0 via Noll variance, tau0 via autocorrelation 1/e crossing
- End-to-end benchmark script with per-frame latency timing
- 4 theory notebooks: SH-WFS, Zernike polynomials, interaction matrix, turbulence statistics
- Rotating 3D GIF visualizations with labeled X/Y/Z axes and physical colorbars
- Comprehensive README: scope, physics, architecture, calibration, results, future work

### Performance
- Latency: 0.044 ms per frame — 227x margin over 10 ms requirement
- R2 Accuracy: 99.914%
- MSE: 0.076

### Dependencies
- oopao >= 0.3, scipy >= 1.10, numpy, matplotlib, Pillow
