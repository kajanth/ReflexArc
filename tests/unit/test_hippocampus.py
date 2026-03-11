"""
Unit tests for Hippocampus memory system.

Tests the async vector memory functionality including:
- Memory storage and retrieval
- Context similarity search
- Connection pooling
- Resource management
"""

import pytest
import asyncio
import tempfile
import os
import numpy as np
from unittest.mock import patch, MagicMock

from memory.hippocampus import Hippocampus, ConnectionPool


class TestConnectionPool:
    """Test the database connection pool functionality."""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, temp_db_path):
        """Test that connection pool initializes with correct parameters."""
        pool = ConnectionPool(temp_db_path, min_size=2, max_size=5)
        
        await pool.initialize()
        
        assert pool._initialized is True
        assert len(pool._pool) == 2  # min_size connections created
        assert len(pool._in_use) == 0
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_connection_acquire_release(self, temp_db_path):
        """Test acquiring and releasing connections from pool."""
        pool = ConnectionPool(temp_db_path, min_size=1, max_size=3)
        
        # Acquire connection
        conn1 = await pool.acquire()
        assert conn1 is not None
        assert len(pool._in_use) == 1
        
        # Acquire another connection
        conn2 = await pool.acquire()
        assert conn2 is not None
        assert len(pool._in_use) == 2
        
        # Release connections
        await pool.release(conn1)
        await pool.release(conn2)
        
        stats = pool.get_stats()
        assert stats["in_use"] == 0
        assert stats["pool_size"] >= 1  # At least min_size maintained
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_pool_max_size_limit(self, temp_db_path):
        """Test that pool respects max_size limit."""
        pool = ConnectionPool(temp_db_path, min_size=1, max_size=2)
        
        # Acquire up to max_size
        conn1 = await pool.acquire()
        conn2 = await pool.acquire()
        
        assert len(pool._in_use) == 2
        
        # Third acquisition should wait (we'll test with timeout)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(pool.acquire(), timeout=0.2)
        
        # Release one connection
        await pool.release(conn1)
        
        # Now third acquisition should succeed
        conn3 = await pool.acquire()
        assert conn3 is not None
        
        await pool.release(conn2)
        await pool.release(conn3)
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_pool_stats(self, temp_db_path):
        """Test connection pool statistics."""
        pool = ConnectionPool(temp_db_path, min_size=2, max_size=5)
        
        stats = pool.get_stats()
        assert stats["min_size"] == 2
        assert stats["max_size"] == 5
        
        await pool.initialize()
        
        stats = pool.get_stats()
        assert stats["pool_size"] == 2
        assert stats["in_use"] == 0
        assert stats["total"] == 2
        
        # Acquire a connection
        conn = await pool.acquire()
        
        stats = pool.get_stats()
        assert stats["in_use"] == 1
        assert stats["total"] == 2
        
        await pool.release(conn)
        await pool.close_all()


