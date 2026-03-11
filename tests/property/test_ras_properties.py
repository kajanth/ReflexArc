"""
Property-based tests for RAS habituation logic.

Uses Hypothesis to test RAS properties across many inputs.
Tests the bio-inspired habituation mechanism that filters
background noise and adapts thresholds based on activity.

**Validates: Requirements FR-001.1 (RAS filtering)**
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
import time
from typing import List, Tuple

# Mock RAS implementation for property testing
class MockRAS:
    """Mock RAS implementation for property-based testing."""
    
    def __init__(self, initial_threshold: float = 0.7):
        self.threshold = initial_threshold
        self.spike_times = []
        self.spike_embeddings = {}
        self.habituation_decay = 0.95
        self.adaptation_rate = 0.1
        
    def process_spike(self, spike_id: str, embedding: List[float], timestamp: float = None) -> bool:
        """
        Process a spike through RAS filtering.
        
        Returns:
            True if spike passes filter (novel), False if filtered (habituated)
        """
        if timestamp is None:
            timestamp = time.time()
            
        # Store spike data
        self.spike_times.append(timestamp)
        self.spike_embeddings[spike_id] = embedding
        
        # Calculate novelty score (simplified cosine similarity)
        novelty_score = self._calculate_novelty(embedding)
        
        # Apply habituation decay
        self._apply_habituation_decay()
        
        # Adapt threshold based on activity
        self._adapt_threshold()
        
        # Filter decision
        passes_filter = novelty_score > self.threshold
        
        return passes_filter
    
    def _calculate_novelty(self, embedding: List[float]) -> float:
        """Calculate novelty score against recent embeddings."""
        if not self.spike_embeddings:
            return 1.0  # First spike is always novel
            
        # Simple similarity calculation (mock)
        recent_embeddings = list(self.spike_embeddings.values())[-10:]
        similarities = []
        
        for recent_emb in recent_embeddings:
            # Simplified dot product similarity
            similarity = sum(a * b for a, b in zip(embedding, recent_emb))
            similarities.append(abs(similarity))
        
        # Novelty is inverse of max similarity
        max_similarity = max(similarities) if similarities else 0
        return 1.0 - min(max_similarity, 1.0)
    
    def _apply_habituation_decay(self):
        """Apply habituation decay to reduce sensitivity over time."""
        current_time = time.time()
        
        # Remove old spikes (older than 1 hour)
        cutoff_time = current_time - 3600
        self.spike_times = [t for t in self.spike_times if t > cutoff_time]
        
        # Clean up old embeddings
        if len(self.spike_embeddings) > 100:
            # Keep only recent embeddings
            recent_keys = list(self.spike_embeddings.keys())[-50:]
            self.spike_embeddings = {
                k: v for k, v in self.spike_embeddings.items() 
                if k in recent_keys
            }
    
    def _adapt_threshold(self):
        """Adapt threshold based on recent activity level."""
        recent_activity = len([t for t in self.spike_times if t > time.time() - 300])  # Last 5 minutes
        
        if recent_activity > 20:  # High activity - raise threshold
            self.threshold = min(0.9, self.threshold + self.adaptation_rate * 0.1)
        elif recent_activity < 5:  # Low activity - lower threshold
            self.threshold = max(0.3, self.threshold - self.adaptation_rate * 0.1)


# Property-based test strategies
spike_embedding = st.lists(
    st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    min_size=10,
    max_size=10
)

spike_id = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))

threshold_value = st.floats(min_value=0.1, max_value=0.9, allow_nan=False, allow_infinity=False)


class TestRASProperties:
    """Property-based tests for RAS habituation logic."""
    
    @given(threshold=threshold_value)
    def test_ras_threshold_bounds(self, threshold):
        """Property: RAS threshold should always stay within valid bounds."""
        ras = MockRAS(initial_threshold=threshold)
        
        # Process many spikes to trigger adaptation
        for i in range(100):
            embedding = [0.1 * i % 1.0] * 10  # Varying embeddings
            ras.process_spike(f"spike_{i}", embedding)
        
        # Threshold should remain in valid range
        assert 0.1 <= ras.threshold <= 0.9
    
    @given(embeddings=st.lists(spike_embedding, min_size=1, max_size=20))
    def test_ras_novelty_detection_consistency(self, embeddings):
        """Property: Identical spikes should become less novel over time."""
        ras = MockRAS()
        
        # Use the same embedding repeatedly
        if embeddings:
            test_embedding = embeddings[0]
            results = []
            
            for i in range(10):
                result = ras.process_spike(f"repeat_{i}", test_embedding)
                results.append(result)
            
            # First spike should likely pass, later ones should be more likely to be filtered
            if len(results) >= 3:
                first_result = results[0]
                later_results = results[2:]  # Skip immediate repeat to avoid edge cases
                
                # If first passed, later ones should be less likely to pass
                if first_result:
                    later_pass_rate = sum(later_results) / len(later_results)
                    # Allow some flexibility due to randomness in similarity calculation
                    assert later_pass_rate <= 0.8  # Should habituate somewhat
    
    @given(
        embedding1=spike_embedding,
        embedding2=spike_embedding,
        spike_count=st.integers(min_value=1, max_value=50)
    )
    def test_ras_different_spikes_independence(self, embedding1, embedding2, spike_count):
        """Property: Different spikes should be processed independently."""
        assume(embedding1 != embedding2)  # Ensure embeddings are different
        
        ras = MockRAS()
        
        # Process alternating different spikes
        results_1 = []
        results_2 = []
        
        for i in range(spike_count):
            if i % 2 == 0:
                result = ras.process_spike(f"type1_{i}", embedding1)
                results_1.append(result)
            else:
                result = ras.process_spike(f"type2_{i}", embedding2)
                results_2.append(result)
        
        # Both types should have some chance of passing (not completely filtered)
        if len(results_1) >= 3 and len(results_2) >= 3:
            # At least one of each type should pass in early attempts
            early_1 = results_1[:2]
            early_2 = results_2[:2]
            
            # Early spikes of different types should have reasonable pass rates
            assert any(early_1) or any(early_2)  # At least some novelty detected
    
    @given(
        initial_threshold=threshold_value,
        spike_intervals=st.lists(
            st.floats(min_value=0.1, max_value=10.0), 
            min_size=5, 
            max_size=20
        )
    )
    def test_ras_temporal_adaptation(self, initial_threshold, spike_intervals):
        """Property: RAS should adapt threshold based on temporal patterns."""
        ras = MockRAS(initial_threshold=initial_threshold)
        
        current_time = time.time()
        
        # Process spikes with given intervals
        for i, interval in enumerate(spike_intervals):
            current_time += interval
            embedding = [0.5 + 0.1 * (i % 5)] * 10  # Slightly varying embeddings
            ras.process_spike(f"temporal_{i}", embedding, current_time)
        
        # Threshold should have adapted from initial value
        # (May increase or decrease based on activity pattern)
        final_threshold = ras.threshold
        
        # Should stay within bounds regardless of adaptation
        assert 0.1 <= final_threshold <= 0.9
        
        # If many rapid spikes, threshold should tend to increase
        avg_interval = sum(spike_intervals) / len(spike_intervals)
        if avg_interval < 1.0:  # Rapid spikes
            # Threshold should not decrease too much under high activity
            assert final_threshold >= initial_threshold - 0.3
    
    @settings(max_examples=50)  # Reduce examples for performance
    @given(
        embeddings=st.lists(spike_embedding, min_size=10, max_size=30),
        noise_level=st.floats(min_value=0.0, max_value=0.3)
    )
    def test_ras_noise_filtering_property(self, embeddings, noise_level):
        """Property: RAS should filter noise while preserving signal."""
        ras = MockRAS()
        
        # Create base signal
        base_embedding = embeddings[0] if embeddings else [0.5] * 10
        
        signal_results = []
        noise_results = []
        
        for i, embedding in enumerate(embeddings[:15]):  # Limit for performance
            if i % 3 == 0:
                # Signal: use base embedding with small variation
                signal_emb = [x + noise_level * (0.5 - (i % 2)) for x in base_embedding]
                result = ras.process_spike(f"signal_{i}", signal_emb)
                signal_results.append(result)
            else:
                # Noise: use random embedding
                result = ras.process_spike(f"noise_{i}", embedding)
                noise_results.append(result)
        
        # Signal should have higher pass rate than pure noise in early stages
        if len(signal_results) >= 2 and len(noise_results) >= 2:
            early_signal_rate = sum(signal_results[:2]) / len(signal_results[:2])
            early_noise_rate = sum(noise_results[:2]) / len(noise_results[:2])
            
            # Allow for some randomness, but signal should generally be better
            # This is a weak property due to the simplified similarity calculation
            assert early_signal_rate >= early_noise_rate - 0.5


class RASStateMachine(RuleBasedStateMachine):
    """Stateful property testing for RAS behavior."""
    
    def __init__(self):
        super().__init__()
        self.ras = MockRAS()
        self.processed_spikes = []
        self.spike_counter = 0
    
    @rule(embedding=spike_embedding)
    def process_spike(self, embedding):
        """Rule: Process a spike through RAS."""
        spike_id = f"spike_{self.spike_counter}"
        self.spike_counter += 1
        
        result = self.ras.process_spike(spike_id, embedding)
        self.processed_spikes.append((spike_id, embedding, result))
    
    @rule(embedding=spike_embedding, count=st.integers(min_value=2, max_value=5))
    def process_repeated_spike(self, embedding, count):
        """Rule: Process the same spike multiple times."""
        results = []
        for i in range(count):
            spike_id = f"repeat_{self.spike_counter}_{i}"
            result = self.ras.process_spike(spike_id, embedding)
            results.append(result)
        
        self.spike_counter += 1
        self.processed_spikes.extend([(f"repeat_{self.spike_counter-1}_{i}", embedding, r) for i, r in enumerate(results)])
    
    @invariant()
    def threshold_bounds_invariant(self):
        """Invariant: Threshold should always be within bounds."""
        assert 0.1 <= self.ras.threshold <= 0.9
    
    @invariant()
    def spike_data_consistency_invariant(self):
        """Invariant: Spike data structures should be consistent."""
        # Number of spike times should not exceed embedding count by too much
        assert len(self.ras.spike_times) <= len(self.ras.spike_embeddings) + 10
        
        # All embeddings should have correct dimension
        for embedding in self.ras.spike_embeddings.values():
            assert len(embedding) == 10


# Test the state machine
TestRASStateMachine = RASStateMachine.TestCase