---
theme: default
css: ./styles.css
highlighter: shiki
lineNumbers: true
transition: slide-left
title: Project Radius Notebook
---

# Project Radius

<div class="mt-4 text-xl text-gray-600">
  Adaptive Optics C-Engine Workspace
</div>

<div class="grid grid-cols-3 gap-6 mt-16">
  <div class="io-card">
    <div class="flex items-center">
      <svg class="io-icon text-blue-500 mr-2" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
      <div class="font-bold">README.md</div>
    </div>
    <div class="text-xs text-gray-500 mt-2">Project Spec & Equations</div>
  </div>
  <div class="io-card">
    <div class="flex items-center">
      <svg class="io-icon text-green-500 mr-2" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
      <div class="font-bold">slopes.c</div>
    </div>
    <div class="text-xs text-gray-500 mt-2">Centroiding Algorithms</div>
  </div>
  <div class="io-card">
    <div class="flex items-center">
      <svg class="io-icon text-purple-500 mr-2" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zm0 2c3.87 0 8 1.11 8 2s-4.13 2-8 2-8-1.11-8-2 4.13-2 8-2zm0 14c-3.87 0-8-1.11-8-2v-2.18c1.72.62 4.6 1.18 8 1.18s6.28-.56 8-1.18V16c0 .89-4.13 2-8 2zm0-5c-3.87 0-8-1.11-8-2v-2.18c1.72.62 4.6 1.18 8 1.18s6.28-.56 8-1.18V11c0 .89-4.13 2-8 2z"/></svg>
      <div class="font-bold">telescope_data.csv</div>
    </div>
    <div class="text-xs text-gray-500 mt-2">WFS Calibration Telemetry</div>
  </div>
</div>

<div class="mt-12 text-xs text-gray-400 text-center">
  Press → to enter the notebook workspace
</div>

---
---

# Sources & Study Focus

<div class="io-workspace">
  <div class="io-sidebar">
    <div class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Sources (3)</div>
    <ul class="space-y-3">
      <li class="p-2 bg-white rounded border border-gray-300 flex items-center text-xs">
        <svg class="io-icon text-blue-500 mr-2" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
        Atmospheric Physics.pdf
      </li>
      <li class="p-2 bg-white rounded border border-gray-300 flex items-center text-xs opacity-50">
        <svg class="io-icon text-green-500 mr-2" viewBox="0 0 24 24"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>
        FSOC_scintillation.md
      </li>
      <li class="p-2 bg-white rounded border border-gray-300 flex items-center text-xs opacity-50">
        <svg class="io-icon text-purple-500 mr-2" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zm0 2c3.87 0 8 1.11 8 2s-4.13 2-8 2-8-1.11-8-2 4.13-2 8-2zm0 14c-3.87 0-8-1.11-8-2v-2.18c1.72.62 4.6 1.18 8 1.18s6.28-.56 8-1.18V16c0 .89-4.13 2-8 2zm0-5c-3.87 0-8-1.11-8-2v-2.18c1.72.62 4.6 1.18 8 1.18s6.28-.56 8-1.18V11c0 .89-4.13 2-8 2z"/></svg>
        telemetry_glitches.csv
      </li>
    </ul>
  </div>
  <div>
    <h2>The Core Challenge: Turbulence</h2>
    <div class="io-card mt-4">
      <div class="text-sm font-semibold text-gray-500">Refractive index variations distort the optical wavefront:</div>
      <ul class="space-y-4 mt-4 text-sm text-gray-700">
        <li v-click><strong>1. Satellite Links (FSOC):</strong> Causes spatial phase distortion, reducing single-mode fiber-coupling efficiency and dropping laser link throughput.</li>
        <li v-click><strong>2. Directed Energy:</strong> Spreads focus away from targets, dissolving energy over horizontal paths.</li>
        <li v-click><strong>3. Imaging Systems:</strong> Blurs satellite tracking features across camera pixels.</li>
      </ul>
    </div>
  </div>
</div>

---
---

# The Loop Deadline

<div class="io-workspace">
  <div class="io-sidebar">
    <div class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Focus Note</div>
    <div class="p-3 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
      The loop execution frequency must run significantly faster than the turbulence evolution timescale.
    </div>
  </div>
  <div>
    <h2>Loop Timing & Coherence Time ($\tau_0$)</h2>
    <div class="grid grid-cols-2 gap-4 mt-6">
      <div class="io-card border-l-4 border-l-amber-500">
        <div class="io-badge io-badge-yellow mb-2">Loop Budget</div>
        <div class="io-giant-stat text-yellow-600">&lt; 10ms</div>
        <p class="text-xs text-gray-500 mt-2">
          Strict real-time correction constraint before the atmospheric phase pattern changes.
        </p>
      </div>
      <div class="io-card">
        <div class="text-blue-500 font-bold mb-1">Traditional RTC Issues</div>
        <p class="text-xs text-gray-600">
          Heavy GPU pipelines suffer from PCIe transfer delays, resulting in latency jitter and lag errors that exceed the coherence limit.
        </p>
      </div>
    </div>
  </div>
