## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-03-24 - JSON Parsing Overhead in Large Logs
**Learning:** Found that `utils/changes_logger.py` was calling `json.loads` on every line of potentially large JSONL files (`changes_log.jsonl`), only to discard most of them when filtering or slicing to the last N items. This creates significant CPU overhead when log files grow large.
**Action:** When parsing large JSONL files where only the most recent N entries are needed, read the lines and iterate backwards (`reversed(f.readlines())`), applying simple substring checks (e.g., `'"skill_added"' in line`) as a pre-filter. Apply `json.loads` only to matches, and `break` early once N valid entries are found. This reduces parsing overhead from O(TotalLines) to O(N).
