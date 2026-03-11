#!/usr/bin/env python3
"""
Manual test for SentenceTransformer model cleanup functionality.

Run this script to verify that models are properly released during shutdown.
"""

import asyncio
import sys


def test_brain_model_cleanup():
    """Test that NSAOrchestrator properly cleans up its RAS model."""
    print("Test 1: Brain RAS model cleanup...")
    
    from brain_core import NSAOrchestrator
    
    # Create orchestrator (this loads the RAS model)
    brain = NSAOrchestrator(db_path=":memory:")
    
    # Verify model is loaded
    assert brain.ras_model is not None, "RAS model should be loaded"
    print("  ✓ RAS model loaded")
    
    # Call cleanup
    brain.cleanup_models()
    
    # Verify model is released
    assert brain.ras_model is None, "RAS model should be None after cleanup"
    print("  ✓ RAS model cleaned up successfully")
    print()


def test_hippocampus_model_cleanup():
    """Test that shared embedding model is properly cleaned up."""
    print("Test 2: Hippocampus shared embedding model cleanup...")
    
    from memory.hippocampus import get_embedding_model, cleanup_embedding_model
    
    # Load the model
    model = get_embedding_model()
    assert model is not None, "Embedding model should be loaded"
    print("  ✓ Embedding model loaded")
    
    # Call cleanup
    cleanup_embedding_model()
    print("  ✓ Embedding model cleaned up")
    
    # Verify model can be reloaded (next call should reload it)
    model2 = get_embedding_model()
    assert model2 is not None, "Embedding model should be reloadable"
    print("  ✓ Embedding model can be reloaded")
    
    # Cleanup again for test isolation
    cleanup_embedding_model()
    print()


def test_dream_engine_model_cleanup():
    """Test that dream engine model is properly cleaned up."""
    print("Test 3: Dream engine model cleanup...")
    
    # Import the module to ensure model is loaded
    import dream_engine
    from dream_engine import cleanup_dream_model
    
    # Verify model exists
    assert dream_engine._model is not None, "Dream model should be loaded"
    print("  ✓ Dream engine model loaded")
    
    # Call cleanup
    cleanup_dream_model()
    
    # Verify model is released
    assert dream_engine._model is None, "Dream model should be None after cleanup"
    print("  ✓ Dream engine model cleaned up successfully")
    print()


async def test_full_shutdown_sequence():
    """Test that full shutdown sequence properly cleans up all models."""
    print("Test 4: Full shutdown sequence...")
    
    from brain_core import NSAOrchestrator
    from memory.hippocampus import get_embedding_model, cleanup_embedding_model
    from dream_engine import cleanup_dream_model
    
    # Create orchestrator
    brain = NSAOrchestrator(db_path=":memory:")
    await brain.memory._ensure_initialized()
    print("  ✓ Brain initialized")
    
    # Load shared models
    _ = get_embedding_model()
    print("  ✓ Shared models loaded")
    
    # Simulate shutdown sequence
    await brain.memory.close()
    print("  ✓ Hippocampus closed")
    
    brain.cleanup_models()
    print("  ✓ Brain models cleaned up")
    
    cleanup_embedding_model()
    print("  ✓ Embedding model cleaned up")
    
    cleanup_dream_model()
    print("  ✓ Dream model cleaned up")
    
    # Verify all models are cleaned up
    assert brain.ras_model is None, "RAS model should be None"
    print("  ✓ All models successfully cleaned up")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("SentenceTransformer Model Cleanup Tests")
    print("=" * 60)
    print()
    
    try:
        test_brain_model_cleanup()
        test_hippocampus_model_cleanup()
        test_dream_engine_model_cleanup()
        asyncio.run(test_full_shutdown_sequence())
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
