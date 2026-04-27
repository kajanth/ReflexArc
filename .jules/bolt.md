## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-04-27 - Caching os.listdir for high-throughput loops
**Learning:** Found that `os.listdir('skills')` was being called synchronously inside `brain_core.py:process_spike`, which is the high-throughput neural cascade loop. Even though the impact isn't an entire file read, repeated directory reads can bottleneck the event loop during heavy loads.
**Action:** Replaced `os.listdir` with an in-memory cached list combined with `os.path.getmtime('skills')`. `os.path.getmtime` is extremely fast and serves as a sub-millisecond validity check before paying the higher cost of scanning the directory contents.
