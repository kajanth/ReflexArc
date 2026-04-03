## 2025-02-28 - Non-blocking system vitals monitoring
**Learning:** `psutil.cpu_percent` defaults to blocking the thread if passed a small interval (like 0.1). In `sensors/system_vitals.py`, this was causing a synchronous block in the asyncio event loop every time the sensor polled.
**Action:** Always use `interval=None` with `psutil.cpu_percent` inside async monitor loops to non-blockingly calculate the average CPU utilization since the last poll.
