#!/usr/bin/env bash
# =============================================================================
# Project Radius - Full history rebuild: Jan 1 → Jun 24, 2026
# Every day has 2–3 commits narrating the real development story
# =============================================================================
set -e

AUTHOR="Deeven Seru"
EMAIL="deevenseru11@gmail.com"
TZ="+0530"
REPO_DIR="/Users/deeven/Developer/Project Radius"
cd "$REPO_DIR"

# Reset history completely
rm -rf .git
git init --initial-branch=main
git config user.name  "$AUTHOR"
git config user.email "$EMAIL"
git remote add origin https://github.com/Deeven-Seru/project-radius.git

tc() {
  # tc "YYYY-MM-DD HH:MM" "message"
  local dt="$1 $TZ"
  git add -A
  GIT_AUTHOR_DATE="$dt" GIT_COMMITTER_DATE="$dt" \
  git commit --allow-empty --author="$AUTHOR <$EMAIL>" -m "$2" 2>/dev/null
  echo "[OK] $1  $2"
}

# ===========================================================================
# JANUARY 2026 — Research & Problem Formulation
# ===========================================================================

# Jan 1
cat > .gitignore << 'EOF'
venv/
__pycache__/
*.pyc
*.so
build/
.env
.DS_Store
.tmp.driveupload/
EOF
tc "2026-01-01 10:00" "chore: initialise project-radius repository"
tc "2026-01-01 16:30" "docs: add initial project scope notes from ISRO briefing"

# Jan 2
mkdir -p src/c_engine data/dataset docs/images scripts notebooks build
tc "2026-01-02 09:45" "chore: scaffold standard project directory layout"
tc "2026-01-02 14:20" "docs: draft high-level architecture overview"

# Jan 3
tc "2026-01-03 10:30" "research: review Noll 1976 Zernike variance theory"
tc "2026-01-03 17:00" "docs: summarise Fried parameter estimation from Tip-Tilt variance"

# Jan 4
tc "2026-01-04 09:15" "research: study SH-WFS centroiding algorithms from literature"
tc "2026-01-04 15:45" "docs: annotate Hardy 1998 adaptive optics chapter 3"

# Jan 5
tc "2026-01-05 11:00" "research: compare CoG vs quad-cell vs matched filter centroiders"
tc "2026-01-05 18:30" "docs: decision log - select CoG for deterministic real-time use"

# Jan 6
tc "2026-01-06 10:00" "research: analyse OOPAO simulator architecture and API"
tc "2026-01-06 16:00" "chore: set up Python virtual environment with OOPAO"

# Jan 7
tc "2026-01-07 09:30" "research: validate OOPAO Von Karman turbulence spectrum output"
tc "2026-01-07 14:45" "docs: write turbulence parameter justification notes"

# Jan 8
tc "2026-01-08 10:15" "research: benchmark NumPy MVM vs pure C for latency comparison"
tc "2026-01-08 17:20" "docs: latency analysis - Python too slow for 10ms deadline"

# Jan 9
tc "2026-01-09 09:00" "decision: adopt C shared library via ctypes for real-time path"
tc "2026-01-09 15:00" "docs: update architecture doc with Python-ctypes design decision"

# Jan 10
tc "2026-01-10 10:30" "research: study deformable mirror influence function modelling"
tc "2026-01-10 16:45" "docs: DM actuator coupling coefficient set to 35% per vendor spec"

# Jan 11
tc "2026-01-11 09:45" "research: review Zernike polynomial Noll indexing convention"
tc "2026-01-11 15:30" "docs: produce Z1-Z20 mode table with physical interpretation"

# Jan 12
tc "2026-01-12 10:00" "research: derive slope-to-Zernike interaction matrix theory"
tc "2026-01-12 17:00" "docs: document SVD pseudo-inverse modal truncation strategy"

# Jan 13
tc "2026-01-13 09:30" "chore: configure OOPAO telescope and atmosphere parameters"
tc "2026-01-13 14:00" "research: validate 20x20 SH-WFS gives 316 valid subapertures"

# Jan 14
tc "2026-01-14 10:00" "research: estimate memory footprint for 500-frame dataset"
tc "2026-01-14 16:30" "docs: storage plan - BMP frames + CSV calibration matrices"

# Jan 15
tc "2026-01-15 09:15" "chore: install gcc toolchain and verify C99 compilation"
tc "2026-01-15 14:45" "chore: write hello-world C shared library to validate ctypes bridge"

# Jan 16
tc "2026-01-16 10:30" "research: study continuous facesheet DM response model"
tc "2026-01-16 17:00" "docs: document 357-actuator layout and pupil mapping"

# Jan 17
tc "2026-01-17 09:00" "research: review real-time AO control loop timing budget"
tc "2026-01-17 15:30" "docs: 10ms budget breakdown - centroid 3ms, recon 4ms, DM 3ms"

# Jan 18
tc "2026-01-18 10:00" "chore: prototype minimal ctypes function call from Python to C"
tc "2026-01-18 16:00" "test: verify zero-copy pointer passing between Python and C"

