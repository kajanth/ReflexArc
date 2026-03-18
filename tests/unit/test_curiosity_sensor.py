import pytest
import os
import json
import tempfile
import sys
from unittest.mock import patch, MagicMock

# Mock dependencies
sys.modules['pydantic'] = MagicMock()
sys.modules['numpy'] = MagicMock()

from sensors.curiosity import CuriositySensor

def test_curiosity_sensor_init():
    with tempfile.TemporaryDirectory() as temp_dir:
        stats_file = os.path.join(temp_dir, "stats.json")
        with patch("sensors.curiosity.CuriositySensor.__init__", return_value=None) as mock_init:
            sensor = CuriositySensor()
            sensor.stats_file = stats_file
            sensor.cost_limit = 1.0
            sensor.latency_threshold = 5.0
            sensor._init_stats()

            assert os.path.exists(stats_file)
            assert sensor.stats == {"total_spent": 0.0, "avg_latency": 0.0, "calls": 0}

def test_curiosity_sensor_get_internal_state():
    with tempfile.TemporaryDirectory() as temp_dir:
        stats_file = os.path.join(temp_dir, "stats.json")
        with patch("sensors.curiosity.CuriositySensor.__init__", return_value=None) as mock_init:
            sensor = CuriositySensor()
            sensor.stats_file = stats_file
            sensor.cost_limit = 1.0
            sensor.latency_threshold = 5.0
            sensor._init_stats()

            # Test stable
            assert sensor.get_internal_state() == "STABLE"

            # Test financial pain
            sensor.stats["total_spent"] = 1.5
            assert sensor.get_internal_state() == "FINANCIAL_PAIN"

            # Test latency pain
            sensor.stats["total_spent"] = 0.5
            sensor.stats["avg_latency"] = 6.0
            assert sensor.get_internal_state() == "COGNITIVE_LUGGISHNESS"

def test_curiosity_sensor_log_event():
    with tempfile.TemporaryDirectory() as temp_dir:
        stats_file = os.path.join(temp_dir, "stats.json")
        with patch("sensors.curiosity.CuriositySensor.__init__", return_value=None) as mock_init:
            sensor = CuriositySensor()
            sensor.stats_file = stats_file
            sensor.cost_limit = 1.0
            sensor.latency_threshold = 5.0
            sensor._init_stats()

            sensor.log_event(0.5, 2.0)

            assert sensor.stats["total_spent"] == 0.5
            assert sensor.stats["calls"] == 1
            assert sensor.stats["avg_latency"] == 2.0

            sensor.log_event(0.3, 4.0)

            assert sensor.stats["total_spent"] == 0.8
            assert sensor.stats["calls"] == 2
            assert sensor.stats["avg_latency"] == 3.0

            with open(stats_file, "r") as f:
                stats = json.load(f)
                assert stats["total_spent"] == 0.8
                assert stats["calls"] == 2
                assert stats["avg_latency"] == 3.0

def test_curiosity_sensor_loads_existing_stats():
    with tempfile.TemporaryDirectory() as temp_dir:
        stats_file = os.path.join(temp_dir, "stats.json")
        with open(stats_file, "w") as f:
            json.dump({"total_spent": 10.0, "avg_latency": 1.0, "calls": 5}, f)

        with patch("sensors.curiosity.CuriositySensor.__init__", return_value=None) as mock_init:
            sensor = CuriositySensor()
            sensor.stats_file = stats_file
            sensor.cost_limit = 1.0
            sensor.latency_threshold = 5.0
            sensor._init_stats()

            assert sensor.stats["total_spent"] == 10.0
            assert sensor.stats["calls"] == 5
            assert sensor.stats["avg_latency"] == 1.0
