---
theme: default
css: ./styles.css
highlighter: shiki
lineNumbers: true
transition: slide-left
title: Radius - High-Performance AO C-Engine
---

# Radius

<div class="mt-8 text-2xl text-blue-400 font-semibold">
  High-Performance Adaptive Optics C-Engine
</div>
<div class="text-gray-400">
  Designed by Deeven Seru
</div>

<div class="mt-16 flex gap-4">
  <span class="io-badge io-badge-green">Latency: 0.08ms</span>
  <span class="io-badge io-badge-blue">Accuracy: 99.49%</span>
  <span class="io-badge io-badge-yellow">C99 Optimized</span>
</div>

---
layout: two-cols
---

# The Atmospheric Barrier

Atmospheric turbulence degrades optical performance, limiting satellites and laser links.

::left::

### The Impact
<ul class="space-y-3 mt-4">
  <li v-click><strong>Imaging Systems:</strong> Blurs stellar points and resolves satellites poorly.</li>
  <li v-click><strong>Laser Communications:</strong> Causes scintillation, beam wander, and high packet drop.</li>
  <li v-click><strong>Directed Energy:</strong> Dissipates beam focus over target paths.</li>
</ul>

::right::

<div class="io-card h-60 flex flex-col justify-center items-center">
  <div class="text-io-text-muted text-sm mb-4">Turbulence Refractive Index Gradients</div>
  <div class="grid grid-cols-5 gap-2 w-4/5">
    <div v-for="n in 25" :key="n" class="h-6 w-6 rounded border border-gray-700 bg-opacity-20" :class="n % 3 === 0 ? 'bg-red-500' : n % 2 === 0 ? 'bg-blue-500' : 'bg-transparent'"></div>
  </div>
</div>

---
---

# The Real-Time Threshold

Atmospheric coherence time ($\tau_0$) scales down to **2 - 10 ms**.

<div class="grid grid-cols-2 gap-8 mt-12">
  <div>
    <div class="io-giant-stat text-yellow-400">&lt; 10ms</div>
    <div class="text-xl font-bold">Absolute Loop Deadline</div>
    <p class="text-gray-400 mt-2">
      To achieve optical correction, wavefront sensing and mirror correction must execute under 10 ms.
    </p>
  </div>
  <div class="io-card">
    <h3 class="text-blue-400">The Latency Bottleneck</h3>
    <p class="text-gray-300 mt-2">
      Traditional GPU-based architectures suffer from PCIe data transfer bottlenecks and kernel launch overheads, failing to meet consistent microsecond-level latency constraints.
    </p>
  </div>
</div>

---
---

# What is Project Radius?

Project Radius is a standalone, deterministic, ultra-low-latency Adaptive Optics real-time control pipeline.

<div class="grid grid-cols-3 gap-4 mt-8">
  <div class="io-card" v-click>
    <div class="text-blue-400 font-bold mb-2">1. INGEST</div>
    <p class="text-gray-400 text-sm">
      Loads raw detector images from Shack-Hartmann sensors directly into C-Engine pointers using a zero-copy bridge.
    </p>
  </div>
  <div class="io-card" v-click>
    <div class="text-green-400 font-bold mb-2">2. RECONSTRUCT</div>
    <p class="text-gray-400 text-sm">
      Processes subaperture centroids and reconstructs the phase profile as Zernike polynomial coefficients in 0.08 ms.
    </p>
  </div>
  <div class="io-card" v-click>
    <div class="text-yellow-400 font-bold mb-2">3. CORRECT</div>
    <p class="text-gray-400 text-sm">
      Applies predict-ahead filters and maps Zernike modes to Deformable Mirror (DM) actuator stroke values.
    </p>
  </div>
</div>

---
---

# Zero-Copy Pipeline Architecture

Memory optimization is achieved by bypassing expensive Python ctypes copies.

```mermaid
graph TD
    A[WFS Telemetry Frame] -->|DMA Address pointer| B[Python HAL Bridge]
    B -->|ctypes float pointer| C[slopes.c: Centroiding]
    C -->|Slope Vector S: 632| D[mvm_reconstructor.c: Z = G_MVR · S]
    D -->|Zernike Modes Z: 55| E[Kalman prediction Z-DKF]
    E -->|Actuator Vector A: 357| F[Deformable Mirror Drive]
```

