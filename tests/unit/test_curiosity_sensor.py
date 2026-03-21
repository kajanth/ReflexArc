import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import json
import tempfile
import shutil
from unittest.mock import patch

from sensors.curiosity import CuriositySensor

class TestCuriositySensor(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for memory
        self.test_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.test_dir, "stats.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_init_creates_file_and_cache(self):
        with patch('sensors.curiosity.CuriositySensor.__init__', return_value=None):
            sensor = CuriositySensor(cost_limit=1.0, latency_threshold=5.0)
            sensor.cost_limit = 1.0
            sensor.latency_threshold = 5.0
            sensor.stats_file = self.stats_file
            sensor._cache = None
            sensor._last_mtime = 0
            sensor._init_stats()

        self.assertTrue(os.path.exists(self.stats_file))
        self.assertEqual(sensor._cache, {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0})
        self.assertEqual(sensor.get_internal_state(), "STABLE")

    def test_log_event_updates_cache_and_file(self):
        with patch('sensors.curiosity.CuriositySensor.__init__', return_value=None):
            sensor = CuriositySensor(cost_limit=1.0, latency_threshold=5.0)
            sensor.cost_limit = 1.0
            sensor.latency_threshold = 5.0
            sensor.stats_file = self.stats_file
            sensor._cache = None
            sensor._last_mtime = 0
            sensor._init_stats()

        sensor.log_event(2.0, 1.0)

        # Check cache
        self.assertEqual(sensor._cache["total_spent"], 2.0)
        self.assertEqual(sensor._cache["calls"], 1)
        self.assertEqual(sensor._cache["avg_latency"], 1.0)
        self.assertEqual(sensor.get_internal_state(), "FINANCIAL_PAIN")

        # Check file
        with open(self.stats_file, 'r') as f:
            stats = json.load(f)
            self.assertEqual(stats["total_spent"], 2.0)

    def test_get_internal_state_does_not_read_file(self):
        sensor = CuriositySensor(cost_limit=1.0, latency_threshold=5.0)
        sensor.stats_file = self.stats_file
        sensor._init_stats()

        with patch('builtins.open') as mock_open:
            state = sensor.get_internal_state()
            self.assertEqual(state, "STABLE")
            mock_open.assert_not_called()

if __name__ == '__main__':
    unittest.main()
