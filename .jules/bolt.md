## 2024-03-12 - Sync I/O in Asyncio Event Loop
**Learning:** Found several API endpoints (`/stats`, `/memories/recent`, `/skills`) executing synchronous blocking I/O (disk reads, SQLite queries, `os.listdir`) directly on the main event loop thread. While these might be fast locally, under load they stall the entire `aiohttp` web server, preventing it from handling concurrent requests.
**Action:** Always wrap synchronous disk or database operations in `asyncio.to_thread()` when working within an `async def` route handler in `aiohttp` to ensure the event loop remains unblocked.

## 2024-03-13 - High-throughput sensor bottlenecks
**Learning:** High-throughput components (like `sensors/curiosity.py` calling `get_internal_state`) become severe bottlenecks when performing synchronous file I/O on every call.
**Action:** Always cache state in-memory and use `os.path.getmtime(filepath)` to detect cross-process file modifications, avoiding constant disk reads while keeping the cache up to date.

## 2024-03-14 - Optimizing JSONL Parsing
**Learning:** Parsing large JSONL files by applying `json.loads` to every line and then slicing the list is extremely slow and memory intensive, especially when only the most recent N entries are needed.
**Action:** When parsing large JSONL files for recent entries, use `readlines()`, iterate in reverse, apply fast substring pre-filters (e.g., `f'"{change_type}"' in line`), parse only the required entries, and use `list.reverse()` after collecting the target number of entries to maintain chronological order.
