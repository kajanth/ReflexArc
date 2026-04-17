## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-04-17 - Non-blocking psutil.cpu_percent
**Learning:** Using `psutil.cpu_percent(interval=X)` blocks the current thread for X seconds. In an asyncio context, this blocks the entire event loop. However, replacing it with `interval=None` breaks accuracy because it shares a single global state across all callers.
**Action:** Always offload blocking `psutil.cpu_percent(interval=X)` calls to a separate thread using `await asyncio.to_thread()` when inside an asyncio event loop to preserve metric accuracy without blocking concurrency.
