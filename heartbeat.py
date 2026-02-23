"""
❤️ NSA Digital Heart — Rhythmic Internal Pulse

Like a biological heartbeat, this sends periodic maintenance signals
to the brain. The heartbeat bypasses the RAS (it's never "redundant")
and triggers system health checks via the Cerebellum.

Integration: Started as an async background task in main.py.
"""

import asyncio
from event_bus import event_bus


class DigitalHeart:
    def __init__(self, bpm=2):  # 2 Beats Per Minute = every 30 seconds
        self.interval = 60 / bpm
        self.is_alive = True
        self.beat_count = 0

    async def pulse(self, orchestrator):
        """Rhythmic pulse loop — sends HEARTBEAT_SIGNAL to the brain."""
        print("❤️ [Heart]: System start. Beginning rhythmic pulse...")

        while self.is_alive:
            self.beat_count += 1
            print(f"\n💓 [Heart]: Pulse {self.beat_count}")

            event_bus.publish("heartbeat", {
                "beat": self.beat_count,
                "interval": self.interval,
            })

            try:
                await orchestrator.process_spike(
                    sense_type="heartbeat",
                    description="HEARTBEAT_SIGNAL: Perform periodic maintenance."
                )
            except Exception as e:
                print(f"[Heart] Pulse failed: {e}")

            await asyncio.sleep(self.interval)

    def stop(self):
        """Graceful shutdown."""
        self.is_alive = False
        print("❤️ [Heart]: Flatline. System pulse stopped.")