# Real-Time IP Camera Video Streaming System

A lightweight, vendor-agnostic desktop viewer and surveillance utility built with Python and OpenCV. This application streams live video over a local network from an authorized IP camera or a smartphone running an IP camera server (e.g., IP Webcam), overlays dynamic operational telemetry, provides interactive still capture and video recording, and features enterprise-grade error resilience against network outages and disconnects.

---

## Key Features

- **Live Stream Ingestion:** Ingests low-latency MJPEG and RTSP video feeds over HTTP/RTSP without proprietary vendor bloatware.
- **Proportional Frame Resizing:** Rescales incoming frames to a fixed display width while calculating and preserving exact source aspect ratios.
- **Real-Time Telemetry Overlays:** Alpha-blended status bar displaying camera identifier, active display resolution, monotonic live timestamps, and an exponentially smoothed frame-rate (FPS) counter.
- **Interactive Screenshot Capture:** Captures high-resolution still frames with millisecond-precision timestamps upon pressing `S`, supported by transient on-screen visual confirmation pills.
- **Interactive Video Recording:** Starts and stops video recording (`.mp4` via `mp4v` FourCC) on keypress `R`, complete with an active elapsed-time recording indicator and fail-safe file flushing.
- **Defensive Networking & Clean Shutdown:**
  - Fast-failing preflight HTTP socket probes via `requests` to avert unmanaged OpenCV C++ backend hangs.
  - Automatic reconnection backoff algorithm with frame-drop tracking for transient network dropouts.
  - POSIX and Windows interrupt trapping (`SIGINT`, `SIGTERM`, `Esc`) to guarantee hardware handles, socket descriptors, and container atom headers (`moov`) are finalized without file corruption.
- **Zero-Trust Secret Isolation:** Environment-driven configuration ensures IP addresses, port numbers, and authentication parameters are never tracked in version control.

---

## Architecture & Project Structure

```text
ip-camera-streamer/
│
├── .env.example          # Template defining configurable parameters
├── .gitignore             # Excludes environments, outputs, and local secrets
├── requirements.txt       # Strict dependency declarations
├── README.md              # Project documentation and operational guide
│
├── config.py              # Configuration validation and environment loader
├── stream_processor.py    # Resizing, telemetry overlay, and FPS calculation engine
├── main.py                # Master application event loop and signal management
│
├── screenshots/           # Output directory for saved still captures (gitignored)
├── recordings/            # Output directory for saved MP4 recordings (gitignored)
└── docs/                  # Verification artifacts, test matrices, and reports
```

---

## Installation & Setup

### Prerequisites
- **Python:** 3.10, 3.11, or 3.12 installed.
- **Camera Device:** An Android phone running [IP Webcam](https://play.google.com/store/apps/details?id=com.pas.webcam) or an RTSP/HTTP-capable IP camera connected to the **same local Wi-Fi network** as your workstation.

### 1. Clone Repository & Create Virtual Environment

```bash
# Clone the repository
git clone https://github.com/<YOUR_GITHUB_USERNAME>/ip-camera-streamer.git
cd ip-camera-streamer

# Create isolated virtual environment
python -m venv .venv

# Activate the virtual environment:
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuration

The application enforces configuration isolation via environment variables.

1. Generate your local `.env` file from the provided template:
   ```bash
   # Windows (PowerShell)
   Copy-Item .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```

2. Open `.env` in an editor and populate your camera's local endpoint:
   ```env
   # Stream Endpoint Configuration
   # Replace with the URL shown in your phone's IP camera application
   CAMERA_STREAM_URL=http://192.168.1.128:8080/video
   CAMERA_NAME=Office_Entrance_Cam

   # Display & Rendering Pipeline
   DISPLAY_WIDTH=960
   TARGET_FPS=30

   # Resiliency & Network Timeouts
   CONNECTION_TIMEOUT_SEC=5
   MAX_RECONNECT_ATTEMPTS=5
   RECONNECT_DELAY_SEC=2
   ```

> **Security Note:** Never commit your active `.env` file or camera URLs to a public repository. The repository's `.gitignore` explicitly prevents tracking of `.env`, `recordings/`, and `screenshots/`.

---

## Usage

Launch the desktop viewer from your terminal:

```bash
python main.py
```

### Runtime Controls

| Key | Action | Description |
| :---: | :---: | :--- |
| **`S`** | **Capture Screenshot** | Saves the current visual frame directly into `screenshots/` with a microsecond timestamp (`screenshot_YYYYMMDD_HHMMSS_ffffff.jpg`) and shows an on-screen confirmation banner. |
| **`R`** | **Toggle Recording** | Toggles video capture to `recordings/recording_YYYYMMDD_HHMMSS.mp4`. Displays an on-screen blinking indicator (`● REC [MM:SS]`). Second press flushes and finalizes the file. |
| **`Esc`** | **Quit Viewer** | Cleanly terminates the active recording (if running), releases the camera feed, flushes file descriptors, and closes all display windows. |
| **`Ctrl+C`** | **Terminal Interrupt** | Trapped via `SIGINT` handler; guarantees non-corrupted recording finalization and terminal recovery without raw tracebacks. |

---

## Network Resiliency & Error Recovery

The viewer implements a fault-tolerant state machine designed to endure adverse local network conditions:

1. **Pre-flight Socket Probing:** Prior to initializing OpenCV's blocking C++ backend, Python issues a non-blocking `GET` probe with a strict 5-second socket timeout via `requests`. If the remote endpoint is down or unreachable, the user is notified immediately without UI hanging.
2. **Transient Wi-Fi Drop Protection:** If the stream drops mid-flight (e.g., packet dropouts or network channel switching), the engine increments a dropped-frame counter. After 30 consecutive empty frames (~1 second), the pipeline triggers automated recovery.
3. **Exponential Backoff:** The reconnect engine releases stale socket handles and initiates up to `MAX_RECONNECT_ATTEMPTS` connection cycles spaced by `RECONNECT_DELAY_SEC`. If the camera re-establishes connectivity, video playback resumes smoothly.
4. **Header Index Finalization:** In video encoding (specifically MP4), container atom headers (`moov`) are finalized upon termination. An unhandled script crash corrupts the recording. This application routes all exits through an idempotent `cleanup()` routine, guaranteeing zero-byte file corruptions are eliminated.

---

## Verified Test Cases

The application has been verified against the project validation suite:

- **TC01 (Live Stream Launch):** Connects to valid camera endpoint within 2 seconds.
- **TC02 (Invalid Scheme/URL):** Rejects malformed addresses with structured exit codes and zero tracebacks.
- **TC03 (Host Unreachable):** Probes inactive endpoints; completes graceful retry cycle and exits cleanly.
- **TC04 (Telemetry Overlays):** Renders legible time, resolution, camera name, and smoothed FPS overlays.
- **TC05 (Aspect Ratio Resizing):** Validates proportional scaling preserving original sensor geometry.
- **TC06 (Collision-Free Screenshots):** Rapid successive captures generate discrete timestamped files.
- **TC07 (Video Recording Lifecycle):** Produces verified, standard-compliant playable `.mp4` video files.
- **TC08 (Mid-Stream Wi-Fi Recovery):** Survives simulated Wi-Fi dropouts and resumes streaming upon link restoration.
- **TC09 (Esc During Recording):** Finalizes video container integrity on interactive exit.
- **TC10 (SIGINT During Recording):** Traps terminal interrupts and guarantees safe disk flush.

---

## License

This project is created for educational and security engineering evaluation under individual project assessment guidelines. Unauthorized access to networks or recording individuals without consent is strictly prohibited.