class TestHippocampus:
    """Test the Hippocampus memory system."""
    
    @pytest.mark.asyncio
    async def test_hippocampus_initialization(self, temp_db_path):
        """Test Hippocampus initialization and context manager."""
        async with Hippocampus(temp_db_path, min_pool_size=1, max_pool_size=3) as hippo:
            assert hippo._initialized is True
            assert hippo.db_path == temp_db_path
            
            # Check that tables were created
            count = await hippo.get_memory_count()
            assert count == 0  # Empty database
    
    @pytest.mark.asyncio
    async def test_memory_storage(self, temp_db_path):
        """Test storing memories in the database."""
        async with Hippocampus(temp_db_path) as hippo:
            # Store a memory
            await hippo.store_memory("vision", "Red car detected in parking lot")
            
            # Verify it was stored
            count = await hippo.get_memory_count()
            assert count == 1
            
            # Store another memory
            await hippo.store_memory("auditory", "Loud noise from construction")
            
            count = await hippo.get_memory_count()
            assert count == 2
    
    @pytest.mark.asyncio
    async def test_context_retrieval_empty_database(self, temp_db_path):
        """Test context retrieval from empty database."""
        async with Hippocampus(temp_db_path) as hippo:
            context = await hippo.retrieve_context("test query")
            assert context == "No prior context found."
    
    @pytest.mark.asyncio
    async def test_context_retrieval_with_memories(self, temp_db_path):
        """Test context retrieval with stored memories."""
        async with Hippocampus(temp_db_path) as hippo:
            # Store some memories
            await hippo.store_memory("vision", "Red car in parking lot")
            await hippo.store_memory("vision", "Blue truck on highway")
            await hippo.store_memory("auditory", "Engine noise from vehicle")
            
            # Retrieve context for car-related query
            context = await hippo.retrieve_context("car vehicle", top_k=2)
            
            # Should return relevant memories
            assert context != "No prior context found."
            assert isinstance(context, str)
            assert len(context) > 0
            
            # Context should contain pipe-separated memories
            memories = context.split(" | ")
            assert len(memories) <= 2  # top_k=2
    
    @pytest.mark.asyncio
    async def test_similarity_search(self, temp_db_path):
        """Test that similarity search returns most relevant memories."""
        async with Hippocampus(temp_db_path) as hippo:
            # Store memories with different semantic content
            await hippo.store_memory("vision", "Red sports car racing")
            await hippo.store_memory("vision", "Blue ocean waves")
            await hippo.store_memory("vision", "Fast motorcycle speeding")
            await hippo.store_memory("auditory", "Birds chirping in trees")
            
            # Query for vehicle-related content
            context = await hippo.retrieve_context("fast vehicle", top_k=2)
            
            # Should prioritize vehicle-related memories
            assert "car" in context.lower() or "motorcycle" in context.lower()
            # Should not include unrelated content like ocean or birds
            assert "ocean" not in context.lower()
            assert "birds" not in context.lower()
    
    @pytest.mark.asyncio
    async def test_pool_stats_access(self, temp_db_path):
        """Test accessing connection pool statistics."""
        async with Hippocampus(temp_db_path, min_pool_size=2, max_pool_size=4) as hippo:
            stats = hippo.get_pool_stats()
            
            assert "pool_size" in stats
            assert "in_use" in stats
            assert "total" in stats
            assert "min_size" in stats
            assert "max_size" in stats
            
            assert stats["min_size"] == 2
            assert stats["max_size"] == 4
    
    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, temp_db_path):
        """Test concurrent memory storage and retrieval operations."""
        async with Hippocampus(temp_db_path, min_pool_size=2, max_pool_size=4) as hippo:
            # Perform concurrent operations
            tasks = []
            
            # Store memories concurrently
            for i in range(5):
                task = hippo.store_memory("test", f"Memory {i}")
                tasks.append(task)
            
            # Add retrieval tasks
            for i in range(3):
                task = hippo.retrieve_context(f"query {i}")
                tasks.append(task)
            
            # Wait for all operations to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check that no exceptions occurred
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent operation failed: {result}")
            
            # Verify memories were stored
            count = await hippo.get_memory_count()
            assert count == 5
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self, temp_db_path):
        """Test that resources are properly cleaned up."""
        hippo = Hippocampus(temp_db_path)
        
        # Initialize manually
        await hippo._ensure_initialized()
        assert hippo._initialized is True
        
        # Close manually
        await hippo.close()
        assert hippo._initialized is False
        
        # Pool should be closed
        stats = hippo.get_pool_stats()
        assert stats["pool_size"] == 0
        assert stats["in_use"] == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_db_path(self):
        """Test error handling with invalid database path."""
        # Use a path that should cause issues (directory as file)
        invalid_path = "/dev/null/invalid.db"
        
        with pytest.raises(Exception):
            async with Hippocampus(invalid_path) as hippo:
                await hippo.store_memory("test", "This should fail")
    
    @pytest.mark.asyncio
    async def test_embedding_model_integration(self, temp_db_path):
        """Test integration with embedding model."""
        with patch('utils.embeddings.get_embedding_model') as mock_get_model:
            # Mock the embedding model
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([0.1, 0.2, 0.3], dtype=np.float32)
            mock_get_model.return_value = mock_model
            
            async with Hippocampus(temp_db_path) as hippo:
                # Store a memory
                await hippo.store_memory("test", "Test memory")
                
                # Verify model was called for encoding
                mock_model.encode.assert_called_with("Test memory")
                
                # Retrieve context
                context = await hippo.retrieve_context("test query")
                
                # Verify model was called for query encoding
                assert mock_model.encode.call_count >= 2  # Once for store, once for retrieve
    
    @pytest.mark.asyncio
    async def test_top_k_parameter(self, temp_db_path):
        """Test that top_k parameter limits results correctly."""
        async with Hippocampus(temp_db_path) as hippo:
            # Store multiple memories
            for i in range(10):
                await hippo.store_memory("test", f"Memory number {i}")
            
            # Test different top_k values
            context_1 = await hippo.retrieve_context("memory", top_k=1)
            context_3 = await hippo.retrieve_context("memory", top_k=3)
            context_5 = await hippo.retrieve_context("memory", top_k=5)
            
            # Count memories in each result
            memories_1 = context_1.split(" | ")
            memories_3 = context_3.split(" | ")
            memories_5 = context_5.split(" | ")
            
            assert len(memories_1) == 1
            assert len(memories_3) == 3
            assert len(memories_5) == 5