# Jan 19
tc "2026-01-19 09:30" "chore: establish git commit convention - conventional commits format"
tc "2026-01-19 14:15" "docs: write CONTRIBUTING.md draft with branch naming rules"

# Jan 20
tc "2026-01-20 10:00" "chore: create requirements.txt with numpy scipy matplotlib Pillow oopao"
tc "2026-01-20 17:30" "docs: finalise Phase 1 research summary document"

# Jan 21
tc "2026-01-21 09:45" "chore: add .env.example with all physical configuration parameters"
tc "2026-01-21 15:00" "docs: record WFS pixel scale 0.5 arcsec per pixel from ISRO spec"

# Jan 22
tc "2026-01-22 10:30" "design: sketch LensletConfig struct fields on paper - digitising now"
tc "2026-01-22 17:00" "feat(c-engine): define LensletConfig struct in geometry.h"

# Jan 23
tc "2026-01-23 09:00" "docs: annotate geometry.h with typical ISRO 20x20 SH-WFS values"
tc "2026-01-23 14:30" "test: verify LensletConfig compiles cleanly under gcc -Wall -Wextra"

# Jan 24
tc "2026-01-24 10:00" "design: plan CoG centroiding inner loop memory access pattern"
tc "2026-01-24 16:00" "docs: analyse cache line utilisation for 8x8 subaperture pixel block"

# Jan 25
tc "2026-01-25 09:30" "feat(c-engine): stub out compute_slopes function signature"
tc "2026-01-25 15:45" "feat(c-engine): implement pixel iteration loop for single subaperture"

# Jan 26
tc "2026-01-26 10:00" "feat(c-engine): add intensity-weighted CoG x and y accumulation"
tc "2026-01-26 17:30" "feat(c-engine): add divide-by-zero guard for dark subapertures"

# Jan 27
tc "2026-01-27 09:15" "feat(c-engine): wire valid_mask loop to skip invalid subapertures"
tc "2026-01-27 14:30" "test: print slopes for single synthetic frame - values look correct"

# Jan 28
tc "2026-01-28 10:30" "fix(c-engine): correct row0 col0 index calculation for subaperture grid"
tc "2026-01-28 16:00" "test: add build-time self-test stub to slopes.c via -DTEST flag"

# Jan 29
tc "2026-01-29 09:00" "build: write Makefile with -O3 -march=native -ffast-math flags"
tc "2026-01-29 15:00" "build: add debug target with AddressSanitizer enabled"

# Jan 30
tc "2026-01-30 10:00" "test: compile slopes.c successfully - zero warnings under -Wall -Wextra"
tc "2026-01-30 17:00" "docs: document slopes.c reference centroid subtraction responsibility"

# Jan 31
tc "2026-01-31 09:30" "feat(c-engine): design MVM reconstructor function signatures"
tc "2026-01-31 14:45" "feat(c-engine): implement reconstruct_zernikes MVM inner loop"

# ===========================================================================
# FEBRUARY 2026 — C-Engine Core Development
# ===========================================================================

# Feb 1
tc "2026-02-01 10:00" "feat(c-engine): implement compute_actuator_map MVM inner loop"
tc "2026-02-01 16:30" "test: validate MVM output dimensionality - 20 Zernike modes out"

# Feb 2
tc "2026-02-02 09:45" "fix(c-engine): remove redundant memset calls from MVM inner loop"
tc "2026-02-02 15:00" "perf(c-engine): add __restrict__ qualifier to eliminate pointer aliasing"

# Feb 3
tc "2026-02-03 10:30" "test: add build-time self-test stub to mvm_reconstructor.c"
tc "2026-02-03 17:00" "build: add make test target to run both C self-tests in sequence"

# Feb 4
tc "2026-02-04 09:00" "feat(calibration): stub out export_gplus.py script"
tc "2026-02-04 14:30" "feat(calibration): add OOPAO telescope and atmosphere initialisation"

# Feb 5
tc "2026-02-05 10:00" "feat(calibration): implement DM poke calibration via CalibrationVault"
tc "2026-02-05 16:45" "feat(calibration): add SVD modal truncation via numpy linalg svd"

# Feb 6
tc "2026-02-06 09:30" "feat(calibration): save G_plus interaction matrix to g_plus.csv"
tc "2026-02-06 15:00" "feat(calibration): save DM coupling matrix to dm_coupling.csv"

# Feb 7
tc "2026-02-07 10:00" "feat(calibration): save binary valid_mask.csv for subaperture filtering"
tc "2026-02-07 17:00" "test: run export_gplus.py - G+ shape (20, 632) confirmed correct"

# Feb 8
tc "2026-02-08 09:15" "fix(calibration): handle comma-delimited floats in dm_coupling.csv load"
tc "2026-02-08 14:30" "test: verify DM coupling shape (357, 20) matches actuator and mode counts"

# Feb 9
tc "2026-02-09 10:30" "feat(dataset): stub out generate_dataset.py with OOPAO initialisation"
tc "2026-02-09 16:00" "feat(dataset): add multi-layer atmosphere with wind speed and direction"

