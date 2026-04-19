## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.
## 2026-03-12 - Optimizing JSONL Parsing for Tail Extraction
**Learning:** Parsing every line in large JSONL files using `json.loads` just to return the last $N$ entries wastes CPU cycles, especially since JSON parsing is expensive. Although the I/O and parsing were offloaded to a background thread (`asyncio.to_thread`), the overhead scales linearly with the file size.
**Action:** Use `collections.deque(maxlen=limit)` to collect the raw string lines first. Then, apply `json.loads` only to the elements within the deque. This reduces the parsing complexity from $O(N)$ (where $N$ is total lines) to $O(L)$ (where $L$ is the limit), providing a significant performance boost.
