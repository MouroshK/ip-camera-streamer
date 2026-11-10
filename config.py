import os
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def validate_stream_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https", "rtsp") and bool(parsed.netloc)

CAMERA_STREAM_URL = os.getenv("CAMERA_STREAM_URL", "").strip()
CAMERA_NAME = os.getenv("CAMERA_NAME", "Camera_01").strip()
DISPLAY_WIDTH = int(os.getenv("DISPLAY_WIDTH", "960"))
TARGET_FPS = int(os.getenv("TARGET_FPS", "30"))
CONNECTION_TIMEOUT_SEC = int(os.getenv("CONNECTION_TIMEOUT_SEC", "5"))
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "5"))
RECONNECT_DELAY_SEC = int(os.getenv("RECONNECT_DELAY_SEC", "2"))

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
RECORDING_DIR = os.path.join(os.path.dirname(__file__), "recordings")

for path in (SCREENSHOT_DIR, RECORDING_DIR):
    os.makedirs(path, exist_ok=True)

if not validate_stream_url(CAMERA_STREAM_URL):
    sys.stderr.write(f"[ERROR] Invalid or missing CAMERA_STREAM_URL in .env: '{CAMERA_STREAM_URL}'\n")
    sys.exit(1)