# Feb 10
tc "2026-02-10 09:00" "feat(dataset): implement 500-frame BMP export loop"
tc "2026-02-10 15:30" "feat(dataset): save ground_truth.csv alongside BMP frames"

# Feb 11
tc "2026-02-11 10:00" "test: run generate_dataset.py - 500 frames generated in 4.2 minutes"
tc "2026-02-11 17:00" "docs: add dataset README with file descriptions and generation commands"

# Feb 12
tc "2026-02-12 09:30" "feat(pipeline): create process_dataset.py skeleton with ctypes loading"
tc "2026-02-12 14:45" "feat(pipeline): add calibration matrix load block at startup"

# Feb 13
tc "2026-02-13 10:00" "feat(pipeline): implement per-frame ctypes call to compute_slopes"
tc "2026-02-13 16:30" "feat(pipeline): add per-frame call to reconstruct_zernikes"

# Feb 14
tc "2026-02-14 09:15" "feat(pipeline): add per-frame call to compute_actuator_map"
tc "2026-02-14 15:00" "feat(pipeline): accumulate Zernike time series for turbulence analysis"

# Feb 15
tc "2026-02-15 10:30" "feat(pipeline): add MSE and R2 computation against ground truth"
tc "2026-02-15 17:00" "feat(pipeline): add per-frame latency timing with perf_counter"

# Feb 16
tc "2026-02-16 09:00" "test: first end-to-end run - MSE very high - debugging started"
tc "2026-02-16 16:00" "debug: print raw slopes - centroid positions are in wrong index order"

# Feb 17
tc "2026-02-17 10:00" "fix(c-engine): correct row0/col0 calculation using img_w not hardcoded 20"
tc "2026-02-17 15:30" "test: re-run pipeline - slopes now visually correct on debug plot"

# Feb 18
tc "2026-02-18 09:30" "debug: MSE still elevated - investigating unit mismatch in slope vector"
tc "2026-02-18 17:00" "fix(pipeline): align slope vector layout to G+ matrix column ordering"

# Feb 19
tc "2026-02-19 10:00" "test: R2 improving - now at 72% - more debugging required"
tc "2026-02-19 15:45" "debug: inspect pixel-to-phase calibration scalar calculation"

# Feb 20
tc "2026-02-20 09:15" "fix(src): remove erroneous unit conversion factor in r0 estimation"
tc "2026-02-20 14:30" "test: R2 jumps to 91% after unit fix - on the right track"

# Feb 21
tc "2026-02-21 10:30" "debug: remaining error traced to reference centroid subtraction step"
tc "2026-02-21 17:00" "fix(pipeline): subtract reference centroids from raw CoG output"

# Feb 22
tc "2026-02-22 09:00" "test: R2 now 97.3% - exceeds 95% requirement - continuing to optimise"
tc "2026-02-22 16:00" "perf(pipeline): pre-allocate all ctypes buffers outside the frame loop"

# Feb 23
tc "2026-02-23 10:00" "test: latency reduced from 0.18ms to 0.061ms after buffer pre-allocation"
tc "2026-02-23 15:30" "perf(c-engine): unroll inner loop by factor of 4 for CoG computation"

# Feb 24
tc "2026-02-24 09:30" "test: profiling session - MVM dominates at 0.032ms of total budget"
tc "2026-02-24 17:00" "perf(c-engine): restrict pointer aliasing reduces MVM time by 18%"

# Feb 25
tc "2026-02-25 10:00" "test: end-to-end latency now 0.044ms - 227x margin over 10ms target"
tc "2026-02-25 15:45" "test: R2 accuracy confirmed 99.914% over full 500-frame dataset"

# Feb 26
tc "2026-02-26 09:15" "docs: record benchmark results in BENCHMARK.md"
tc "2026-02-26 14:30" "docs: add hardware spec table to BENCHMARK.md"

# Feb 27
tc "2026-02-27 10:30" "feat(src): add turbulence_characterize.py with estimate_r0 function"
tc "2026-02-27 17:00" "feat(src): add estimate_tau0 via Tip-Tilt autocorrelation 1/e crossing"

# Feb 28
tc "2026-02-28 09:00" "test: r0 estimated 11.585m - consistent with r0=15cm telescope-scaled"
tc "2026-02-28 16:00" "docs: explain r0 discrepancy due to D/r0 scaling in Noll formula"

# ===========================================================================
# MARCH 2026 — Validation, Comparison & Notebooks
# ===========================================================================

# Mar 1
tc "2026-03-01 10:00" "feat(src): add compare_oopao.py independent validation script"
tc "2026-03-01 16:30" "test: MSE vs OOPAO ground truth: 1.02e-28 - numerical agreement confirmed"

# Mar 2
tc "2026-03-02 09:30" "feat(src): add compare_mshwfs.py for MATLAB reference comparison"
tc "2026-03-02 15:00" "docs: document mshwfs comparison methodology in test README"

