"""
Manual test script for connection pooling functionality.
"""

import asyncio
import os
import tempfile
from memory.hippocampus import Hippocampus


async def test_basic_pooling():
    """Test basic connection pooling functionality."""
    print("Testing basic connection pooling...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        async with Hippocampus(db_path=db_path, min_pool_size=2, max_pool_size=5) as hippo:
            print(f"✓ Hippocampus initialized with pooling")
            
            stats = hippo.get_pool_stats()
            print(f"  Pool stats: {stats}")
            assert stats["min_size"] == 2
            assert stats["max_size"] == 5
            print(f"✓ Pool configured correctly (min=2, max=5)")
            
            # Store some memories
            await hippo.store_memory("test", "First test memory")
            await hippo.store_memory("test", "Second test memory")
            print(f"✓ Stored 2 memories")
            
            stats = hippo.get_pool_stats()
            print(f"  Pool stats after operations: {stats}")
            assert stats["in_use"] == 0, "All connections should be released"
            print(f"✓ Connections properly released")
            
            # Test concurrent operations
            print("Testing concurrent operations...")
            tasks = []
            for i in range(10):
                tasks.append(hippo.store_memory("test", f"Concurrent memory {i}"))
            
            await asyncio.gather(*tasks)
            print(f"✓ Completed 10 concurrent operations")
            
            count = await hippo.get_memory_count()
            assert count == 12, f"Expected 12 memories, got {count}"
            print(f"✓ All memories stored correctly (count={count})")
            
            stats = hippo.get_pool_stats()
            print(f"  Final pool stats: {stats}")
            assert stats["in_use"] == 0, "All connections should be released"
            print(f"✓ All connections released after concurrent operations")
            
            # Test retrieval
            context = await hippo.retrieve_context("test memory")
            assert len(context) > 0
            print(f"✓ Context retrieval works")
    
    print("\n✅ All tests passed!")


async def test_backward_compatibility():
    """Test backward compatibility with default parameters."""
    print("\nTesting backward compatibility...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        
        # Should work with just db_path (using default pool sizes)
        async with Hippocampus(db_path=db_path) as hippo:
            print(f"✓ Hippocampus initialized with default parameters")
            
            stats = hippo.get_pool_stats()
            print(f"  Default pool stats: {stats}")
            assert stats["min_size"] == 1
            assert stats["max_size"] == 5
            print(f"✓ Default pool sizes correct (min=1, max=5)")
            
            await hippo.store_memory("test", "Test memory")
            context = await hippo.retrieve_context("Test")
            
            assert "Test memory" in context
            print(f"✓ Basic operations work with defaults")
    
    print("✅ Backward compatibility test passed!")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Connection Pooling Tests")
    print("=" * 60)
    
    try:
        await test_basic_pooling()
        await test_backward_compatibility()
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