</div>

---
---

# Project Radius Pipeline

NotebookLM workspace highlights three distinct pipeline steps:

<div class="grid grid-cols-3 gap-4 mt-8">
  <div class="io-card">
    <div class="flex items-center text-blue-500 font-bold mb-2">
      <svg class="io-icon mr-2" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 3.79 2 6v12c0 2.21 4.48 4 10 4s10-1.79 10-4V6c0-2.21-4.48-4-10-4zm0 2c3.87 0 8 1.11 8 2s-4.13 2-8 2-8-1.11-8-2 4.13-2 8-2zm0 14c-3.87 0-8-1.11-8-2v-2.18c1.72.62 4.6 1.18 8 1.18s6.28-.56 8-1.18V16c0 .89-4.13 2-8 2zm0-5c-3.87 0-8-1.11-8-2v-2.18c1.72.62 4.6 1.18 8 1.18s6.28-.56 8-1.18V11c0 .89-4.13 2-8 2z"/></svg>
      1. INGEST
    </div>
    <div class="text-xs text-gray-500">
      Telemetry bmp frames are loaded directly in memory using a zero-copy pointer cast in the C-Engine.
    </div>
  </div>
  <div class="io-card" v-click>
    <div class="flex items-center text-green-600 font-bold mb-2">
      <svg class="io-icon mr-2" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10H7v-2h10v2z"/></svg>
      2. RECONSTRUCT
    </div>
    <div class="text-xs text-gray-500">
      Processes subaperture centroids and maps slopes to 55 Zernike modes in under 0.08 ms.
    </div>
  </div>
  <div class="io-card" v-click>
    <div class="flex items-center text-yellow-600 font-bold mb-2">
      <svg class="io-icon mr-2" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>
      3. CORRECT
    </div>
    <div class="text-xs text-gray-500">
      Applies single-mode predictive filters and exports command voltages to the 357 DM actuators.
    </div>
  </div>
</div>

---
---

# System Architecture

<div class="io-workspace">
  <div class="io-sidebar">
    <div class="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Architecture</div>
    <div class="p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-800">
      Zero-copy ctypes bridge allows C-Engine to directly manipulate python detector memory handles.
    </div>
  </div>
  <div class="io-card">
    <h2>Data Pipeline Flow</h2>
    <div class="mt-4">
      ```mermaid
      graph TD
          A[Raw WFS Camera DMA Buffer] -->|zero-copy pointer| B[slopes.c: Centroiding]
          B -->|Slope Vector S: 632| C[mvm_reconstructor.c: G_MVR]
          C -->|Zernike Modes Z: 55| D[Kalman prediction Z-DKF]
          D -->|Actuators A: 357| E[Deformable Mirror Stroke]
      ```
    </div>
  </div>
</div>

---
layout: two-cols
---

# Centroiding (slopes.c)

Subaperture gradients are computed from camera pixel blocks.

::left::

### Centroid Selectors
- **Standard CoG:** Arithmetic center of intensity.
- **Thresholded CoG:** Rejects background read noise.
- **Iterative Weighted CoG:** High accuracy iterative Gaussian fit.

$$\Delta x_k = \frac{f_{\text{lens}}}{\lambda} \cdot \frac{\partial \phi}{\partial x}\bigg|_{k}$$

::right::

<div class="io-card border-l-4 border-l-green-500">
  <div class="io-badge io-badge-green mb-2">Auto-Tuning Engine</div>
  <p class="text-xs text-gray-600">
    During system startup, the pipeline profiles the local hardware capacity. If the precision IWCoG executes in under 5ms, it is selected; otherwise, the C-Engine dynamically switches to the vectorized TCoG to secure the real-time loop deadline.
  </p>
</div>

---
---

# SIMD Vectorization & ISA Tuning

Processor registers are optimized dynamically at the instruction set level.