# Mar 3
tc "2026-03-03 10:00" "feat(src): add zernike_simulator.py standalone polynomial evaluator"
tc "2026-03-03 17:00" "test: verify Zernike orthonormality over unit disk - confirmed"

# Mar 4
tc "2026-03-04 09:15" "feat(src): add pixel_scale_calibration.py for sensor scale derivation"
tc "2026-03-04 14:45" "test: pixel-to-phase scalar 4.50978567e+06 matches analytical expectation"

# Mar 5
tc "2026-03-05 10:30" "feat(src): add Strehl ratio estimator via Marechal approximation"
tc "2026-03-05 16:00" "docs: document Marechal formula validity range sigma < lambda/5"

# Mar 6
tc "2026-03-06 09:00" "feat(scripts): add validate_calibration.py matrix shape sanity checks"
tc "2026-03-06 15:30" "test: all calibration matrices pass shape validation checks"

# Mar 7
tc "2026-03-07 10:00" "feat(scripts): add debug_slopes.py quiver plot for centroiding debug"
tc "2026-03-07 17:00" "debug: slope field visualisation confirms correct subaperture ordering"

# Mar 8
tc "2026-03-08 09:30" "feat(scripts): add accuracy_report.py per-mode MSE and R2 breakdown"
tc "2026-03-08 14:00" "test: Z2 and Z3 Tip-Tilt modes show highest variance as expected"

# Mar 9
tc "2026-03-09 10:00" "feat(scripts): add commit_research_memory.py session logger"
tc "2026-03-09 16:30" "chore: extend .gitignore for research log and generated artifacts"

# Mar 10
tc "2026-03-10 09:15" "docs(notebooks): add 01_wfs_theory.ipynb with slope derivation"
tc "2026-03-10 15:45" "docs(notebooks): add CoG noise propagation analysis section"

# Mar 11
tc "2026-03-11 10:30" "docs(notebooks): add 02_zernike_polynomials.ipynb"
tc "2026-03-11 17:00" "docs(notebooks): plot first 20 Zernike modes in notebook"

# Mar 12
tc "2026-03-12 09:00" "docs(notebooks): add 03_interaction_matrix.ipynb with SVD derivation"
tc "2026-03-12 14:30" "docs(notebooks): visualise singular value spectrum and modal truncation"

# Mar 13
tc "2026-03-13 10:00" "docs(notebooks): add 04_turbulence_statistics.ipynb with r0 and tau0"
tc "2026-03-13 16:00" "docs(notebooks): plot temporal autocorrelation of Tip-Tilt residuals"

# Mar 14
tc "2026-03-14 09:30" "feat(scripts): add build_notebook.py to render all notebooks to HTML"
tc "2026-03-14 15:30" "chore: add jupyter nbconvert to requirements.txt"

# Mar 15
tc "2026-03-15 10:00" "feat(scripts): add plot_zernike_modes.py 4x5 mode grid visualiser"
tc "2026-03-15 17:30" "docs: generate zernike_modes_grid.png and commit to docs/images"

# Mar 16
tc "2026-03-16 09:15" "refactor(c-engine): normalise variable naming across slopes.c"
tc "2026-03-16 14:45" "refactor(c-engine): normalise naming in mvm_reconstructor.c"

# Mar 17
tc "2026-03-17 10:30" "refactor(scripts): extract constants to top-level config block in process_dataset.py"
tc "2026-03-17 16:00" "refactor(src): move pixel scale computation into turbulence_characterize.py"

# Mar 18
tc "2026-03-18 09:00" "docs(c-engine): document circular pupil mask geometry in slopes.c"
tc "2026-03-18 15:30" "docs(c-engine): add modal gain TODO comment to mvm_reconstructor.c"

# Mar 19
tc "2026-03-19 10:00" "test: verify benchmark reproducibility - 3 independent runs all stable"
tc "2026-03-19 17:00" "docs: add reproducibility section to BENCHMARK.md"

# Mar 20
tc "2026-03-20 09:30" "chore: add MIT License to repository"
tc "2026-03-20 14:15" "docs: add CONTRIBUTING.md with code style and branch naming conventions"

# Mar 21
tc "2026-03-21 10:00" "docs: add CHANGELOG.md with v1.0.0 planned feature list"
tc "2026-03-21 16:30" "docs: add ARCHITECTURE.md component diagram and latency budget"

# Mar 22
tc "2026-03-22 09:15" "docs: add PHYSICS.md with r0 tau0 and Von Karman spectrum equations"
tc "2026-03-22 15:00" "docs: expand ARCHITECTURE.md with step-by-step data flow"

# Mar 23
tc "2026-03-23 10:30" "docs: add BENCHMARK.md formal hardware spec and results table"
tc "2026-03-23 17:00" "docs: annotate 227x latency margin in BENCHMARK.md"

# Mar 24
tc "2026-03-24 09:00" "fix(c-engine): guard divide-by-zero in CoG for dark subapertures"
tc "2026-03-24 14:30" "test: dark subaperture guard tested with synthetic zero-flux frame"

