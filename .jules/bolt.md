## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-03-14 - Large JSONL Log Parsing Bottleneck
**Learning:** Parsing massive JSONL files line-by-line using `json.loads()` on every line, just to take the last few `limit` lines, causes a severe performance bottleneck with lots of overhead due to JSON parsing everything just to throw it away.
**Action:** Always read the file lines into a `collections.deque(maxlen=limit)` of raw strings to get only the recent lines, and *then* run `json.loads` only on those final strings. This turns a slow linear scaling operation with an expensive constant factor into a fast log-tail style operation.
