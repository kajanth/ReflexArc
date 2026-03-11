"""
Tests for Hippocampus connection pooling functionality.
"""

import pytest
import asyncio
import os
import tempfile
from memory.hippocampus import Hippocampus


@pytest.mark.asyncio
async def test_connection_pool_initialization():
    """Test that connection pool initializes with correct min/max sizes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        async with Hippocampus(db_path=db_path, min_pool_size=2, max_pool_size=5) as hippo:
            stats = hippo.get_pool_stats()
            
            # Pool should have min_size connections available
            assert stats["min_size"] == 2
            assert stats["max_size"] == 5
            assert stats["pool_size"] >= 2  # At least min_size connections


@pytest.mark.asyncio
async def test_connection_pool_acquire_release():
    """Test that connections can be acquired and released."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        async with Hippocampus(db_path=db_path, min_pool_size=1, max_pool_size=3) as hippo:
            # Store a memory (acquires and releases connection)
            await hippo.store_memory("test", "Test memory 1")
            
            stats = hippo.get_pool_stats()
            # After operation, connection should be back in pool
            assert stats["in_use"] == 0
            
            # Store multiple memories concurrently
            await asyncio.gather(
                hippo.store_memory("test", "Test memory 2"),
                hippo.store_memory("test", "Test memory 3"),
                hippo.store_memory("test", "Test memory 4")
            )
            
            # All connections should be released after operations
            stats = hippo.get_pool_stats()
            assert stats["in_use"] == 0


@pytest.mark.asyncio
async def test_connection_pool_concurrent_operations():
    """Test that pool handles concurrent operations correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        async with Hippocampus(db_path=db_path, min_pool_size=2, max_pool_size=4) as hippo:
            # Perform many concurrent operations
            tasks = []
            for i in range(10):
                tasks.append(hippo.store_memory("test", f"Concurrent memory {i}"))
            
            await asyncio.gather(*tasks)
            
            # Verify all memories were stored
            count = await hippo.get_memory_count()
            assert count == 10
            
            # All connections should be released
            stats = hippo.get_pool_stats()
            assert stats["in_use"] == 0


@pytest.mark.asyncio
async def test_connection_pool_cleanup():
    """Test that connection pool is properly cleaned up."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        hippo = Hippocampus(db_path=db_path, min_pool_size=2, max_pool_size=5)
        
        async with hippo:
            await hippo.store_memory("test", "Test memory")
            stats = hippo.get_pool_stats()
            assert stats["total"] >= 2
        
        # After context exit, pool should be closed
        stats = hippo.get_pool_stats()
        assert stats["total"] == 0
        assert stats["pool_size"] == 0
        assert stats["in_use"] == 0


@pytest.mark.asyncio
async def test_backward_compatibility():
    """Test that Hippocampus works with default parameters (backward compatibility)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Should work with just db_path (using default pool sizes)
        async with Hippocampus(db_path=db_path) as hippo:
            await hippo.store_memory("test", "Test memory")
            context = await hippo.retrieve_context("Test")
            
            assert "Test memory" in context
            
            count = await hippo.get_memory_count()
            assert count == 1
