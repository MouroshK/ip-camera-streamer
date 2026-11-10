import time
from datetime import datetime
from typing import Optional
import cv2
import numpy as np

class StreamProcessor:
    def __init__(self, display_width: int, camera_name: str, smoothing_factor: float = 0.9):
        self.display_width = display_width
        self.camera_name = camera_name
        self.smoothing_factor = smoothing_factor
        self.prev_time: Optional[float] = None
        self.smoothed_fps: float = 0.0
        self.notification_text: Optional[str] = None
        self.notification_expiry: float = 0.0

    def resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        if w == self.display_width:
            return frame
        ratio = self.display_width / float(w)
        target_height = int(h * ratio)
        return cv2.resize(frame, (self.display_width, target_height), interpolation=cv2.INTER_LINEAR)

    def calculate_fps(self) -> float:
        current_time = time.perf_counter()
        if self.prev_time is None:
            self.prev_time = current_time
            return 0.0
        delta = current_time - self.prev_time
        self.prev_time = current_time
        if delta > 0.0:
            instantaneous_fps = 1.0 / delta
            if self.smoothed_fps == 0.0:
                self.smoothed_fps = instantaneous_fps
            else:
                self.smoothed_fps = (self.smoothing_factor * self.smoothed_fps) + ((1.0 - self.smoothing_factor) * instantaneous_fps)
        return self.smoothed_fps

    def trigger_notification(self, message: str, duration_sec: float = 2.0):
        self.notification_text = message
        self.notification_expiry = time.time() + duration_sec

    def apply_overlays(self, frame: np.ndarray, is_recording: bool = False, recording_duration: float = 0.0) -> np.ndarray:
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        fps = self.calculate_fps()

        header_height = 40
        overlay_mask = annotated[:header_height, :].copy()
        cv2.rectangle(overlay_mask, (0, 0), (w, header_height), (20, 20, 20), -1)
        cv2.addWeighted(overlay_mask, 0.7, annotated[:header_height, :], 0.3, 0, annotated[:header_height, :])

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_thickness = 1
        font_color = (255, 255, 255)

        cv2.putText(annotated, f"{self.camera_name} | Res: {w}x{h}", (10, 25), font, font_scale, font_color, font_thickness, cv2.LINE_AA)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        right_text = f"{now_str} | FPS: {fps:.1f}"
        (text_w, _), _ = cv2.getTextSize(right_text, font, font_scale, font_thickness)
        cv2.putText(annotated, right_text, (w - text_w - 10, 25), font, font_scale, font_color, font_thickness, cv2.LINE_AA)

        if is_recording:
            cv2.circle(annotated, (20, h - 25), 8, (0, 0, 255), -1)
            rec_text = f"REC [{time.strftime('%M:%S', time.gmtime(recording_duration))}]"
            cv2.putText(annotated, rec_text, (35, h - 19), font, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

        if self.notification_text and time.time() < self.notification_expiry:
            banner_text = self.notification_text
            (b_w, b_h), _ = cv2.getTextSize(banner_text, font, 0.6, 2)
            b_x = (w - b_w) // 2
            b_y = h - 30
            cv2.rectangle(annotated, (b_x - 10, b_y - b_h - 6), (b_x + b_w + 10, b_y + 6), (0, 160, 0), -1)
            cv2.putText(annotated, banner_text, (b_x, b_y), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        elif self.notification_text and time.time() >= self.notification_expiry:
            self.notification_text = None

        return annotated