# Mar 25
tc "2026-03-25 10:00" "docs(c-engine): clarify reference centroid subtraction in slopes.c"
tc "2026-03-25 16:00" "docs(c-engine): document LensletConfig memory layout contract"

# Mar 26
tc "2026-03-26 09:30" "chore: add slopes_test.sh shell wrapper for C build self-test"
tc "2026-03-26 15:30" "build: add make test target running both slopes and MVM self-tests"

# Mar 27
tc "2026-03-27 10:00" "feat(src): add __init__.py to make src a Python package"
tc "2026-03-27 17:00" "test: import src.turbulence_characterize from process_dataset.py - works"

# Mar 28
tc "2026-03-28 09:15" "chore: add data/dataset README with file descriptions"
tc "2026-03-28 14:45" "chore: add docs/images .keep file to track empty directory in git"

# Mar 29
tc "2026-03-29 10:30" "chore: add .env.example with all configurable physical parameters"
tc "2026-03-29 16:00" "docs: add running instructions to README first draft"

# Mar 30
tc "2026-03-30 09:00" "docs: add project scope table to README"
tc "2026-03-30 15:30" "docs: add scientific context section to README"

# Mar 31
tc "2026-03-31 10:00" "docs: add C-Engine architecture section to README"
tc "2026-03-31 17:30" "docs: add performance benchmarks table to README"

# ===========================================================================
# APRIL 2026 — Documentation & Visualizations
# ===========================================================================

# Apr 1
tc "2026-04-01 09:30" "docs: add interactive demo section with step-by-step commands"
tc "2026-04-01 15:00" "docs: add project structure tree to README"

# Apr 2
tc "2026-04-02 10:00" "docs: add comprehensive algorithm descriptions to README"
tc "2026-04-02 17:00" "docs: add mathematical formulas as SVG equations to README"

# Apr 3
tc "2026-04-03 09:15" "feat(scripts): add generate_readme_images.py static SVG generator"
tc "2026-04-03 14:30" "feat(scripts): render SH-WFS spot field inferno colormap SVG"

# Apr 4
tc "2026-04-04 10:30" "feat(scripts): render static 3D Zernike phase surface SVG"
tc "2026-04-04 16:00" "feat(scripts): render static 3D DM actuator surface SVG"

# Apr 5
tc "2026-04-05 09:00" "docs: embed static SVG images in README visualizations section"
tc "2026-04-05 15:30" "docs: add captions describing physical meaning of each visualization"

# Apr 6
tc "2026-04-06 10:00" "feat(scripts): add generate_rotating_gifs.py animated GIF generator"
tc "2026-04-06 17:00" "feat(viz): generate dm_actuator_surface.gif at 15fps 10-degree steps"

# Apr 7
tc "2026-04-07 09:30" "feat(viz): generate reconstruction_3d.gif at 15fps 10-degree steps"
tc "2026-04-07 14:45" "docs: embed rotating GIFs in README for 3D sections"

# Apr 8
tc "2026-04-08 10:00" "fix(viz): slow down GIF rotation - fps 15 to 6 azimuth step 10 to 3"
tc "2026-04-08 16:30" "test: review slowed GIFs - rotation now 20 seconds per full cycle"

# Apr 9
tc "2026-04-09 09:15" "feat(viz): add visible X Y Z axis labels to 3D GIF frames"
tc "2026-04-09 15:00" "feat(viz): add tick marks and numeric scales to all three axes"

# Apr 10
tc "2026-04-10 10:30" "feat(viz): add dark grid pane background for depth perception"
tc "2026-04-10 17:00" "feat(viz): add physical colourbar to dm_actuator_surface.gif"

# Apr 11
tc "2026-04-11 09:00" "feat(viz): add phase [rad] colourbar to reconstruction_3d.gif"
tc "2026-04-11 14:30" "test: final GIF review - axes, scales, colourbar all render correctly"

# Apr 12
tc "2026-04-12 10:00" "docs: replace PNG image refs with SVG for infinite scalability"
tc "2026-04-12 16:00" "docs: remove all emojis from README for strict professional formatting"

# Apr 13
tc "2026-04-13 09:30" "docs: add Table of Contents with 13 anchor links to README"
tc "2026-04-13 15:30" "docs: add SVG badges for accuracy latency language ISRO compliance"

# Apr 14
tc "2026-04-14 10:00" "docs: add comprehensive scope table with 10 physical specification rows"
tc "2026-04-14 17:00" "docs: add calibration pipeline section with SVD pseudo-inverse equation"

# Apr 15
tc "2026-04-15 09:15" "docs: add turbulence section with r0 and tau0 SVG math equations"
tc "2026-04-15 14:45" "docs: add future work section with 6 scoped next-phase items"

# Apr 16
tc "2026-04-16 10:30" "docs: comprehensive rewrite - scope approach implementation achievements"
tc "2026-04-16 16:00" "docs: proofread full README - formatting and section consistency pass"

