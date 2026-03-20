## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2025-02-27 - Synchronous I/O Bottleneck in High-Throughput Components
**Learning:** Discovered a bottleneck in `sensors/curiosity.py` where `get_internal_state` and `log_event` read from disk on every invocation. In high-throughput scenarios (e.g. within an asyncio event loop for triage context gathering on every spike), this blocks the thread significantly and causes latency.
**Action:** For frequently accessed properties and state in components that handle a high volume of calls, cache the state in memory using an instance dictionary (`self._stats`). This allows near-instant read access and reduces the number of file I/O operations strictly to background updates or deferred writes.
