"""
test_genicam_interface.py
-------------------------
Unit tests for the GenICamCameraInterface.
Since harvesters requires the genicam C-extension (which lacks wheels for Python 3.14 on macOS),
we mock the harvesters modules to validate our interface logic without importing the real library.
"""
import sys
import os
from unittest.mock import MagicMock

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# Create and register mocks for harvesters modules in sys.modules
mock_harvesters_core = MagicMock()
mock_harvester_class = MagicMock()
mock_harvesters_core.Harvester = mock_harvester_class
sys.modules['harvesters'] = MagicMock()
sys.modules['harvesters.core'] = mock_harvesters_core

import unittest

# Now we can import the interface without it failing on ImportError
from src.core.camera_interface import GenICamCameraInterface

class TestGenICamInterface(unittest.TestCase):
    def test_acquisition_flow(self):
        # 1. Setup mocks for Harvester class behavior
        mock_harvester = MagicMock()
        mock_harvester_class.return_value = mock_harvester
        
        mock_device_info = MagicMock()
        mock_device_info.model = "Mock Camera Model"
        mock_harvester.device_info_list = [mock_device_info]
        
        mock_ia = MagicMock()
        mock_harvester.create_image_acquirer.return_value = mock_ia
        
        # Mock buffer acquisition
        mock_buffer = MagicMock()
        mock_component = MagicMock()
        mock_component.data = 12345678 # simulated raw data address
        mock_buffer.payload.components = [mock_component]
        mock_ia.fetch_buffer.return_value = mock_buffer
        
        # 2. Instantiate and run interface
        interface = GenICamCameraInterface(cti_path="/dummy/path/producer.cti")
        
        # Verify startup
        interface.start_acquisition()
        mock_harvester.add_file.assert_called_with("/dummy/path/producer.cti")
        mock_harvester.update.assert_called_once()
        mock_harvester.create_image_acquirer.assert_called_with(0)
        mock_ia.start_acquisition.assert_called_once()
        
        # Verify frame retrieval
        data_ptr, retrieved_buf = interface.get_next_frame(timeout=1.0)
        mock_ia.fetch_buffer.assert_called_with(timeout=1.0)
        self.assertEqual(data_ptr, 12345678)
        self.assertEqual(retrieved_buf, mock_buffer)
        
        # Verify queueing back
        interface.queue_buffer(mock_buffer)
        mock_buffer.queue.assert_called_once()
        
        # Verify stop
        interface.stop_acquisition()
        mock_ia.stop_acquisition.assert_called_once()
        mock_ia.destroy.assert_called_once()
        mock_harvester.reset.assert_called_once()
        print("\nGenICam wrapper interface test: PASSED (All harvesters calls validated successfully)")

if __name__ == '__main__':
    unittest.main()
