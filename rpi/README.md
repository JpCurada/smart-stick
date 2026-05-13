# Smart Stick — RPi Backend

FastAPI backend for the Smart Stick BVI device. Runs on a Raspberry Pi 5,
orchestrates the sensor stack, runs YOLO object detection, drives the
haptics/buzzer/TTS outputs, persists telemetry to SQLite, and exposes a
local HTTP API consumed by the caregiver mobile app.

---

## Quick start

### 1. Install dependencies

```bash
cd rpi
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On non-Pi hardware (for development), packages that need GPIO/I2C/Serial
silently fall back to logged stubs — the API and detection layer still
boot so you can exercise endpoints with `pytest` and the OpenAPI docs.

### 2. Configure

```bash
cp .env.example .env
# edit .env to match your hardware and storage paths
```

The `Config` class in `core/config.py` reads each variable exactly once
at import time. Nothing else in the codebase reads `os.environ` directly.

### 3. Run

```bash
python main.py
# or
uvicorn api.app:create_app --factory --host 0.0.0.0 --port 5000
```

Then open `http://<rpi-ip>:5000/docs` for the auto-generated Swagger UI.

### 4. Run as a systemd service

```bash
sudo cp systemd/smartstick.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now smartstick
journalctl -u smartstick -f
```

---

## Layout

```
rpi/
├── core/         Configuration, constants, types, exceptions
├── sensors/      Hardware abstraction (camera, gps, lidar, ultrasonic, imu, battery, esp32)
├── detection/    YOLO model, alert engine, rate limiter, distance fusion, detection loop
├── output/       Vibration, buzzer, TTS, async command queue
├── storage/      SQLite database, Pydantic models, repositories, migrations
├── services/     Orchestrators (detection, location, battery, electrical log, sessions, messages)
├── api/          FastAPI app, routes, DI container, schemas, middleware
├── utils/        Shared utilities (logger, decorators, geometry, validators, converters)
├── tests/        Unit tests (no hardware required)
├── systemd/      Service unit file
├── main.py       Entry point
└── requirements.txt
```

Each layer depends only on layers above it. Sensors do not know about the
API, the API does not know about hardware, services are the only code
allowed to chain sensors → detection → storage → output.

---

## API surface (all under `/api`)

| Method | Path                             | Purpose                                       |
| ------ | -------------------------------- | --------------------------------------------- |
| GET    | `/latest_detections`             | Current detections, FPS, latest alert         |
| GET    | `/detections/history?hours=24`   | Historical detections                         |
| GET    | `/location`                      | Most recent GPS fix                           |
| GET    | `/history/location?hours=24`     | Location history                              |
| GET    | `/history/location/geojson`      | Location history as GeoJSON                   |
| GET    | `/battery`                       | Battery percentage, voltage, health, runtime  |
| GET    | `/latest_frame`                  | Latest JPEG (501 in MVP — streaming pending)  |
| POST   | `/vibrate`                       | Trigger vibration `{intensity, duration_ms}`  |
| POST   | `/buzz`                          | Play buzzer `{frequency_hz, duration_ms}`     |
| POST   | `/message`                       | Send TTS text `{text, priority}`              |
| GET    | `/message/history`               | Last 20 messages                              |
| POST   | `/emergency/sos`                 | Trigger SOS tone pattern                      |
| GET    | `/health`                        | Liveness                                      |
| GET    | `/status`                        | Aggregate runtime status                      |

---

## Testing

```bash
pytest
```

All tests run without hardware: sensors are mocked, the YOLO model is not
loaded, and the database is created in a temp directory.

---

## Operations

- **Database:** SQLite at `Config.DATABASE_PATH`. Schema is initialised on
  startup via `storage.migrations.run_migrations`. WAL is enabled.
- **Retention:** `storage.migrations.apply_retention(db)` deletes rows past
  their window (see `core.constants.RETENTION_DAYS`). Schedule via cron or
  call it from the main loop on a fixed timer.
- **Electrical CSV:** `Config.CSV_LOG_PATH` is appended every
  `ELECTRICAL_LOG_INTERVAL_S` seconds with the schema documented in
  `docs/data-schema.md`.
- **Logs:** All modules use the `get_logger(name)` helper, which configures
  the root logger exactly once. Default format is human-readable; redirect
  to journald when running under systemd.

See `ARCHITECTURE.md` for design decisions and rationale.
