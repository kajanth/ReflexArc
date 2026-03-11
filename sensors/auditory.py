"""
🧠 NSA Sensor: Auditory (Cochlea / Auditory Nerve)
Layer 0 — Peripheral Sense

Monitors the system microphone for ambient sound spikes.
Detects sudden loud events (voice, alarms, impacts) by computing
RMS amplitude over short audio frames.

Falls back gracefully to disabled state if no mic is available.
"""

import struct
import math
import asyncio

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


class AudioSensor:
    def __init__(self, rms_threshold=500, rate=44100, chunk_size=1024):
        """
        Args:
            rms_threshold: RMS amplitude above which a "spike" fires.
            rate: Audio sample rate in Hz.
            chunk_size: Number of frames per buffer read.
        """
        self.rms_threshold = rms_threshold
        self.rate = rate
        self.chunk_size = chunk_size
        self.stream = None
        self.pa = None
        self.available = False
        
        # Adaptive thresholding (EMA of ambient noise)
        self.noise_floor_ema = None
        self.ema_alpha = 0.05
        self.spike_multiplier = 3.0

        if PYAUDIO_AVAILABLE:
            try:
                self.pa = pyaudio.PyAudio()
                self.stream = self.pa.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                )
                self.available = True
            except Exception as e:
                print(f"[Auditory]: Mic unavailable ({e}). Sensor disabled.")
                self.available = False

    def _compute_rms(self, data):
        """Compute Root Mean Square of an audio buffer."""
        count = len(data) // 2  # 16-bit = 2 bytes per sample
        if count == 0:
            return 0
        fmt = f"<{count}h"
        shorts = struct.unpack(fmt, data)
        sum_squares = sum(s * s for s in shorts)
        return math.sqrt(sum_squares / count)

    async def monitor(self):
        """
        Non-blocking audio check.
        Returns (True, description) if a loud event is detected, else (False, None).
        """
        if not self.available:
            return False, None

        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            rms = self._compute_rms(data)

            # Update ambient noise floor EMA
            if self.noise_floor_ema is None:
                self.noise_floor_ema = rms
            elif rms < self.rms_threshold * 5:  # Don't let massive spikes skew the noise floor instantly
                self.noise_floor_ema = (self.ema_alpha * rms) + ((1 - self.ema_alpha) * self.noise_floor_ema)

            # Active threshold is max of base and dynamic
            active_threshold = max(self.rms_threshold, self.noise_floor_ema * self.spike_multiplier)

            if rms > active_threshold:
                db_approx = 20 * math.log10(rms + 1)
                return True, f"Audio spike detected (RMS: {rms:.0f}, Threshold: {active_threshold:.0f}, ~{db_approx:.1f} dB)"

        except Exception:
            pass

        return False, None

    def release(self):
        """Cleanup audio resources."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        if self.pa:
            self.pa.terminate()
