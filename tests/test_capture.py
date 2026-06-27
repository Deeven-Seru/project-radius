import os
import tempfile
import numpy as np
from pathlib import Path

import subprocess


def test_simulate_capture_creates_pairs():
    repo_root = Path(__file__).resolve().parents[1]
    venv_python = os.environ.get('VENV_PYTHON', 'python')
    out = subprocess.run([venv_python, str(repo_root / 'scripts' / 'capture_synchronized.py'), '--mode', 'simulate', '--n_pairs', '5'], capture_output=True, text=True)
    assert out.returncode == 0
    assert (repo_root / 'build' / 'captured_pairs.npz').exists()
    data = np.load(repo_root / 'build' / 'captured_pairs.npz', allow_pickle=True)
    assert 'pixel_paths' in data
    assert len(data['pixel_paths']) == 5
