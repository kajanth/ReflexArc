## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-03-14 - Synchronous os.listdir in High-Throughput Paths
**Learning:** Calling `os.listdir('skills')` synchronously within the `process_spike` method of `NSAOrchestrator` blocks the event loop on every incoming spike, leading to high latency under load.
**Action:** Cache directory contents in memory and use `os.path.getmtime()` with a strict inequality check (`current_mtime != self._cache_mtime`) to invalidate the cache efficiently, avoiding continuous blocking disk I/O while ensuring the cache stays updated when files are added or modified.
