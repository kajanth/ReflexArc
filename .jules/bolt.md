## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-16 - Synchronous File I/O Bottleneck in High-Throughput Sensors
**Learning:** High-throughput components like sensors (`CuriositySensor.get_internal_state`) being called continuously throughout the codebase can become a major bottleneck if they perform synchronous disk I/O and JSON parsing on every call.
**Action:** When optimizing high-throughput components, cache state in an in-memory dictionary instead of reading from disk on every routine call to prevent synchronous file I/O bottlenecks.
