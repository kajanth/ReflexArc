## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.
## 2024-05-15 - Fast JSONL Tail Parsing
**Learning:** Parsing the entirety of large JSONL logs sequentially just to extract the `N` most recent entries introduces significant overhead. A reverse reading approach using `readlines()` followed by `reversed()` to parse only until the required `N` entries are found cuts parsing time substantially while remaining O(N) in memory.
**Action:** When tailing JSONL files for the most recent log entries, avoid iterating from the top and applying `json.loads` to every line. Instead, read the lines, iterate them in reverse, and stop parsing once the desired limit is reached.
