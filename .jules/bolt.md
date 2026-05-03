## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2025-01-08 - O(N) JSON Parsing in Large Logs
**Learning:** Found that `_read_changes_log` and `_read_activity_log` in `api_server.py` were parsing every line of large JSONL files using `json.loads` in order to return only the most recent N entries. This is an O(N) operation on potentially massive log files, acting as a CPU bottleneck for the event loop.
**Action:** When parsing large JSONL files for the most recent entries, use `f.readlines()`, iterate in reverse using `reversed(lines)`, and break once N valid entries are parsed to achieve O(N) performance where N is just the limit.
