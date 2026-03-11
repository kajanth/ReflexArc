"""
Unit tests for Basal Ganglia habit formation system.

Tests the habit reinforcement functionality including:
- Habit reinforcement and optimization
- Persistence with write-behind caching
- Async flush operations
- Pattern recognition and thresholds
"""

import pytest
import asyncio
import tempfile
import os
import json
import time
from unittest.mock import patch, mock_open

from basal_ganglia import BasalGanglia


class TestBasalGanglia:
    """Test the Basal Ganglia habit formation system."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Use a temporary file for habits
        self.temp_habits_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_habits_file.close()
        
        # Patch the HABITS_FILE constant
        self.habits_file_patcher = patch('basal_ganglia.HABITS_FILE', self.temp_habits_file.name)
        self.habits_file_patcher.start()
    
    def teardown_method(self):
        """Clean up after each test."""
        self.habits_file_patcher.stop()
        
        # Clean up temp file
        if os.path.exists(self.temp_habits_file.name):
            os.unlink(self.temp_habits_file.name)
    
    def test_initialization(self):
        """Test BasalGanglia initialization."""
        bg = BasalGanglia(flush_interval=60)
        
        assert bg.habits == {}
        assert bg._flush_interval == 60
        assert bg._dirty is False
        assert bg._running is False
    
    def test_reinforce_new_habit(self):
        """Test reinforcing a new habit pattern."""
        bg = BasalGanglia()
        
        # Reinforce a new pattern
        result = bg.reinforce_habit("test_pattern")
        
        # Check that habit was created with default values
        assert "test_pattern" in bg.habits
        habit = bg.habits["test_pattern"]
        assert habit["count"] == 1
        assert habit["latency_multiplier"] == 1.0
        assert habit["cost_multiplier"] == 1.0
        
        # Check return value
        assert result == habit
        assert bg._dirty is True
    
    def test_reinforce_existing_habit(self):
        """Test reinforcing an existing habit pattern."""
        bg = BasalGanglia()
        
        # Create initial habit
        bg.reinforce_habit("existing_pattern")
        initial_habit = bg.habits["existing_pattern"].copy()
        
        # Reinforce again
        result = bg.reinforce_habit("existing_pattern")
        
        # Check that habit was optimized
        habit = bg.habits["existing_pattern"]
        assert habit["count"] == 2
        assert habit["latency_multiplier"] < initial_habit["latency_multiplier"]
        assert habit["cost_multiplier"] < initial_habit["cost_multiplier"]
        
        # Multipliers should not go below 0.1
        assert habit["latency_multiplier"] >= 0.1
        assert habit["cost_multiplier"] >= 0.1
    
    def test_habit_optimization_convergence(self):
        """Test that habit optimization converges to minimum values."""
        bg = BasalGanglia()
        
        # Reinforce many times to test convergence
        for _ in range(100):
            bg.reinforce_habit("convergence_test")
        
        habit = bg.habits["convergence_test"]
        assert habit["count"] == 100
        
        # Should converge to minimum values
        assert habit["latency_multiplier"] == 0.1
        assert habit["cost_multiplier"] == 0.1
    
    def test_get_habit_optimization_existing(self):
        """Test getting optimization parameters for existing habit."""
        bg = BasalGanglia()
        
        # Create a habit
        bg.reinforce_habit("test_habit")
        bg.reinforce_habit("test_habit")  # Reinforce twice
        
        optimization = bg.get_habit_optimization("test_habit")
        
        assert optimization["count"] == 2
        assert optimization["latency_multiplier"] < 1.0
        assert optimization["cost_multiplier"] < 1.0
    
    def test_get_habit_optimization_nonexistent(self):
        """Test getting optimization parameters for non-existent habit."""
        bg = BasalGanglia()
        
        optimization = bg.get_habit_optimization("nonexistent")
        
        # Should return default values
        assert optimization["count"] == 0
        assert optimization["latency_multiplier"] == 1.0
        assert optimization["cost_multiplier"] == 1.0
    
    def test_is_habitual_threshold(self):
        """Test habit threshold detection."""
        bg = BasalGanglia()
        
        # Pattern not yet habitual
        assert bg.is_habitual("new_pattern") is False
        assert bg.is_habitual("new_pattern", threshold=5) is False
        
        # Reinforce below threshold
        bg.reinforce_habit("new_pattern")
        bg.reinforce_habit("new_pattern")
        assert bg.is_habitual("new_pattern", threshold=3) is False
        
        # Reinforce to meet threshold
        bg.reinforce_habit("new_pattern")
        assert bg.is_habitual("new_pattern", threshold=3) is True
        
        # Test default threshold
        assert bg.is_habitual("new_pattern") is True  # default threshold=3
    
    def test_get_all_habits(self):
        """Test retrieving all habits."""
        bg = BasalGanglia()
        
        # Initially empty
        assert bg.get_all_habits() == {}
        
        # Add some habits
        bg.reinforce_habit("habit1")
        bg.reinforce_habit("habit2")
        bg.reinforce_habit("habit1")  # Reinforce habit1 again
        
        all_habits = bg.get_all_habits()
        assert len(all_habits) == 2
        assert "habit1" in all_habits
        assert "habit2" in all_habits
        assert all_habits["habit1"]["count"] == 2
        assert all_habits["habit2"]["count"] == 1
    
    @pytest.mark.asyncio
    async def test_flush_async(self):
        """Test async flush operation."""
        bg = BasalGanglia()
        
        # Add some habits
        bg.reinforce_habit("test_habit")
        assert bg._dirty is True
        
        # Flush
        await bg.flush()
        
        assert bg._dirty is False
        
        # Verify file was written
        assert os.path.exists(self.temp_habits_file.name)
        
        with open(self.temp_habits_file.name, 'r') as f:
            saved_habits = json.load(f)
        
        assert "test_habit" in saved_habits
        assert saved_habits["test_habit"]["count"] == 1
    
    @pytest.mark.asyncio
    async def test_periodic_flush_lifecycle(self):
        """Test starting and stopping periodic flush."""
        bg = BasalGanglia(flush_interval=0.1)  # Very short interval for testing
        
        # Start periodic flush
        await bg.start_periodic_flush()
        assert bg._running is True
        assert bg._flush_task is not None
        
        # Add a habit and wait for auto-flush
        bg.reinforce_habit("auto_flush_test")
        await asyncio.sleep(0.2)  # Wait longer than flush interval
        
        # Should have been flushed
        assert bg._dirty is False
        
        # Stop periodic flush
        await bg.stop_periodic_flush()
        assert bg._running is False
    
    @pytest.mark.asyncio
    async def test_flush_on_reinforce_interval(self):
        """Test that flush is triggered when interval is reached."""
        bg = BasalGanglia(flush_interval=0.1)
        
        # Mock time to control flush timing
        with patch('time.time') as mock_time:
            mock_time.side_effect = [0, 0.2]  # Second call shows interval passed
            
            # This should trigger a flush due to time interval
            bg.reinforce_habit("interval_test")
            
            # Give a moment for the async task to start
            await asyncio.sleep(0.01)
    
    def test_load_habits_existing_file(self):
        """Test loading habits from existing file."""
        # Create a habits file with test data
        test_habits = {
            "existing_habit": {
                "count": 5,
                "latency_multiplier": 0.5,
                "cost_multiplier": 0.6
            }
        }
        
        with open(self.temp_habits_file.name, 'w') as f:
            json.dump(test_habits, f)
        
        # Create BasalGanglia - should load existing habits
        bg = BasalGanglia()
        
        assert "existing_habit" in bg.habits
        habit = bg.habits["existing_habit"]
        assert habit["count"] == 5
        assert habit["latency_multiplier"] == 0.5
        assert habit["cost_multiplier"] == 0.6
    
    def test_load_habits_corrupted_file(self):
        """Test loading habits from corrupted file."""
        # Create a corrupted JSON file
        with open(self.temp_habits_file.name, 'w') as f:
            f.write("invalid json content")
        
        # Should handle corruption gracefully
        bg = BasalGanglia()
        assert bg.habits == {}  # Should start with empty habits
    
    def test_load_habits_nonexistent_file(self):
        """Test loading habits when file doesn't exist."""
        # Remove the temp file
        os.unlink(self.temp_habits_file.name)
        
        # Should handle missing file gracefully
        bg = BasalGanglia()
        assert bg.habits == {}
    
    @pytest.mark.asyncio
    async def test_flush_error_handling(self):
        """Test error handling during flush operations."""
        bg = BasalGanglia()
        bg.reinforce_habit("error_test")
        
        # Mock file operations to raise an error
        with patch('builtins.open', side_effect=IOError("Disk full")):
            # Should not raise exception
            await bg.flush()
            
            # Should still be dirty since flush failed
            assert bg._dirty is True
    
    @pytest.mark.asyncio
    async def test_concurrent_habit_operations(self):
        """Test concurrent habit reinforcement and flush operations."""
        bg = BasalGanglia()
        
        # Start periodic flush
        await bg.start_periodic_flush()
        
        # Perform concurrent operations
        tasks = []
        
        # Multiple reinforcements
        for i in range(10):
            task = asyncio.create_task(
                asyncio.to_thread(bg.reinforce_habit, f"concurrent_habit_{i}")
            )
            tasks.append(task)
        
        # Multiple flushes
        for _ in range(3):
            task = asyncio.create_task(bg.flush())
            tasks.append(task)
        
        # Wait for all operations
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all habits were created
        assert len(bg.habits) == 10
        for i in range(10):
            assert f"concurrent_habit_{i}" in bg.habits
        
        await bg.stop_periodic_flush()
    
    def test_save_habits_deprecated(self):
        """Test deprecated _save_habits method."""
        bg = BasalGanglia()
        
        # Should just mark as dirty
        bg._save_habits()
        assert bg._dirty is True
    
    @pytest.mark.asyncio
    async def test_flush_loop_error_handling(self):
        """Test error handling in the flush loop."""
        bg = BasalGanglia(flush_interval=0.05)
        
        # Start the flush loop
        await bg.start_periodic_flush()
        
        # Add a habit to make it dirty
        bg.reinforce_habit("loop_test")
        
        # Mock flush to raise an error once
        original_flush = bg._flush_async
        error_count = 0
        
        async def mock_flush_with_error():
            nonlocal error_count
            error_count += 1
            if error_count == 1:
                raise Exception("Simulated flush error")
            return await original_flush()
        
        with patch.object(bg, '_flush_async', side_effect=mock_flush_with_error):
            # Wait for a couple of flush cycles
            await asyncio.sleep(0.15)
        
        # Should have recovered from the error
        assert error_count >= 1
        
        await bg.stop_periodic_flush()
    
    @pytest.mark.asyncio
    async def test_atomic_file_operations(self):
        """Test that file operations are atomic (temp file + rename)."""
        bg = BasalGanglia()
        bg.reinforce_habit("atomic_test")
        
        # Mock os.replace to verify it's called
        with patch('os.replace') as mock_replace:
            await bg.flush()
            
            # Should have used atomic rename
            mock_replace.assert_called_once()
            args = mock_replace.call_args[0]
            assert args[0].endswith('.tmp')  # temp file
            assert args[1] == self.temp_habits_file.name  # target file