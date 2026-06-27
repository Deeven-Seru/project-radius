**Capture Runbook**

- Purpose: Acquire many synchronized pixel frames paired with gradient frames so we can train a robust mapping (avoid overfitting).

- Strategy (preferred): Run the instrument in data-collection mode and use a small trigger/collector service to snapshot every pixel frame when a gradient frame is reported. Save timestamped pairs to `/build/captured_pairs.npz` and raw images to `/build/captured_*.npy`.

- Quick simulation (no hardware): use `scripts/capture_synchronized.py --mode simulate --n_pairs 1000 --augment` to generate 1000 synthetic captured pairs from the ERIS FITS file.

- Live capture requirements:
  - A trigger source that announces gradient frames. This can be a tiny process that publishes lines like `GRADIENT <idx> <timestamp>` over ZeroMQ PUB on an address (e.g. `tcp://controller:5555`).
  - A camera capture command or script that can be invoked from shell and saves a numpy array to a provided path. Example script: `capture_camera.sh <out_path>` that writes the raw frame to `<out_path>`.

- Example live workflow (instrument team):
  1. Start trigger publisher on controller that sends `GRADIENT` messages for each gradient frame.
  2. On the capture host, run:

```bash
./venv/bin/python scripts/capture_synchronized.py --mode live --zmq_addr tcp://controller:5555 --camera_cmd "./capture_camera.sh {out_path}" --max_pairs 2000 --timeout 600
```

  3. Confirm `/build/captured_pairs.npz` contains `pixel_paths`, `gradient_idx`, and `timestamps`.

- Post-capture processing:
  - Convert raw numpy frames to whatever canonical format required, run `scripts/aotpy_validation.py` to compute metrics, and feed the new dataset into `scripts/train_lowrank_ridge.py` or `scripts/fit_subap_affine_reg.py` for training.

- Notes for NASA deployment:
  - Ensure the capture host has a deterministic camera SDK and the capture command returns immediately after write.
  - Prefer hardware timestamping if available; otherwise record timestamps at the earliest point possible.
  - Save raw frames and checksum them to ensure integrity.

Contact: For help adapting the `--camera_cmd` or trigger integration, tell me the camera SDK or how the gradient frames are announced and I will adapt the script.
