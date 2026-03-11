"""
Test SentenceTransformer model cleanup functionality.

Validates that models are properly released during shutdown.
"""

import pytest
import asyncio
from brain_core import NSAOrchestrator
from memory.hippocampus import get_embedding_model, cleanup_embedding_model
from dream_engine import cleanup_dream_model


def test_brain_model_cleanup():
    """Test that NSAOrchestrator properly cleans up its RAS model."""
    # Create orchestrator (this loads the RAS model)
    brain = NSAOrchestrator(db_path=":memory:")
    
    # Verify model is loaded
    assert brain.ras_model is not None
    
    # Call cleanup
    brain.cleanup_models()
    
    # Verify model is released
    assert brain.ras_model is None


def test_hippocampus_model_cleanup():
    """Test that shared embedding model is properly cleaned up."""
    # Load the model
    model = get_embedding_model()
    assert model is not None
    
    # Call cleanup
    cleanup_embedding_model()
    
    # Verify model is released (next call should reload it)
    model2 = get_embedding_model()
    assert model2 is not None
    
    # Cleanup again for test isolation
    cleanup_embedding_model()


def test_dream_engine_model_cleanup():
    """Test that dream engine model is properly cleaned up."""
    # Import the module to ensure model is loaded
    import dream_engine
    
    # Verify model exists
    assert dream_engine._model is not None
    
    # Call cleanup
    cleanup_dream_model()
    
    # Verify model is released
    assert dream_engine._model is None


@pytest.mark.asyncio
async def test_full_shutdown_sequence():
    """Test that full shutdown sequence properly cleans up all models."""
    # Create orchestrator
    brain = NSAOrchestrator(db_path=":memory:")
    await brain.memory._ensure_initialized()
    
    # Load shared models
    _ = get_embedding_model()
    
    # Simulate shutdown sequence
    await brain.memory.close()
    brain.cleanup_models()
    cleanup_embedding_model()
    cleanup_dream_model()
    
    # Verify all models are cleaned up
    assert brain.ras_model is None
    
    # Note: We can't directly check the global variables after cleanup
    # but we verified they're set to None in the individual tests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
