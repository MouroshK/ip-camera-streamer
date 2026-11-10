import os
import signal
import sys
import time
from datetime import datetime
from typing import Optional, Tuple
import cv2
import numpy as np
import requests

import config
from stream_processor import StreamProcessor

class IPStreamViewer:
    def __init__(self):
        self.stream_url = config.CAMERA_STREAM_URL
        self.display_width = config.DISPLAY_WIDTH
        self.processor = StreamProcessor(config.DISPLAY_WIDTH, config.CAMERA_NAME)
        self.cap: Optional[cv2.VideoCapture] = None
        self.writer: Optional[cv2.VideoWriter] = None
        self.is_recording = False
        self.recording_start_time: float = 0.0
        self.running = False
        self.consecutive_frame_drops = 0
        self.max_frame_drops = 30

    def preflight_http_check(self) -> bool:
        if not self.stream_url.startswith(("http://", "https://")):
            return True
        try:
            with requests.get(self.stream_url, timeout=config.CONNECTION_TIMEOUT_SEC, stream=True) as response:
                return response.status_code == 200
        except requests.exceptions.RequestException as e:
            sys.stderr.write(f"[WARN] HTTP probe failed: {e}\n")
            return False

    def connect(self) -> bool:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            time.sleep(1.0)

        for attempt in range(1, config.MAX_RECONNECT_ATTEMPTS + 1):
            sys.stdout.write(f"[INFO] Connection attempt {attempt}/{config.MAX_RECONNECT_ATTEMPTS} to {self.stream_url}...\n")
            if self.preflight_http_check():
                self.cap = cv2.VideoCapture(self.stream_url)
                if self.cap.isOpened():
                    sys.stdout.write("[SUCCESS] Camera stream connected.\n")
                    self.consecutive_frame_drops = 0
                    return True
                sys.stderr.write("[WARN] VideoCapture failed to open camera stream.\n")
            else:
                sys.stderr.write("[WARN] Camera unreachable or returned non-200 status.\n")

            if attempt < config.MAX_RECONNECT_ATTEMPTS:
                time.sleep(config.RECONNECT_DELAY_SEC)

        sys.stderr.write("[FATAL] Camera unavailable after max reconnect attempts.\n")
        return False


    
    def capture_screenshot(self, frame: np.ndarray):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = os.path.join(config.SCREENSHOT_DIR, f"screenshot_{timestamp}.jpg")
        cv2.imwrite(path, frame)
        self.processor.trigger_notification(f"Saved: {os.path.basename(path)}")
        sys.stdout.write(f"[INFO] Screenshot saved: {path}\n")

    def toggle_recording(self, frame_size: Tuple[int, int]):
        if not self.is_recording:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(config.RECORDING_DIR, f"recording_{timestamp}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(path, fourcc, config.TARGET_FPS, frame_size)
            if not self.writer.isOpened():
                sys.stderr.write(f"[ERROR] Failed to open VideoWriter at {path}\n")
                self.writer = None
                return
            self.is_recording = True
            self.recording_start_time = time.time()
            self.processor.trigger_notification("Recording Started")
            sys.stdout.write(f"[INFO] Recording started: {path}\n")
        else:
            self.stop_recording()
            self.processor.trigger_notification("Recording Saved")

    def stop_recording(self):
        if self.is_recording and self.writer is not None:
            self.writer.release()
            self.writer = None
            self.is_recording = False
            sys.stdout.write("[INFO] Recording finalized and saved cleanly.\n")

    def run(self):
        if not self.connect():
            self.cleanup()
            return

        self.running = True
        window_name = f"Live Monitor - {config.CAMERA_NAME}"
        cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)

        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                self.consecutive_frame_drops += 1
                if self.consecutive_frame_drops >= self.max_frame_drops:
                    sys.stderr.write("[ERROR] Stream dropped mid-flight. Reconnecting...\n")
                    if self.cap:
                        self.cap.release()
                    if not self.connect():
                        break
                continue

            self.consecutive_frame_drops = 0
            processed_frame = self.processor.resize(frame)
            rec_duration = time.time() - self.recording_start_time if self.is_recording else 0.0
            display_frame = self.processor.apply_overlays(processed_frame, is_recording=self.is_recording, recording_duration=rec_duration)

            if self.is_recording and self.writer is not None:
                self.writer.write(display_frame)

            cv2.imshow(window_name, display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # Esc
                break
            elif key in (ord('s'), ord('S')):
                self.capture_screenshot(display_frame)
            elif key in (ord('r'), ord('R')):
                h, w = display_frame.shape[:2]
                self.toggle_recording(frame_size=(w, h))

        self.cleanup()

    def cleanup(self):
        self.running = False
        self.stop_recording()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        cv2.destroyAllWindows()
        for _ in range(5):
            cv2.waitKey(1)
        sys.stdout.write("[INFO] Shutdown complete. Resources released.\n")

viewer_instance: Optional[IPStreamViewer] = None

def handle_interrupt(sig, frame):
    if viewer_instance:
        viewer_instance.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)
    viewer_instance = IPStreamViewer()
    viewer_instance.run()