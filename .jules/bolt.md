## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-04-11 - Asynchronous CPU Profiling
**Learning:** `psutil.cpu_percent(interval=0.1)` introduces a synchronous 0.1-second sleep inside the execution flow, directly blocking the asyncio event loop when executed within an `async def monitor()` sensor routine. Over many frequent loops, this severely degrades concurrent performance.
**Action:** Use `psutil.cpu_percent(interval=None)` inside asynchronous polling loops to instantly fetch the average CPU utilization measured since the last call, keeping the event loop unblocked.