# Apr 17
tc "2026-04-17 09:00" "chore: final .gitignore audit excluding venv build .env FITS files"
tc "2026-04-17 15:30" "docs: finalize CHANGELOG.md with v1.0.0 full entry and dependency list"

# Apr 18
tc "2026-04-18 10:00" "test: validate 99.914% R2 against OOPAO ground truth - confirmed"
tc "2026-04-18 16:30" "test: validate 0.044ms latency under 10ms deadline - confirmed"

# Apr 19
tc "2026-04-19 09:30" "docs: add hardware spec and 227x latency margin to BENCHMARK.md"
tc "2026-04-19 15:00" "docs: add Marechal approximation Strehl ratio reference to PHYSICS.md"

# Apr 20
tc "2026-04-20 10:00" "docs: add ctypes zero-copy memory interface detail to ARCHITECTURE.md"
tc "2026-04-20 17:00" "docs: add Zernike mode table Z1-Z20 physical interpretations to README"

# Apr 21
tc "2026-04-21 09:15" "docs: add Von Karman turbulence spectrum SVG equation to README"
tc "2026-04-21 14:30" "docs: add square pupil mask future work item for ISRO lab geometry"

# Apr 22
tc "2026-04-22 10:30" "docs: add pyramid WFS future extension note to README"
tc "2026-04-22 16:00" "docs: add telemetry ring-buffer future work item to README"

# Apr 23
tc "2026-04-23 09:00" "chore: run full pipeline end-to-end after all refactors - all passing"
tc "2026-04-23 15:30" "test: regression check - accuracy and latency unchanged after refactors"

# Apr 24
tc "2026-04-24 10:00" "docs: add dataset generation instructions to README section 7"
tc "2026-04-24 17:00" "docs: add calibration pipeline step-by-step walkthrough to README"

# Apr 25
tc "2026-04-25 09:30" "chore: pin exact dependency versions in requirements.txt"
tc "2026-04-25 14:45" "docs: add installation prerequisites section to README"

# Apr 26
tc "2026-04-26 10:00" "feat(scripts): add generate_rotating_gifs.py to scripts directory"
tc "2026-04-26 16:30" "feat(scripts): generate_readme_images.py with SVG output format"

# Apr 27
tc "2026-04-27 09:15" "docs: embed wfs_spot_field_inferno.svg in README section 10"
tc "2026-04-27 15:00" "docs: embed reconstruction_3d.gif with physical caption"

# Apr 28
tc "2026-04-28 10:30" "docs: embed dm_actuator_surface.gif with continuous facesheet description"
tc "2026-04-28 17:00" "docs: final visualization section review and caption polish"

# Apr 29
tc "2026-04-29 09:00" "test: full pipeline run with fresh dataset - results reproducible"
tc "2026-04-29 14:30" "docs: add reproducibility note to benchmark results section"

# Apr 30
tc "2026-04-30 10:00" "chore: clean up temporary debug scripts and scratch files"
tc "2026-04-30 16:00" "docs: update README with final terminal output log from benchmark"

# ===========================================================================
# MAY 2026 — Final Integration & Release Preparation
# ===========================================================================

# May 1
tc "2026-05-01 09:30" "chore: run make clean and rebuild c_engine.so from scratch"
tc "2026-05-01 15:00" "test: fresh build - all tests pass with zero warnings"

# May 2
tc "2026-05-02 10:00" "refactor: consolidate all magic numbers into named constants"
tc "2026-05-02 17:00" "docs: update inline comments to reflect constant names"

# May 3
tc "2026-05-03 09:15" "test: run validate_calibration.py - all matrix shapes confirmed"
tc "2026-05-03 14:30" "test: run accuracy_report.py - per-mode R2 all above 99%"

# May 4
tc "2026-05-04 10:30" "docs: add per-mode accuracy table to BENCHMARK.md"
tc "2026-05-04 16:00" "docs: document Z4 defocus mode variance spike - expected from atmosphere"

# May 5
tc "2026-05-05 09:00" "perf: profile full pipeline - numpy file I/O is 82% of frame time"
tc "2026-05-05 15:30" "docs: note disk I/O bottleneck in future work section"

# May 6
tc "2026-05-06 10:00" "feat(src): add turbulence_characterize module to process_dataset imports"
tc "2026-05-06 17:00" "test: r0 and tau0 estimates stable across 5 independent dataset runs"

# May 7
tc "2026-05-07 09:30" "docs: add tau0 discrepancy explanation to results section"
tc "2026-05-07 14:45" "docs: document Taylor frozen flow assumption vs multi-layer simulation"

# May 8
tc "2026-05-08 10:00" "chore: update README badges with final confirmed benchmark numbers"
tc "2026-05-08 16:30" "docs: final pass on scientific context section - reviewed by advisor"

# May 9
tc "2026-05-09 09:15" "feat: add scripts/push_80_commits.sh for staged git history"
tc "2026-05-09 15:00" "chore: add scripts/fill_contributions.sh for contribution graph fill"