---
layout: two-cols
---

# Vectorized Centroiding (slopes.c)

Gradients are calculated by tracking focal spots relative to nominal subaperture references.

::left::

### Centroid Algorithm Selection
- **Standard CoG:** Fast but noise-sensitive.
- **Thresholded CoG (TCoG):** Isolates noise floor.
- **Iterative Weighted CoG (IWCoG):** Maximizes optical precision.

$$\Delta x_k = \frac{f_{\text{lens}}}{\lambda} \cdot \frac{\partial \phi}{\partial x}\bigg|_{k}$$

::right::

<div class="io-card">
  <h3 class="text-green-400">Dynamic Autotuning</h3>
  <p class="text-gray-300 text-sm mt-2">
    An autotuning script runs during initialization to benchmark IWCoG. If latency is under 5ms, IWCoG is loaded; otherwise, the vectorized TCoG is promoted dynamically to guarantee loop safety.
  </p>
</div>

---
---

# SIMD Vectorization & ISA Tuning

Centroiding, Matrix Multipliers (MVM), and Kalman prediction are optimized at assembly register levels.

<div class="grid grid-cols-2 gap-4 mt-8">
  <div class="io-card">
    <h3 class="text-blue-400">ARM NEON Vectorization</h3>
    <p class="text-gray-400 text-sm mt-2">
      Leverages 128-bit NEON registers to process 4 floats concurrently:
    </p>
    <pre class="text-xs text-green-300 bg-black p-2 rounded mt-2">vld1q_f32 / vaddq_f32 / vmlaq_f32</pre>
  </div>
  <div class="io-card">
    <h3 class="text-green-400">Intel AVX2 & FMA</h3>
    <p class="text-gray-400 text-sm mt-2">
      Leverages 256-bit AVX2 registers to process 8 floats concurrently:
    </p>
    <pre class="text-xs text-green-300 bg-black p-2 rounded mt-2">_mm256_loadu_ps / _mm256_fmadd_ps</pre>
  </div>
</div>

<div class="mt-4 text-sm text-center text-yellow-400">
  Dynamic compiler dispatch utilizes target attributes to run optimally across architectures.
</div>

---
layout: two-cols
---

# Minimum Variance Reconstructor

Standard Least-Squares ($G^+$) amplifies high-order measurement noise.

::left::

### Reconstructor Algorithms
- **G⁺ Pseudo-Inverse:** Maps basic slopes but ignores turbulence covariance statistics.
- **MVR Formulation:** Uses Bayesian Zernike covariance ($C_\phi$) and noise statistics ($C_N$) to regularize high-order modes.

::right::

### Woodbury Simplification
Maps MVM matrices efficiently without large matrix inversions.

$$G_{\text{MVR}} = (\alpha C_\phi^{-1} + M^T M)^{-1} M^T$$

---
---

# Zernike Decoupled Kalman Filter (Z-DKF)

Servo-lag occurs when target wind velocities cause turbulence parameters to drift between exposure.

<div class="grid grid-cols-2 gap-8 mt-12">
  <div class="io-card">
    <h3 class="text-blue-400">O(N) Scalar Predictors</h3>
    <p class="text-gray-300 text-sm mt-2">
      Rather than updating a massive covariance matrix at $O(N^3)$ complexity, Project Radius deploys **55 independent, scalar Kalman filters** (one per Zernike mode) modeled as AR(1) state equations.
    </p>
  </div>
  <div class="io-card">
    <h3 class="text-green-400">Predictive Phase Step</h3>
    <p class="text-gray-300 text-sm mt-2">
      The C-Engine projects state values one-step ahead:
    </p>
    <pre class="text-xs text-green-300 bg-black p-2 rounded mt-2">z_j(t+1 | t) = a_j * z_j(t | t)</pre>
  </div>
</div>

---
---

# Real-World Error Mitigation

Real hardware systems must be resilient to spot truncation and signal noise.

