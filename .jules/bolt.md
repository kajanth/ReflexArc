## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-04-08 - psutil CPU Polling Blocks Async Loop
**Learning:** Calling `psutil.cpu_percent` with a fixed interval (e.g., `interval=0.1`) blocks the thread synchronously for that duration, which stalls the `asyncio` event loop when called in high-throughput sensor monitoring routes.
**Action:** Always use `interval=None` with `psutil.cpu_percent()` inside async contexts to non-blockingly calculate the average CPU utilization since the last poll.