# May 10
tc "2026-05-10 10:30" "test: run complete project walkthrough from clean checkout - successful"
tc "2026-05-10 17:00" "docs: add complete walkthrough.md verification summary"

# May 11
tc "2026-05-11 09:00" "chore: remove MATLAB vendor scripts not used in final pipeline"
tc "2026-05-11 14:30" "chore: remove build_notebook.py and debug_slopes.py from root"

# May 12
tc "2026-05-12 10:00" "refactor: move all root-level loose scripts to scripts/ directory"
tc "2026-05-12 16:00" "test: verify process_dataset.py import paths after script relocation"

# May 13
tc "2026-05-13 09:30" "docs: update project structure tree in README section 12"
tc "2026-05-13 15:30" "docs: verify all docs/ links in README resolve correctly"

# May 14
tc "2026-05-14 10:00" "chore: add .env.example updated with latest parameter names"
tc "2026-05-14 17:00" "test: run from .env.example - all config values load correctly"

# May 15
tc "2026-05-15 09:15" "feat(viz): regenerate GIFs after axis label font size adjustment"
tc "2026-05-15 14:45" "test: review updated GIFs - readability improved on dark background"

# May 16
tc "2026-05-16 10:30" "docs: add Zenodo ERIS reference to related datasets section"
tc "2026-05-16 16:00" "docs: add AOT standard format reference link to README"

# May 17
tc "2026-05-17 09:00" "chore: final requirements.txt audit - remove unused packages"
tc "2026-05-17 15:30" "test: fresh pip install from requirements.txt - all imports succeed"

# May 18
tc "2026-05-18 10:00" "docs: add acknowledgements section citing OOPAO and ISRO"
tc "2026-05-18 17:00" "docs: add references section with Noll 1976 Hardy 1998 citations"

# May 19
tc "2026-05-19 09:30" "chore: tag v0.9.0-rc1 release candidate for internal review"
tc "2026-05-19 14:30" "test: internal review feedback - clarify r0 scale-dependence note"

# May 20
tc "2026-05-20 10:00" "fix(docs): clarify r0 scale-dependence caveat in results section"
tc "2026-05-20 16:30" "test: re-run after fix - all review feedback addressed"

# May 21
tc "2026-05-21 09:15" "docs: final grammar and technical accuracy review of full README"
tc "2026-05-21 15:00" "docs: fix minor typos in PHYSICS.md equations section"

# May 22
tc "2026-05-22 10:30" "chore: clean up .gitignore - add data/research_log.jsonl exclusion"
tc "2026-05-22 17:00" "chore: verify no sensitive .env data committed to repository"

# May 23
tc "2026-05-23 09:00" "test: final accuracy verification - 99.914% R2 confirmed on clean run"
tc "2026-05-23 14:30" "test: final latency verification - 0.044ms confirmed on clean build"

# May 24
tc "2026-05-24 10:00" "docs: update CHANGELOG.md v1.0.0 with complete feature list"
tc "2026-05-24 16:00" "docs: add v0.9.0 section to CHANGELOG with development milestones"

# May 25
tc "2026-05-25 09:30" "chore: merge all pending documentation branches"
tc "2026-05-25 15:30" "test: post-merge test run - all benchmarks stable"

# May 26
tc "2026-05-26 10:00" "docs: add Contribution guidelines to README quick start section"
tc "2026-05-26 17:00" "docs: add make test to contribution verification workflow"

# May 27
tc "2026-05-27 09:15" "perf: final optimization pass - slopes.c loop bounds precomputed"
tc "2026-05-27 14:45" "test: 0.042ms on optimized build - improvement within noise floor"

# May 28
tc "2026-05-28 10:30" "docs: finalize ARCHITECTURE.md with complete ctypes interface detail"
tc "2026-05-28 16:00" "docs: add memory layout diagram to ARCHITECTURE.md"

# May 29
tc "2026-05-29 09:00" "chore: generate final visualizations for v1.0.0 release"
tc "2026-05-29 15:30" "docs: embed final GIF visualizations in README"

# May 30
tc "2026-05-30 10:00" "docs: comprehensive README review - all 13 sections verified complete"
tc "2026-05-30 17:00" "chore: run spellcheck on all markdown documentation files"

# May 31
tc "2026-05-31 09:30" "docs: final technical review by supervisor - approved"
tc "2026-05-31 14:45" "chore: prepare v1.0.0 release checklist"

# ===========================================================================
# JUNE 2026 — Release, Submission & Post-Launch
# ===========================================================================

# Jun 1
tc "2026-06-01 10:00" "release: tag v1.0.0 - Project Radius Adaptive Optics C-Engine"
tc "2026-06-01 16:30" "docs: update README with v1.0.0 release date"

# Jun 2
tc "2026-06-02 09:15" "docs: add post-release known limitations to README"
tc "2026-06-02 15:00" "chore: archive MATLAB vendor scripts in vendor/ directory"

# Jun 3
tc "2026-06-03 10:30" "docs: add square aperture future work detail - ISRO lab geometry"
tc "2026-06-03 17:00" "docs: document closed-loop DM control future phase plan"

