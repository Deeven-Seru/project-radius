import pytest
import numpy as np
from tests.nasa_grade.utils import generate_spot_field, generate_valid_mask

def test_benchmark_centroiding_enhanced(benchmark, c_engine):
    """
    Benchmarks the enhanced centroiding algorithm.
    Target: Execution < 2ms for a 40x40 lenslet array.
    """
    n_sub = 1600 # 40x40
    sub_px = 10
    n_valid = n_sub
    
    img_data = generate_spot_field(n_sub=n_sub, sub_px=sub_px, photon_count=5000, noise_std=1.0)
    valid_mask = generate_valid_mask(n_sub, geometry="square")
    slopes = np.zeros(n_valid * 2, dtype=np.float32)
    
    def run_centroiding():
        c_engine.compute_slopes_enhanced(img_data, slopes, valid_mask, n_sub, n_valid, sub_px, 10.0, 0.0, 0.0)

    benchmark.pedantic(run_centroiding, iterations=100, rounds=100)

def test_benchmark_mvm_reconstruction(benchmark, c_engine):
    """
    Benchmarks the Matrix-Vector Multiplication for Zernike reconstruction.
    Target: Execution < 1ms for typical matrix sizes.
    """
    n_slopes = 1600 * 2
    n_zernike = 150
    
    slopes = np.random.uniform(-1.0, 1.0, n_slopes).astype(np.float32)
    G_plus = np.random.uniform(-1.0, 1.0, (n_zernike, n_slopes)).astype(np.float32)
    zernikes = np.zeros(n_zernike, dtype=np.float32)
    
    G_plus_flat = G_plus.flatten()
    
    def run_reconstruction():
        c_engine.reconstruct_zernikes(slopes, G_plus_flat, zernikes, n_zernike, n_slopes)

    benchmark.pedantic(run_reconstruction, iterations=100, rounds=100)

def test_benchmark_actuator_mapping(benchmark, c_engine):
    """
    Benchmarks the Actuator Map generation.
    Target: Execution < 0.5ms.
    """
    n_zernike = 150
    n_actuators = 256
    
    zernikes = np.random.uniform(-1.0, 1.0, n_zernike).astype(np.float32)
    C_DM = np.random.uniform(-1.0, 1.0, (n_actuators, n_zernike)).astype(np.float32)
    actuators = np.zeros(n_actuators, dtype=np.float32)
    
    C_DM_flat = C_DM.flatten()
    
    def run_mapping():
        c_engine.compute_actuator_map(zernikes, C_DM_flat, actuators, n_actuators, n_zernike)
        
    benchmark.pedantic(run_mapping, iterations=100, rounds=100)