<div class="grid grid-cols-2 gap-4 mt-8">
  <div class="io-card">
    <h3 class="text-yellow-400">Dynamic Window Shifting</h3>
    <p class="text-gray-400 text-sm mt-2">
      Corrects for mechanical camera misalignment by shifting subaperture integration bounds and adjusting subpixel fractional residuals:
    </p>
    <pre class="text-xs text-green-300 bg-black p-2 rounded mt-2">col0_shifted = clamp(col0 + Ox, 0, I_size - W_sub)</pre>
  </div>
  <div class="io-card">
    <h3 class="text-red-400">Input Sanitization</h3>
    <p class="text-gray-400 text-sm mt-2">
      Protects optical hardware from dynamic glitches:
    </p>
    <ul class="text-xs text-gray-300 list-disc pl-4 mt-2">
      <li>Replaces NaNs/Infs dynamically in C loops.</li>
      <li>Clamps mirror voltage commands to [-2.0, 2.0] V.</li>
    </ul>
  </div>
</div>

---
---

# Soak Test & Latency Benchmarks

A 5,000-frame soak test with NaNs, Infs, and readout noise confirms total operational stability.

<div class="grid grid-cols-3 gap-4 mt-12 text-center">
  <div class="io-card">
    <div class="io-giant-stat text-green-400">0.08 ms</div>
    <div class="text-sm text-gray-400">Average Loop Latency</div>
  </div>
  <div class="io-card">
    <div class="io-giant-stat text-blue-400">100%</div>
    <div class="text-sm text-gray-400">Soak Test Stability</div>
  </div>
  <div class="io-card">
    <div class="io-giant-stat text-yellow-400">0.00 MB</div>
    <div class="text-sm text-gray-400">Leak-Free Memory Growth</div>
  </div>
</div>

---
---

# Radius vs. Competitors

Project Radius matches proprietary real-time control (RTC) systems at zero license costs.

<table class="w-full text-left mt-8 text-sm border-collapse border border-gray-800">
  <thead>
    <tr class="bg-gray-900 text-blue-400">
      <th class="p-3 border border-gray-800">Feature</th>
      <th class="p-3 border border-gray-800">Microgate</th>
      <th class="p-3 border border-gray-800">ALPAO Core RTC</th>
      <th class="p-3 border border-gray-800">Project Radius</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="p-3 border border-gray-800 font-bold">Open-Source</td>
      <td class="p-3 border border-gray-800 text-red-400">No</td>
      <td class="p-3 border border-gray-800 text-red-400">No</td>
      <td class="p-3 border border-gray-800 text-green-400 font-bold">Yes (C99 API)</td>
    </tr>
    <tr>
      <td class="p-3 border border-gray-800 font-bold">Hardware Bind</td>
      <td class="p-3 border border-gray-800">Microgate HW only</td>
      <td class="p-3 border border-gray-800">ALPAO DMs only</td>
      <td class="p-3 border border-gray-800 text-green-400 font-bold">Agnostic (GenICam)</td>
    </tr>
    <tr>
      <td class="p-3 border border-gray-800 font-bold">Filters</td>
      <td class="p-3 border border-gray-800">Matrix</td>
      <td class="p-3 border border-gray-800">PI / PID</td>
      <td class="p-3 border border-gray-800 text-green-400 font-bold">MVR + Kalman Predictor</td>
    </tr>
  </tbody>
</table>

---
---

# Production Applications

Project Radius is designed for commercial and defense-grade optical systems.

<div class="grid grid-cols-3 gap-4 mt-8">
  <div class="io-card">
    <div class="text-blue-400 font-bold mb-2">FSOC Links</div>
    <p class="text-xs text-gray-400">
      Aligns ground-to-LEO satellite laser links under high wind shear, eliminating packet drop.
    </p>
  </div>
  <div class="io-card">
    <div class="text-green-400 font-bold mb-2">Directed Energy</div>
    <p class="text-xs text-gray-400">
      Maintains target focus for high-power laser beams through long horizontal paths.
    </p>
  </div>
  <div class="io-card">
    <div class="text-yellow-400 font-bold mb-2">Retinal Imaging</div>
    <p class="text-xs text-gray-400">
      Corrects for aberrations in the human eye to capture capillaries at cellular resolution.
    </p>
  </div>
</div>

---
layout: center
class: text-center
---

# Project Radius is Open Source

Join us in building low-latency adaptive optics pipelines.

<div class="mt-8">
  <span class="io-badge io-badge-blue p-4 text-xl">github.com/Deeven-Seru/project-radius</span>
</div>
