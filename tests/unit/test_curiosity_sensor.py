import pytest
import os
import json
from sensors.curiosity import CuriositySensor

def test_curiosity_sensor_initialization(tmpdir):
    stats_file = os.path.join(str(tmpdir), "stats.json")
    # Patch the stats_file path to use the temporary directory
    CuriositySensor.__init__.__defaults__ = (1.00, 5.0)

    # We'll just monkeypatch the class directly for testing
    original_init = CuriositySensor.__init__

    def mock_init(self, cost_limit=1.00, latency_threshold=5.0):
        self.cost_limit = cost_limit
        self.latency_threshold = latency_threshold
        self.stats_file = stats_file
        self.stats_cache = {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}
        self._init_stats()

    CuriositySensor.__init__ = mock_init

    sensor = CuriositySensor()

    # Ensure stats.json is created
    assert os.path.exists(stats_file)
    with open(stats_file, 'r') as f:
        data = json.load(f)
        assert data == {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}

    # Test log_event updates cache and file
    sensor.log_event(0.1, 1.0)
    assert sensor.stats_cache["total_spent"] == 0.1
    assert sensor.stats_cache["calls"] == 1
    assert sensor.stats_cache["avg_latency"] == 1.0

    with open(stats_file, 'r') as f:
        data = json.load(f)
        assert data == {"total_spent": 0.1, "avg_latency": 1.0, "calls": 1}

    # Test get_internal_state
    assert sensor.get_internal_state() == "STABLE"

    sensor.log_event(1.0, 1.0)
    assert sensor.get_internal_state() == "FINANCIAL_PAIN"

    # Restore original init
    CuriositySensor.__init__ = original_init
