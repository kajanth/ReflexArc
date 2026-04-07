## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-05-15 - psutil blocking in asyncio
**Learning:** `psutil.cpu_percent(interval=0.1)` performs a blocking sleep for the specified interval. In an `async` context like `sensors/system_vitals.py`, this completely stalls the main event loop for 100ms on every poll, causing severe latency degradation across the entire application.
**Action:** Always use `psutil.cpu_percent(interval=None)` inside async functions to get a non-blocking measurement since the last call, or execute it in a separate thread/executor if a specific interval measurement is required.
