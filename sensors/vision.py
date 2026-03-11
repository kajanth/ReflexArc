import cv2
import time
import os

class OpenCVReflex:
    def __init__(self, sensitivity=15000):
        self.sensitivity = sensitivity
        self.cap = cv2.VideoCapture(0) # 0 is usually the built-in webcam
        self.last_frame = None
        self._current_raw_frame = None
        self._current_processed_frame = None
        self._last_change_amount = 0

    async def monitor(self):
        """
        Deterministic sensing. 
        Returns (True, description) if motion is detected, else (False, None).
        """
        ret, frame = self.cap.read()
        if not ret:
            return False, None

        # Store raw frame for dashboard streaming
        self._current_raw_frame = frame.copy()

        # Process frame for math-based change detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.last_frame is None:
            self.last_frame = gray
            self._current_processed_frame = frame
            return False, None

        # Compare current frame to previous frame
        frame_delta = cv2.absdiff(self.last_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Calculate how much of the image changed
        change_amount = cv2.countNonZero(thresh)
        self._last_change_amount = change_amount
        self.last_frame = gray

        # Draw motion overlay on frame for dashboard
        display_frame = frame.copy()
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            if cv2.contourArea(contour) > 500:
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Calculate dynamic sensitivity based on time of day
        current_hour = time.localtime().tm_hour
        # Night mode: 8 PM (20) to 6 AM (6) -> highly sensitive
        if current_hour >= 20 or current_hour < 6:
            active_sensitivity = int(self.sensitivity * 0.5)
        else:
            active_sensitivity = self.sensitivity

        # Add HUD overlay
        status = "MOTION" if change_amount > active_sensitivity else "IDLE"
        color = (0, 0, 255) if status == "MOTION" else (0, 255, 0)
        cv2.putText(display_frame, f"[{status}] Delta: {change_amount}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(display_frame, f"Threshold: {active_sensitivity} (Base: {self.sensitivity})",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(display_frame, time.strftime("%H:%M:%S"),
                    (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        self._current_processed_frame = display_frame

        if change_amount > active_sensitivity:
            return True, f"Significant motion detected (Intensity: {change_amount}, Threshold: {active_sensitivity})"
        
        return False, None

    def get_frame(self):
        """Return the current processed frame (with overlays) for MJPEG streaming."""
        return self._current_processed_frame

    def get_raw_frame(self):
        """Return the raw camera frame."""
        return self._current_raw_frame

    def get_stats(self):
        """Return current vision sensor stats."""
        return {
            "change_amount": self._last_change_amount,
            "sensitivity": self.sensitivity,
            "has_frame": self._current_raw_frame is not None,
        }

    def release(self):
        self.cap.release()