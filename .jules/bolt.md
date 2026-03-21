## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2025-03-21 - Caching to Prevent Synchronous File I/O Bottlenecks
**Learning:** High-throughput components (like the `CuriositySensor` in `sensors/curiosity.py`) that perform synchronous file I/O operations (like reading JSON configurations) on every polling tick can become massive bottlenecks. Reading from the file system repetitively creates an unnecessary drag on performance.
**Action:** Use an in-memory caching mechanism (like a class-level dictionary) to store the state. To safely support concurrency across processes, ensure that any write operations retain a read-modify-write pattern directly against the file while concurrently updating the in-memory cache for fast read access.
