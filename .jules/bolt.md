## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.
## 2024-06-13 - Optimize JSONL parsing for recent N entries
**Learning:** When parsing large JSONL files for the most recent N entries, applying `json.loads` to every line is O(N) and very slow. Using `deque(maxlen=N)` on raw lines before filtering is risky because valid entries could be dropped.
**Action:** Iterate over `f.readlines()` in reverse, apply fast substring pre-filters (e.g., `f'"{change_type}"' in line`) to bypass unnecessary parsing, and break early once N valid entries are collected. Reverse the final list to preserve chronological order. This makes the read O(limit) instead of O(N) for JSON parsing.
