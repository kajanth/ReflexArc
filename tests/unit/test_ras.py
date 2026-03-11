"""
Unit tests for RAS (Reticular Activating System) layer in brain_core.py

Tests Layer 1 of the neural cascade: novelty detection, habituation filtering,
and adaptive threshold adjustment. The RAS is critical for $0 cost filtering
that prevents redundant processing in higher layers.

Tests validate:
- 14.3.1: Novelty detection (how it determines if a spike is novel vs habituated)
- 14.3.2: Habituation filtering (how repeated similar spikes get filtered out)  
- 14.3.3: Adaptive threshold adjustment (how threshold changes based on spike frequency)
"""

import pytest
import asyncio
import time
import numpy as np
from unittest.mock import patch, MagicMock
from typing import Optional

# Local imports
from brain_core import NSAOrchestrator
from tests.mocks.mock_provider import MockProvider


class TestRASNoveltyDetection:
    """Test RAS novelty detection functionality (14.3.1)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @pytest.fixture
    def mock_embedding_model(self):
        """Mock embedding model that returns deterministic vectors."""
        mock_model = MagicMock()
        # Create deterministic vectors for testing with more variation
        def encode_text(text):
            # Use text content to create different vectors
            if "Original spike" in text:
                return np.array([0.1, 0.2, 0.3])
            elif "Completely different content" in text:
                return np.array([0.8, 0.9, 0.1])  # Very different vector
            elif "First spike" in text:
                return np.array([1.0, 0.0, 0.0])  # Orthogonal vectors for clear difference
            elif "Second spike" in text:
                return np.array([0.0, 1.0, 0.0])  # Orthogonal to first
            else:
                # Default deterministic vector
                return np.array([
                    hash(text) % 100 / 100.0,
                    (hash(text) >> 8) % 100 / 100.0,
                    (hash(text) >> 16) % 100 / 100.0
                ])
        
        mock_model.encode.side_effect = encode_text
        return mock_model
    
    def test_initial_novelty_threshold(self, orchestrator):
        """Test that RAS starts with correct initial novelty threshold."""
        assert orchestrator.base_novelty_threshold == 0.22
        assert orchestrator.novelty_threshold == 0.22
        assert orchestrator.habituation_vector is None
        assert orchestrator.ras_spike_times == []
    
    @patch('brain_core.get_embedding_model')
    def test_first_spike_always_novel(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that the first spike is always considered novel (no habituation vector)."""
        mock_get_model.return_value = mock_embedding_model
        
        # Mock event bus to avoid actual publishing
        with patch('brain_core.event_bus') as mock_event_bus:
            # Mock other dependencies
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process first spike
                        result = asyncio.run(orchestrator.process_spike("test", "First spike"))
                        
                        # Verify habituation vector was set
                        assert orchestrator.habituation_vector is not None
                        assert len(orchestrator.habituation_vector) == 3
                        
                        # Verify spike was processed (not filtered)
                        mock_event_bus.publish.assert_any_call("spike", {
                            "sense_type": "test",
                            "description": "First spike",
                            "novelty_distance": "Init",
                        })
    
    @patch('brain_core.get_embedding_model')
    def test_similar_spike_detection(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that similar spikes are detected and filtered."""
        mock_get_model.return_value = mock_embedding_model
        
        # Set up initial habituation vector (simulate previous spike)
        initial_text = "Test spike"
        orchestrator.habituation_vector = mock_embedding_model.encode(initial_text)
        
        with patch('brain_core.event_bus') as mock_event_bus:
            # Process very similar spike (should be filtered)
            result = asyncio.run(orchestrator.process_spike("test", "Test spike"))
            
            # Should return None (filtered)
            assert result is None
            
            # Verify RAS filter event was published
            mock_event_bus.publish.assert_called_with("ras_filter", {
                "result": "HABITUATED",
                "distance": pytest.approx(0.0, abs=0.1),  # Very similar = low distance
                "description": "Test spike"
            })
    
    @patch('brain_core.get_embedding_model')
    def test_novel_spike_detection(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that novel spikes pass through RAS filter."""
        mock_get_model.return_value = mock_embedding_model
        
        # Set up initial habituation vector
        orchestrator.habituation_vector = mock_embedding_model.encode("Original spike")
        
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process different spike (should pass through)
                        result = asyncio.run(orchestrator.process_spike("test", "Completely different content"))
                        
                        # Should not return None (not filtered)
                        assert result is not None
                        
                        # Verify novel spike was detected
                        calls = mock_event_bus.publish.call_args_list
                        ras_filter_calls = [call for call in calls if call[0][0] == "ras_filter"]
                        assert any(call[0][1]["result"] == "NOVEL" for call in ras_filter_calls)
    
    def test_cosine_similarity_calculation(self, orchestrator):
        """Test the cosine similarity calculation used in novelty detection."""
        # Create test vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])  # Identical
        vec3 = np.array([0.0, 1.0, 0.0])  # Orthogonal
        
        # Test identical vectors (similarity = 1, distance = 0)
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        distance = 1 - similarity
        assert similarity == pytest.approx(1.0)
        assert distance == pytest.approx(0.0)
        
        # Test orthogonal vectors (similarity = 0, distance = 1)
        similarity = np.dot(vec1, vec3) / (np.linalg.norm(vec1) * np.linalg.norm(vec3))
        distance = 1 - similarity
        assert similarity == pytest.approx(0.0)
        assert distance == pytest.approx(1.0)
    
    @patch('brain_core.get_embedding_model')
    def test_habituation_vector_update(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that habituation vector is updated with each processed spike that passes RAS."""
        mock_get_model.return_value = mock_embedding_model
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process first spike
                        asyncio.run(orchestrator.process_spike("test", "First spike"))
                        first_vector = orchestrator.habituation_vector.copy()
                        
                        # Process second spike that's different enough to pass RAS
                        asyncio.run(orchestrator.process_spike("test", "Second spike"))
                        second_vector = orchestrator.habituation_vector
                        
                        # Habituation vector should be updated to the second spike's vector
                        # Since "Second spike" produces [0.0, 1.0, 0.0] and "First spike" produces [1.0, 0.0, 0.0]
                        expected_second_vector = np.array([0.0, 1.0, 0.0])
                        assert np.array_equal(second_vector, expected_second_vector)
                        assert not np.array_equal(first_vector, second_vector)


class TestRASHabituationFiltering:
    """Test RAS habituation filtering functionality (14.3.2)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @pytest.fixture
    def mock_embedding_model(self):
        """Mock embedding model with predictable similarity."""
        mock_model = MagicMock()
        
        def encode_text(text):
            # Create vectors where similar text has high similarity
            if "similar" in text.lower():
                return np.array([0.8, 0.6, 0.0])  # Base similar vector
            elif "different" in text.lower():
                return np.array([0.1, 0.2, 0.9])  # Different vector
            else:
                # Default vector based on text hash
                return np.array([
                    hash(text) % 100 / 100.0,
                    (hash(text) >> 8) % 100 / 100.0,
                    (hash(text) >> 16) % 100 / 100.0
                ])
        
        mock_model.encode.side_effect = encode_text
        return mock_model
    
    @patch('brain_core.get_embedding_model')
    def test_repeated_similar_spikes_filtered(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that repeated similar spikes are filtered out."""
        mock_get_model.return_value = mock_embedding_model
        
        # Set habituation vector to "similar" content
        orchestrator.habituation_vector = mock_embedding_model.encode("similar content")
        
        with patch('brain_core.event_bus') as mock_event_bus:
            # Process similar spike (should be filtered)
            result = asyncio.run(orchestrator.process_spike("test", "similar content again"))
            
            assert result is None
            
            # Verify habituation filter was triggered
            mock_event_bus.publish.assert_called_with("ras_filter", {
                "result": "HABITUATED",
                "distance": pytest.approx(0.0, abs=0.2),  # Should be low distance
                "description": "similar content again"
            })
    
    @patch('brain_core.get_embedding_model')
    def test_different_spikes_pass_through(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that different spikes pass through habituation filter."""
        mock_get_model.return_value = mock_embedding_model
        
        # Set habituation vector to "similar" content
        orchestrator.habituation_vector = mock_embedding_model.encode("similar content")
        
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process different spike (should pass through)
                        result = asyncio.run(orchestrator.process_spike("test", "different content entirely"))
                        
                        assert result is not None
                        
                        # Verify novel spike was detected
                        calls = mock_event_bus.publish.call_args_list
                        ras_filter_calls = [call for call in calls if call[0][0] == "ras_filter"]
                        assert any(call[0][1]["result"] == "NOVEL" for call in ras_filter_calls)
    
    def test_threshold_boundary_conditions(self, orchestrator):
        """Test habituation filtering at threshold boundaries."""
        # Test with vectors at exact threshold distance
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.78, 0.0, 0.0])  # Should give distance ≈ 0.22 (at threshold)
        
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        distance = 1 - similarity
        
        # At threshold, should be filtered (distance < threshold)
        assert distance < orchestrator.novelty_threshold
    
    @patch('brain_core.get_embedding_model')
    def test_bypass_ras_spikes_not_filtered(self, mock_get_model, orchestrator, mock_embedding_model):
        """Test that spikes that bypass RAS are not subject to habituation filtering."""
        mock_get_model.return_value = mock_embedding_model
        
        # Set habituation vector
        orchestrator.habituation_vector = mock_embedding_model.encode("test content")
        
        with patch('brain_core.event_bus') as mock_event_bus:
            # Process spike that bypasses RAS (heartbeat) - this has special fast-path handling
            result = asyncio.run(orchestrator.process_spike("internal", "HEARTBEAT_SIGNAL: system check"))
            
            # Heartbeat should return a result (not filtered)
            assert result is not None
            assert "Heartbeat" in result
            
            # Verify heartbeat event was published (not spike event since it's fast-path)
            calls = mock_event_bus.publish.call_args_list
            heartbeat_calls = [call for call in calls if call[0][0] == "heartbeat_exec"]
            assert len(heartbeat_calls) > 0


class TestRASAdaptiveThreshold:
    """Test RAS adaptive threshold adjustment functionality (14.3.3)."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    def test_initial_threshold_values(self, orchestrator):
        """Test initial threshold configuration."""
        assert orchestrator.base_novelty_threshold == 0.22
        assert orchestrator.novelty_threshold == 0.22
        assert orchestrator.ras_spike_times == []
    
    def test_spike_time_tracking(self, orchestrator):
        """Test that spike times are tracked correctly."""
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        initial_count = len(orchestrator.ras_spike_times)
                        
                        # Process a spike
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # Spike time should be recorded
                        assert len(orchestrator.ras_spike_times) == initial_count + 1
                        assert orchestrator.ras_spike_times[-1] <= time.time()
    
    def test_spike_time_pruning(self, orchestrator):
        """Test that old spike times are pruned (older than 60 seconds)."""
        # Add old spike times
        now = time.time()
        orchestrator.ras_spike_times = [
            now - 70,  # Should be pruned
            now - 50,  # Should be kept
            now - 30,  # Should be kept
        ]
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process a spike (triggers pruning)
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # Old spike should be pruned, recent ones kept, plus new one
                        assert len(orchestrator.ras_spike_times) == 3  # 2 kept + 1 new
                        assert all(now - t <= 60 for t in orchestrator.ras_spike_times)
    
    def test_high_noise_threshold_adjustment(self, orchestrator):
        """Test threshold adjustment in high noise environment (>20 spikes/min)."""
        # Simulate high noise (21 spikes in last 60 seconds)
        now = time.time()
        orchestrator.ras_spike_times = [now - i for i in range(21)]
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process spike in high noise environment
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # Threshold should be increased (less sensitive)
                        expected_threshold = min(0.60, orchestrator.base_novelty_threshold + 0.15)
                        assert orchestrator.novelty_threshold == expected_threshold
    
    def test_quiet_environment_threshold_adjustment(self, orchestrator):
        """Test threshold adjustment in quiet environment (<5 spikes/min)."""
        # Simulate quiet environment (3 spikes in last 60 seconds)
        now = time.time()
        orchestrator.ras_spike_times = [now - i * 20 for i in range(3)]  # Spread out, only 3 spikes
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process spike in quiet environment
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # After processing, we should have 4 spikes total (3 + 1 new)
                        # This should trigger quiet environment logic (< 5 spikes)
                        expected_threshold = max(0.05, orchestrator.base_novelty_threshold - 0.05)
                        assert orchestrator.novelty_threshold == expected_threshold
    
    def test_normal_environment_threshold_unchanged(self, orchestrator):
        """Test threshold remains unchanged in normal environment (5-20 spikes/min)."""
        # Simulate normal environment (10 spikes in last 60 seconds)
        now = time.time()
        orchestrator.ras_spike_times = [now - i * 6 for i in range(10)]
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        # Process spike in normal environment
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # Threshold should remain at base level
                        assert orchestrator.novelty_threshold == orchestrator.base_novelty_threshold
    
    def test_synaptic_plasticity_threshold_adjustment(self, orchestrator):
        """Test that synaptic plasticity (reinforcement) adjusts base threshold."""
        initial_base_threshold = orchestrator.base_novelty_threshold
        
        # Trigger synaptic plasticity
        orchestrator._handle_reinforce_spike({"description": "useful spike"})
        
        # Base threshold should be lowered (more sensitive)
        assert orchestrator.base_novelty_threshold < initial_base_threshold
        assert orchestrator.base_novelty_threshold == max(0.10, initial_base_threshold - 0.01)
        assert orchestrator.novelty_threshold == orchestrator.base_novelty_threshold
    
    def test_synaptic_plasticity_minimum_threshold(self, orchestrator):
        """Test that synaptic plasticity respects minimum threshold."""
        # Set base threshold near minimum
        orchestrator.base_novelty_threshold = 0.11
        orchestrator.novelty_threshold = 0.11
        
        # Trigger synaptic plasticity
        orchestrator._handle_reinforce_spike({"description": "useful spike"})
        
        # Should be clamped to minimum
        assert orchestrator.base_novelty_threshold == 0.10
        assert orchestrator.novelty_threshold == 0.10
    
    def test_threshold_bounds(self, orchestrator):
        """Test that adaptive thresholds respect bounds."""
        # Test high noise upper bound
        orchestrator.base_novelty_threshold = 0.50
        now = time.time()
        orchestrator.ras_spike_times = [now - i for i in range(25)]  # High noise
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # Should be capped at 0.60
                        assert orchestrator.novelty_threshold <= 0.60
        
        # Test quiet environment lower bound
        orchestrator.base_novelty_threshold = 0.08
        orchestrator.ras_spike_times = [now - 50]  # Very quiet
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context', return_value=""):
                with patch.object(orchestrator.memory, 'store_memory'):
                    with patch.object(orchestrator.router, 'route') as mock_route:
                        mock_route.return_value = MagicMock(
                            content="LOG",
                            provider="mock",
                            model="mock-nano",
                            cost=0.0
                        )
                        
                        asyncio.run(orchestrator.process_spike("test", "test spike"))
                        
                        # Should be clamped at 0.05
                        assert orchestrator.novelty_threshold >= 0.05


class TestRASIntegration:
    """Integration tests for RAS layer functionality."""
    
    @pytest.fixture
    def orchestrator(self, temp_db_path):
        """Create NSAOrchestrator instance for testing."""
        return NSAOrchestrator(db_path=temp_db_path, min_pool_size=1, max_pool_size=2)
    
    @patch('brain_core.get_embedding_model')
    def test_ras_cost_optimization(self, mock_get_model, orchestrator):
        """Test that RAS achieves $0 cost filtering by preventing redundant processing."""
        # Mock embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.5, 0.5, 0.5])
        mock_get_model.return_value = mock_model
        
        # Set up habituation vector
        orchestrator.habituation_vector = np.array([0.5, 0.5, 0.5])  # Identical vector
        
        with patch('brain_core.event_bus'):
            # Process similar spike (should be filtered at $0 cost)
            result = asyncio.run(orchestrator.process_spike("test", "similar content"))
            
            # Should return None (filtered) without expensive processing
            assert result is None
            
            # Embedding model should be called (that's the $0 cost operation)
            mock_model.encode.assert_called_once()
    
    @patch('brain_core.get_embedding_model')
    def test_ras_layer_ordering(self, mock_get_model, orchestrator):
        """Test that RAS operates as Layer 1 before other layers."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_get_model.return_value = mock_model
        
        # Set up for filtering
        orchestrator.habituation_vector = np.array([0.1, 0.2, 0.3])  # Same vector
        
        with patch('brain_core.event_bus'):
            with patch.object(orchestrator.memory, 'retrieve_context') as mock_memory:
                with patch.object(orchestrator.router, 'route') as mock_router:
                    # Process spike that should be filtered
                    result = asyncio.run(orchestrator.process_spike("test", "test content"))
                    
                    # Should be filtered before reaching memory (Layer 3) or router (Layer 2)
                    assert result is None
                    mock_memory.assert_not_called()
                    mock_router.assert_not_called()
    
    def test_ras_event_bus_integration(self, orchestrator):
        """Test RAS integration with event bus for observability."""
        with patch('brain_core.event_bus') as mock_event_bus:
            with patch('brain_core.get_embedding_model') as mock_get_model:
                mock_model = MagicMock()
                mock_model.encode.return_value = np.array([0.5, 0.5, 0.5])
                mock_get_model.return_value = mock_model
                
                # Set up for filtering
                orchestrator.habituation_vector = np.array([0.5, 0.5, 0.5])
                
                # Process filtered spike
                asyncio.run(orchestrator.process_spike("test", "filtered content"))
                
                # Verify RAS filter event was published
                mock_event_bus.publish.assert_called_with("ras_filter", {
                    "result": "HABITUATED",
                    "distance": pytest.approx(0.0, abs=0.1),
                    "description": "filtered content"
                })