"""
🧠 NSA Hippocampus — Async Vector Memory System

Stores and retrieves contextual memories using semantic similarity.
Now with async database operations for non-blocking I/O and connection pooling.
"""

import aiosqlite
import asyncio
import numpy as np
from typing import Optional, List, Tuple
from utils.logging_config import get_logger
from utils.embeddings import get_embedding_model

logger = get_logger(__name__)


class ConnectionPool:
    """
    Simple connection pool for aiosqlite.
    
    Manages a pool of database connections with configurable min/max sizes.
    """
    
    def __init__(self, db_path: str, min_size: int = 1, max_size: int = 5):
        self.db_path = db_path
        self.min_size = min_size
        self.max_size = max_size
        self._pool: List[aiosqlite.Connection] = []
        self._in_use: List[aiosqlite.Connection] = []
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the connection pool with minimum connections."""
        if self._initialized:
            return
        
        async with self._lock:
            if self._initialized:  # Double-check after acquiring lock
                return
            
            for _ in range(self.min_size):
                conn = await aiosqlite.connect(self.db_path)
                self._pool.append(conn)
            
            self._initialized = True
            logger.info("connection_pool_initialized",
                       db_path=self.db_path,
                       min_size=self.min_size,
                       max_size=self.max_size)
    
    async def acquire(self) -> aiosqlite.Connection:
        """
        Acquire a connection from the pool.
        
        Returns:
            An available database connection
        """
        await self.initialize()
        
        async with self._lock:
            # Try to get an available connection from the pool
            if self._pool:
                conn = self._pool.pop()
                self._in_use.append(conn)
                logger.debug("connection_acquired_from_pool",
                           pool_size=len(self._pool),
                           in_use=len(self._in_use))
                return conn
            
            # If pool is empty but we haven't reached max size, create new connection
            if len(self._in_use) < self.max_size:
                conn = await aiosqlite.connect(self.db_path)
                self._in_use.append(conn)
                logger.debug("connection_created",
                           pool_size=len(self._pool),
                           in_use=len(self._in_use))
                return conn
            
            # Pool exhausted, wait for a connection to be released
            logger.warning("connection_pool_exhausted",
                          max_size=self.max_size,
                          message="Waiting for connection to be released")
        
        # Wait a bit and retry
        await asyncio.sleep(0.1)
        return await self.acquire()
    
    async def release(self, conn: aiosqlite.Connection) -> None:
        """
        Release a connection back to the pool.
        
        Args:
            conn: Connection to release
        """
        async with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                
                # Keep connection in pool if we're at or below min size
                if len(self._pool) < self.min_size:
                    self._pool.append(conn)
                    logger.debug("connection_released_to_pool",
                               pool_size=len(self._pool),
                               in_use=len(self._in_use))
                else:
                    # Close excess connections
                    await conn.close()
                    logger.debug("connection_closed",
                               pool_size=len(self._pool),
                               in_use=len(self._in_use))
    
    async def close_all(self) -> None:
        """Close all connections in the pool."""
        async with self._lock:
            # Close all pooled connections
            for conn in self._pool:
                await conn.close()
            
            # Close all in-use connections
            for conn in self._in_use:
                await conn.close()
            
            self._pool.clear()
            self._in_use.clear()
            self._initialized = False
            
            logger.info("connection_pool_closed")
    
    def get_stats(self) -> dict:
        """Get current pool statistics."""
        return {
            "pool_size": len(self._pool),
            "in_use": len(self._in_use),
            "total": len(self._pool) + len(self._in_use),
            "min_size": self.min_size,
            "max_size": self.max_size
        }


class Hippocampus:
    """
    Async vector memory system for contextual recall.
    
    Uses semantic embeddings to store and retrieve relevant memories
    based on similarity to current stimulus. Supports connection pooling
    for efficient database access.
    """
    
    def __init__(self, db_path: str = "memory/long_term_memory.db",
                 min_pool_size: int = 1, max_pool_size: int = 5):
        """
        Initialize Hippocampus with connection pooling.
        
        Args:
            db_path: Path to SQLite database file
            min_pool_size: Minimum number of connections to maintain
            max_pool_size: Maximum number of connections allowed
        """
        self.db_path = db_path
        self._pool = ConnectionPool(db_path, min_pool_size, max_pool_size)
        self._initialized = False
    
    async def __aenter__(self) -> "Hippocampus":
        """Async context manager entry."""
        await self._ensure_initialized()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    def __del__(self) -> None:
        """Cleanup fallback for cases where async context manager isn't used."""
        if self._pool._initialized:
            logger.warning("hippocampus_cleanup_fallback",
                          message="Connection pool not properly closed, using fallback")
            # Note: Can't await in __del__, so we just log the issue
            # Proper cleanup should use async context manager or explicit close()
    
    async def _ensure_initialized(self) -> None:
        """Ensure database connection pool and tables exist."""
        if self._initialized:
            return
        
        await self._pool.initialize()
        await self._create_tables()
        self._initialized = True
        logger.info("hippocampus_initialized",
                   db_path=self.db_path,
                   pool_stats=self._pool.get_stats())
    
    async def _create_tables(self) -> None:
        """Create memory tables if they don't exist."""
        conn = await self._pool.acquire()
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sense_type TEXT,
                    description TEXT,
                    vector BLOB
                )
            ''')
            await conn.commit()
        finally:
            await self._pool.release(conn)
    
    async def store_memory(self, sense_type: str, description: str) -> None:
        """
        Encode and store a memory in the database.
        
        Args:
            sense_type: Type of sensory input (vision, auditory, etc.)
            description: Text description of the event
        """
        await self._ensure_initialized()
        
        # Encode description to vector
        model = get_embedding_model()
        vector = model.encode(description).tobytes()
        
        conn = await self._pool.acquire()
        try:
            await conn.execute(
                "INSERT INTO memories (sense_type, description, vector) VALUES (?, ?, ?)",
                (sense_type, description, vector)
            )
            await conn.commit()
            
            logger.info("memory_stored",
                       sense_type=sense_type,
                       description_preview=description[:50])
        finally:
            await self._pool.release(conn)
    
    async def retrieve_context(self, query_text: str, top_k: int = 3) -> str:
        """
        Find the most relevant historical context for a stimulus.
        
        Args:
            query_text: Current stimulus to find context for
            top_k: Number of similar memories to retrieve
            
        Returns:
            Concatenated context from similar past memories
        """
        await self._ensure_initialized()
        
        # Encode query
        model = get_embedding_model()
        query_vec = model.encode(query_text)
        
        conn = await self._pool.acquire()
        try:
            # Fetch all memories
            cursor = await conn.execute("SELECT description, vector FROM memories")
            rows = await cursor.fetchall()
            
            if not rows:
                logger.debug("no_memories_found")
                return "No prior context found."
            
            # Calculate cosine similarity for each memory
            scores: List[Tuple[float, str]] = []
            for desc, vec_blob in rows:
                stored_vec = np.frombuffer(vec_blob, dtype=np.float32)
                similarity = np.dot(query_vec, stored_vec) / (
                    np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
                )
                scores.append((similarity, desc))
            
            # Sort by similarity and return top results
            scores.sort(key=lambda x: x[0], reverse=True)
            context_items = [s[1] for s in scores[:top_k]]
            
            logger.debug("context_retrieved",
                        query_preview=query_text[:50],
                        num_results=len(context_items),
                        top_similarity=scores[0][0] if scores else 0)
            
            return " | ".join(context_items)
        finally:
            await self._pool.release(conn)
    
    async def get_memory_count(self) -> int:
        """Get total number of stored memories."""
        await self._ensure_initialized()
        
        conn = await self._pool.acquire()
        try:
            cursor = await conn.execute("SELECT COUNT(*) FROM memories")
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await self._pool.release(conn)
    
    async def close(self) -> None:
        """Close all database connections in the pool."""
        await self._pool.close_all()
        self._initialized = False
        logger.info("hippocampus_closed")
    
    def get_pool_stats(self) -> dict:
        """
        Get connection pool statistics.
        
        Returns:
            Dictionary with pool size, in-use connections, and limits
        """
        return self._pool.get_stats()
