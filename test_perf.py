import asyncio
from brain_core import NSAOrchestrator
import time

async def main():
    brain = NSAOrchestrator()
    start = time.time()
    for _ in range(100):
        brain._get_internal_state()
    end = time.time()
    print(f"Time taken: {end - start:.4f} seconds")

asyncio.run(main())
