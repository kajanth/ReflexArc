## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-03-14 - Synchronous os.listdir in critical path
**Learning:** Found `os.listdir('skills')` running synchronously in the hot path of `NSAOrchestrator.process_spike` in `brain_core.py`. On every incoming event, this blocked the entire event loop, causing severe latency under high throughput.
**Action:** Replace direct `os.listdir` calls with an in-memory cache validated by `os.path.getmtime(directory)`. This ensures we only read the directory when its contents have actually changed, preserving event loop availability.