<div class="grid grid-cols-2 gap-6 mt-8">
  <div class="io-card">
    <div class="flex items-center text-blue-500 font-bold mb-2">
      <svg class="io-icon mr-2" viewBox="0 0 24 24"><path d="M9 2H7v2H5c-1.1 0-2 .9-2 2v2H1v2h2v2H1v2h2v2c0 1.1.9 2 2 2h2v2h2v-2h2v2h2v-2h2v2h2v-2h2c1.1 0 2-.9 2-2v-2h2v-2h-2v-2h2v-2h-2V6c0-1.1-.9-2-2-2h-2V2h-2v2H9V2zm8 14H7V7h10v9z"/></svg>
      ARM NEON (AArch64)
    </div>
    <p class="text-xs text-gray-600">
      Processes 4 parallel single-precision floats inside 128-bit vector registers:
    </p>
    <pre class="text-xs text-blue-600 bg-gray-50 border p-2 rounded mt-2">vld1q_f32 / vmlaq_f32</pre>
  </div>
  <div class="io-card">
    <div class="flex items-center text-yellow-600 font-bold mb-2">
      <svg class="io-icon mr-2" viewBox="0 0 24 24"><path d="M9 2H7v2H5c-1.1 0-2 .9-2 2v2H1v2h2v2H1v2h2v2c0 1.1.9 2 2 2h2v2h2v-2h2v2h2v-2h2v2h2v-2h2c1.1 0 2-.9 2-2v-2h2v-2h-2v-2h2v-2h-2V6c0-1.1-.9-2-2-2h-2V2h-2v2H9V2zm8 14H7V7h10v9z"/></svg>
      Intel AVX2 & FMA (x86_64)
    </div>
    <p class="text-xs text-gray-600">
      Processes 8 parallel floats inside 256-bit registers with Fused Multiply-Accumulate:
    </p>
    <pre class="text-xs text-blue-600 bg-gray-50 border p-2 rounded mt-2">_mm256_fmadd_ps</pre>
  </div>
</div>

<div class="mt-8 text-xs text-center text-yellow-800 bg-yellow-50 border border-yellow-200 p-2 rounded">
  Uses <code>__attribute__((target("avx2,fma")))</code> with runtime dispatch (<code>__builtin_cpu_supports</code>).
</div>

---
layout: two-cols
---

# Reconstructor Math

Least-squares reconstructors amplify noise in high-order aberrations.

::left::

### Bayesian Minimum Variance Reconstructor (MVR)
Maintains high spatial correction accuracy under scintillation by regularizing modes using atmospheric Kolmogorov Zernike covariance statistics.

$$G_{\text{MVR}} = C_\phi M^T (M C_\phi M^T + C_N)^{-1}$$

::right::

<div class="io-card border-l-4 border-l-blue-500">
  <div class="io-badge io-badge-blue mb-2">Woodbury Identity</div>
  <p class="text-xs text-gray-600 mt-2">
    Bypasses massive matrix inversions in the loop step, reducing the operations to standard matrix-vector multiplications:
  </p>
  <div class="text-sm font-semibold mt-2 text-blue-600">
    $$G_{\text{MVR}} = (\alpha C_\phi^{-1} + M^T M)^{-1} M^T$$
  </div>
</div>

---
---

# Zernike Decoupled Kalman Filter

Servo-lag is mitigated by predicting atmospheric phase shifts ahead of correction.

<div class="grid grid-cols-2 gap-6 mt-8">
  <div class="io-card">
    <div class="text-green-600 font-bold mb-2">O(N) Complexity Reduction</div>
    <p class="text-xs text-gray-600">
      Instead of running a large multi-variable matrix Kalman filter, Project Radius models **55 independent, scalar filters** (one per Zernike mode) as first-order autoregressive AR(1) processes.
    </p>
  </div>
  <div class="io-card">
    <div class="text-blue-500 font-bold mb-2">Filter State Equations</div>
    <p class="text-xs text-gray-600">
      Updates the estimated aberration coefficients dynamically each frame:
    </p>
    <div class="text-xs text-blue-600 font-mono mt-2 bg-gray-50 p-2 border rounded">
      z_j(t+1 | t) = a_j * z_j(t | t)
    </div>
  </div>
</div>

---
---

# Error Mitigation & Sanitization

The C-Engine guards against physical optical glitches.

<div class="grid grid-cols-2 gap-6 mt-8">
  <div class="io-card border-l-4 border-l-yellow-600">
    <div class="io-badge io-badge-yellow mb-2">Integration Window Shifting</div>
    <p class="text-xs text-gray-600 mt-2">
      Compensates for mechanical shifts of the MLA relative to the camera by dynamically adjusting subaperture bounds and residual fractional pixel offsets:
    </p>
    <pre class="text-xs text-gray-700 bg-gray-50 border p-2 rounded mt-2">col0_shifted = clamp(col0 + Ox, 0, max_px)</pre>
  </div>
  <div class="io-card border-l-4 border-l-red-500">
    <div class="io-badge io-badge-red mb-2">Input Sanitization</div>
    <p class="text-xs text-gray-600 mt-2">
      Isolates corruptions on the fly:
    </p>
    <ul class="text-xs text-gray-600 list-disc pl-4 mt-2">
      <li>Replaces NaN and Infinity pixels with background thresholds.</li>
      <li>Clamps mirror stroke commands to [-2.0, 2.0] V to prevent physical DM damage.</li>
    </ul>
  </div>