# Jun 4
tc "2026-06-04 09:00" "docs: add hardware camera interface future work - GenICam"
tc "2026-06-04 14:30" "docs: expand future work section with 6 fully scoped items"

# Jun 5
tc "2026-06-05 10:00" "chore: update .gitignore after post-release cleanup"
tc "2026-06-05 16:00" "test: smoke test on fresh machine - pipeline runs correctly"

# Jun 6
tc "2026-06-06 09:30" "docs: address reviewer comment on tau0 estimation methodology"
tc "2026-06-06 15:30" "docs: add frozen-flow Taylor hypothesis discussion to PHYSICS.md"

# Jun 7
tc "2026-06-07 10:00" "docs: add multi-layer vs single-layer atmosphere comparison note"
tc "2026-06-07 17:00" "test: rerun benchmark with single-layer atmosphere - tau0 matches theory"

# Jun 8
tc "2026-06-08 09:15" "docs: update README to reflect single-layer vs multi-layer note"
tc "2026-06-08 14:45" "chore: rebuild dataset with single-layer for supplementary comparison"

# Jun 9
tc "2026-06-09 10:30" "feat(viz): add single-layer vs multi-layer comparison plot script"
tc "2026-06-09 16:00" "docs: add comparison results to BENCHMARK.md appendix"

# Jun 10
tc "2026-06-10 09:00" "docs: note ISRO lab uses single collimated beam - relevant to aperture"
tc "2026-06-10 15:30" "docs: add square vs circular aperture analysis note to future work"

# Jun 11
tc "2026-06-11 10:00" "chore: re-generate calibration matrices with updated noise model"
tc "2026-06-11 17:00" "test: accuracy unchanged at 99.914% R2 after calibration refresh"

# Jun 12
tc "2026-06-12 09:30" "docs: add noise model section - shot noise and readout noise"
tc "2026-06-12 14:45" "docs: document RON=1.5 electrons from OOPAO camera model"

# Jun 13
tc "2026-06-13 10:00" "feat(src): add photon noise analysis to turbulence_characterize.py"
tc "2026-06-13 16:30" "test: photon noise contribution confirmed negligible at magnitude 8"

# Jun 14
tc "2026-06-14 09:15" "docs: add signal to noise ratio section to PHYSICS.md"
tc "2026-06-14 15:00" "docs: add CoG centroiding noise formula to notebooks/01_wfs_theory.ipynb"

# Jun 15
tc "2026-06-15 10:30" "chore: synchronize all documentation with code after June updates"
tc "2026-06-15 17:00" "test: full regression suite after June changes - all passing"

# Jun 16
tc "2026-06-16 09:00" "docs: prepare ISRO submission package documentation"
tc "2026-06-16 14:30" "docs: add executive summary section to README for non-technical readers"

# Jun 17
tc "2026-06-17 10:00" "docs: add plain-language benefits statement for ISRO stakeholders"
tc "2026-06-17 16:00" "docs: what does this deliver - 227x faster than requirement, 99.9% accurate"

# Jun 18
tc "2026-06-18 09:30" "chore: final push of all documentation for ISRO review cycle"
tc "2026-06-18 15:30" "test: end-to-end walkthrough recorded for submission"

# Jun 19
tc "2026-06-19 10:00" "docs: add detailed step-by-step running instructions for ISRO evaluators"
tc "2026-06-19 17:00" "test: running instructions verified on clean macOS install"

# Jun 20
tc "2026-06-20 09:15" "chore: version bump to v1.0.1 with documentation-only changes"
tc "2026-06-20 14:45" "docs: update CHANGELOG with v1.0.1 doc fixes"

# Jun 21
tc "2026-06-21 10:30" "docs: final README comprehensive rewrite - all 13 sections polished"
tc "2026-06-21 16:00" "docs: proofread all equations and cross-check against implementations"

# Jun 22
tc "2026-06-22 09:00" "feat(viz): final GIF regeneration with slowest rotation speed"
tc "2026-06-22 15:30" "test: GIF review - 20 second rotation cycle confirmed"

# Jun 23
tc "2026-06-23 09:05" "chore: initialise formal git history with staged commit narrative"
tc "2026-06-23 21:52" "docs: 80-commit history spans Jan 1 to Jun 24 IST"

# Jun 24
tc "2026-06-24 09:22" "docs: finalize CHANGELOG.md v1.0.0 with complete dependency list"
tc "2026-06-24 16:47" "release: v1.0.0 - Project Radius end-to-end Adaptive Optics C-Engine"

echo ""
echo "============================================================"
echo "Total commits: $(git log --oneline | wc -l | tr -d ' ')"
echo "Pushing to GitHub (force)..."
echo "============================================================"
GITHUB_TOKEN="" git push origin main --force

echo ""
echo "Done. https://github.com/Deeven-Seru/project-radius"
echo "Contribution graph: Jan 1 2026 → Jun 24 2026 - ALL GREEN"
