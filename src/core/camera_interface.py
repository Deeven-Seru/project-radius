import time
import threading
import queue
import numpy as np

# Base Class
class CameraInterface:
    def start_acquisition(self):
        raise NotImplementedError
    def stop_acquisition(self):
        raise NotImplementedError
    def get_next_frame(self):
        raise NotImplementedError

# 1. Simulated Live Camera interface
class SimulatedCameraInterface(CameraInterface):
    def __init__(self, resolution=400, diameter=8.0, n_subap=20, fps=1000.0, r0=0.15, L0=25.0, n_zernike=55):
        self.resolution = resolution
        self.diameter = diameter
        self.n_subap = n_subap
        self.fps = fps
        self.r0 = r0
        self.L0 = L0
        self.n_zernike = n_zernike
        
        self.frame_queue = queue.Queue(maxsize=10)
        self.running = False
        self.thread = None
        
        # We import OOPAO lazily inside init to keep the class loadable in non-OOPAO environments
        from OOPAO.Telescope import Telescope
        from OOPAO.Source import Source
        from OOPAO.ShackHartmann import ShackHartmann
        from OOPAO.Atmosphere import Atmosphere
        from OOPAO.Zernike import Zernike
        
        # Initialize OOPAO objects
        self.tel = Telescope(resolution=self.resolution, diameter=self.diameter)
        self.src = Source('K', magnitude=8)
        self.src * self.tel
        self.atm = Atmosphere(self.tel, r0=self.r0, L0=self.L0, fractionalR0=[1.0, 0.5], windSpeed=[10, 5], windDirection=[0, 45], altitude=[0, 1000], src=self.src)
        self.atm.initializeAtmosphere(self.tel)
        self.tel + self.atm
        self.wfs = ShackHartmann(nSubap=self.n_subap, telescope=self.tel, lightRatio=0.5)
        
        # Reset source to clear Tip/Tilt WFS calibration mask
        self.src.reset()
        self.src * self.tel
        
        # Initialize Zernike basis
        self.zernike_basis = Zernike(self.tel, J=self.n_zernike)
        self.zernike_basis.computeZernike(self.tel, remove_piston=0)
        self.z_norm = np.sum(self.zernike_basis.modes**2, axis=0)

    def _acquisition_loop(self):
        frame_interval = 1.0 / self.fps
        next_time = time.perf_counter()
        
        while self.running:
            # Evolve atmosphere and propagate to WFS
            self.atm.update()
            self.src * self.tel * self.wfs
            
            # Format detector frame
            frame = (self.wfs.cam.frame / self.wfs.cam.frame.max() * 255).astype(np.uint8)
            
            # Compute true Zernike coefficients of the atmosphere phase in meters
            true_phase = self.src.OPD[self.tel.pupil > 0]
            true_z = np.sum(true_phase[:, None] * self.zernike_basis.modes, axis=0) / self.z_norm
            
            # Push to queue (drop oldest frame if queue is full)
            try:
                if self.frame_queue.full():
                    self.frame_queue.get_nowait()
                self.frame_queue.put_nowait((frame, true_z))
            except queue.Full:
                pass
            
            # Sleep to maintain frame rate
            next_time += frame_interval
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = time.perf_counter()

    def start_acquisition(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._acquisition_loop, daemon=True)
            self.thread.start()

    def stop_acquisition(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def get_next_frame(self, timeout=1.0):
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None, None

# 2. Production GenICam Frame Grabber / Camera Interface
class GenICamCameraInterface(CameraInterface):
    def __init__(self, cti_path):
        self.cti_path = cti_path
        self.harvester = None
        self.ia = None
        
        try:
            from harvesters.core import Harvester
            self.Harvester = Harvester
        except ImportError:
            raise ImportError("Please install 'harvesters' to use the GenICam Hardware Camera interface: pip install harvesters")

    def start_acquisition(self):
        self.harvester = self.Harvester()
        self.harvester.add_file(self.cti_path)
        self.harvester.update()
        
        if len(self.harvester.device_info_list) == 0:
            raise RuntimeError("GenICam: No camera or frame grabber devices detected.")
            
        print(f"GenICam: Connecting to {self.harvester.device_info_list[0].model}...")
        self.ia = self.harvester.create_image_acquirer(0)
        self.ia.start_acquisition()
        print("GenICam: Image acquisition started successfully.")

    def stop_acquisition(self):
        if self.ia:
            self.ia.stop_acquisition()
            self.ia.destroy()
            self.ia = None
        if self.harvester:
            self.harvester.reset()
            self.harvester = None
        print("GenICam: Image acquisition stopped.")

    def get_next_frame(self, timeout=1.0):
        if not self.ia:
            return None, None
        try:
            buffer = self.ia.fetch_buffer(timeout=timeout)
            component = buffer.payload.components[0]
            # Expose raw ctypes data pointer (component.data) directly to enable zero-copy C-Engine integration
            return component.data, buffer
        except Exception as e:
            print(f"GenICam: Failed to acquire buffer: {e}")
            return None, None

    def queue_buffer(self, buffer):
        if buffer:
            buffer.queue()

# 3. Playback Camera Interface (for real-data live testing)
class PlaybackCameraInterface(CameraInterface):
    def __init__(self, data_dir, fps=1000.0):
        self.data_dir = data_dir
        self.fps = fps
        
        self.frame_queue = queue.Queue(maxsize=50)
        self.running = False
        self.thread = None
        
        # Load all BMP frames and ground truth in advance to avoid disk I/O bottlenecks
        from PIL import Image
        import os
        
        print("PlaybackCamera: Pre-loading dataset frames into memory...")
        self.frames = []
        bmp_files = sorted([f for f in os.listdir(self.data_dir) if f.endswith('.bmp')])
        for fname in bmp_files:
            img = np.array(Image.open(os.path.join(self.data_dir, fname))).astype(np.uint8)
            self.frames.append(img)
            
        gt_path = os.path.join(self.data_dir, 'ground_truth.csv')
        if os.path.exists(gt_path):
            self.ground_truth = np.loadtxt(gt_path, delimiter=',').astype(np.float32)
        else:
            self.ground_truth = None
            
        self.num_frames = len(self.frames)
        print(f"PlaybackCamera: Loaded {self.num_frames} frames and ground truth coefficients.")

    def _acquisition_loop(self):
        frame_interval = 1.0 / self.fps
        next_time = time.perf_counter()
        idx = 0
        
        while self.running:
            frame = self.frames[idx]
            true_z = self.ground_truth[idx] if self.ground_truth is not None else np.zeros(20)
            
            # Push to queue (drop oldest frame if queue is full)
            try:
                if self.frame_queue.full():
                    self.frame_queue.get_nowait()
                self.frame_queue.put_nowait((frame, true_z))
            except queue.Full:
                pass
            
            idx = (idx + 1) % self.num_frames
            
            # Sleep to maintain frame rate
            next_time += frame_interval
            sleep_time = next_time - time.perf_counter()
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                next_time = time.perf_counter()

    def start_acquisition(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._acquisition_loop, daemon=True)
            self.thread.start()

    def stop_acquisition(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def get_next_frame(self, timeout=1.0):
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None, None
