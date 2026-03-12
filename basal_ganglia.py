"""
🧠 NSA Basal Ganglia — Habit Formation (Layer 5.5)

Reinforces patterns that succeed via Reflex or Template layers.
Repeated patterns get "burned in" — making them faster and cheaper
over time, like muscle memory.

Now with batched writes and async I/O for better performance.
"""

import json
import os
import asyncio
import time
from typing import Dict, Any
from utils.logging_config import get_logger
import fcntl

logger = get_logger(__name__)

HABITS_FILE = "memory/habits.json"


class BasalGanglia:
    def __init__(self, flush_interval: int = 30):
        """
        Initialize Basal Ganglia with write-behind caching.
        
        Args:
            flush_interval: Seconds between automatic flushes (default 30)
        """
        self.habits = {}
        self._dirty = False
        self._flush_interval = flush_interval
        self._last_flush = time.time()
        self._flush_task = None
        self._running = False
        self._load_habits()

    def reinforce_habit(self, pattern_id: str):
        """
        Reinforce a pattern that succeeded.
        Makes repeated patterns cheaper and faster over time.
        Uses write-behind caching - changes are batched and flushed periodically.
        """
        if pattern_id in self.habits:
            habit = self.habits[pattern_id]
            habit["count"] += 1
            habit["latency_multiplier"] = max(0.1, habit["latency_multiplier"] * 0.95)
            habit["cost_multiplier"] = max(0.1, habit["cost_multiplier"] * 0.90)
        else:
            self.habits[pattern_id] = {
                "count": 1,
                "latency_multiplier": 1.0,
                "cost_multiplier": 1.0,
            }

        self._dirty = True
        
        # Check if it's time for a flush
        if time.time() - self._last_flush >= self._flush_interval:
            asyncio.create_task(self._flush_async())

        return self.habits[pattern_id]

    def get_habit_optimization(self, pattern_id: str):
        """Retrieve optimization parameters if a habit exists."""
        return self.habits.get(pattern_id, {
            "latency_multiplier": 1.0,
            "cost_multiplier": 1.0,
            "count": 0,
        })

    def is_habitual(self, pattern_id: str, threshold: int = 3) -> bool:
        """Check if a pattern has been reinforced enough to be a habit."""
        habit = self.habits.get(pattern_id)
        return habit is not None and habit["count"] >= threshold

    def get_all_habits(self) -> dict:
        """Return all habits for dashboard display."""
        return self.habits
    
    async def _flush_async(self):
        """Asynchronously flush dirty habits to disk."""
        if not self._dirty:
            return

        temp_file = f"{HABITS_FILE}.tmp"
        try:
            os.makedirs(os.path.dirname(HABITS_FILE), exist_ok=True)

            # Write to temp file first for atomicity
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._write_habits_sync,
                temp_file,
            )

            # Atomic rename — only reached if write succeeded
            os.replace(temp_file, HABITS_FILE)

            self._dirty = False
            self._last_flush = time.time()

            logger.debug("habits_flushed",
                         habit_count=len(self.habits),
                         file=HABITS_FILE)
        except Exception as e:
            logger.error("habits_flush_failed", error=str(e))
            # Clean up orphaned temp file so the next flush can retry cleanly
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except OSError:
                pass

    
    def _write_habits_sync(self, filepath: str):
        """Synchronous write helper for executor with file locking."""
        with open(filepath, "w") as f:
            try:
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(self.habits, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    
    async def flush(self):
        """Force an immediate flush of pending changes."""
        await self._flush_async()
    
    async def start_periodic_flush(self):
        """Start the periodic flush background task."""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("basal_ganglia_flush_started",
                   interval_seconds=self._flush_interval)
    
    async def stop_periodic_flush(self):
        """Stop the periodic flush task and do a final flush."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush()
        logger.info("basal_ganglia_flush_stopped")
    
    async def _flush_loop(self):
        """Background task that periodically flushes habits."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval)
                if self._dirty:
                    await self._flush_async()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("flush_loop_error", error=str(e))

    def _save_habits(self):
        """
        Mark habits as dirty for batched write.
        Deprecated - use reinforce_habit which handles batching automatically.
        """
        self._dirty = True

    def _load_habits(self):
        """Load habits from disk with file locking."""
        if os.path.exists(HABITS_FILE):
            try:
                with open(HABITS_FILE, "r") as f:
                    try:
                        fcntl.flock(f, fcntl.LOCK_SH)
                        self.habits = json.load(f)
                    finally:
                        fcntl.flock(f, fcntl.LOCK_UN)
            except (json.JSONDecodeError, IOError):
                pass