</div>

---
---

# Soak Test Benchmarks

A 5,000-frame stress test with Gaussian noise and glitch injection.

<div class="grid grid-cols-3 gap-6 mt-12 text-center">
  <div class="io-card border-t-4 border-t-green-600">
    <div class="io-giant-stat text-green-600">0.08 ms</div>
    <div class="text-xs text-gray-500 mt-2">Average Pipeline Latency</div>
  </div>
  <div class="io-card border-t-4 border-t-blue-500">
    <div class="io-giant-stat text-blue-500">100.0%</div>
    <div class="text-xs text-gray-500 mt-2">Operational Stability</div>
  </div>
  <div class="io-card border-t-4 border-t-yellow-500">
    <div class="io-giant-stat text-yellow-600">0.00 MB</div>
    <div class="text-xs text-gray-500 mt-2">Memory Leak Growth</div>
  </div>
</div>

---
---

# Radius vs. Competitors

Project Radius matches proprietary real-time control (RTC) systems.

<table class="w-full text-left mt-8 text-xs border-collapse border border-gray-300">
  <thead>
    <tr class="bg-gray-100 text-blue-600">
      <th class="p-3 border border-gray-300">Feature</th>
      <th class="p-3 border border-gray-300">Microgate</th>
      <th class="p-3 border border-gray-300">ALPAO Core RTC</th>
      <th class="p-3 border border-gray-300">Project Radius</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="p-3 border border-gray-300 font-bold">Open-Source</td>
      <td class="p-3 border border-gray-300"><svg class="io-icon text-red-500" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg></td>
      <td class="p-3 border border-gray-300"><svg class="io-icon text-red-500" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg></td>
      <td class="p-3 border border-gray-300 text-green-700 font-bold"><svg class="io-icon text-green-600 mr-1" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg> Yes (C99 API)</td>
    </tr>
    <tr>
      <td class="p-3 border border-gray-300 font-bold">Hardware Bind</td>
      <td class="p-3 border border-gray-300">Bound to Microgate</td>
      <td class="p-3 border border-gray-300">Bound to ALPAO</td>
      <td class="p-3 border border-gray-300 text-green-700 font-bold"><svg class="io-icon text-green-600 mr-1" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg> Agnostic (GenICam)</td>
    </tr>
    <tr>
      <td class="p-3 border border-gray-300 font-bold">Power Draw</td>
      <td class="p-3 border border-gray-300">High (&gt; 500W rack)</td>
      <td class="p-3 border border-gray-300">Medium (Workstation)</td>
      <td class="p-3 border border-gray-300 text-green-700 font-bold"><svg class="io-icon text-green-600 mr-1" viewBox="0 0 24 24"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg> Low (&lt; 10W Embedded)</td>
    </tr>
  </tbody>
</table>

---
---

# Real-World Use Cases

Study focus areas of Project Radius:

<div class="grid grid-cols-3 gap-6 mt-8">
  <div class="io-card">
    <div class="io-badge io-badge-blue mb-2">Laser Comms</div>
    <div class="font-bold text-sm">FSOC Ground-to-LEO</div>
    <p class="text-xs text-gray-500 mt-2">
      Eliminates packet drop on satellite links under severe turbulence.
    </p>
  </div>
  <div class="io-card">
    <div class="io-badge io-badge-green mb-2">Defense</div>
    <div class="font-bold text-sm">Directed Energy</div>
    <p class="text-xs text-gray-500 mt-2">
      Locks target beam focus over long horizontal atmospheric paths.
    </p>
  </div>
  <div class="io-card">
    <div class="io-badge io-badge-yellow mb-2">Medicine</div>
    <div class="font-bold text-sm">Retinal Imaging</div>
    <p class="text-xs text-gray-500 mt-2">
      Bypasses ocular aberrations to capture in-vivo capillaries at cellular resolution.
    </p>
  </div>
</div>

---
layout: center
class: text-center
---

# Project Radius Workspace

Join us in building high-performance adaptive optics.

<div class="mt-8 flex justify-center items-center">
  <div class="p-4 bg-white border rounded shadow flex items-center">
    <svg class="io-icon text-gray-800 mr-2" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0012 2z"/></svg>
    <span class="font-bold text-gray-800">github.com/Deeven-Seru/project-radius</span>
  </div>
</div>
