# Architecture

Smart Stick is an offline-first, BVI navigation assistant. The Raspberry Pi
backend is structured as a clean, layered Python application so that
detection logic, hardware drivers, storage, and the HTTP API can evolve
independently.

---

## Data flow

```
┌──────────┐   frame    ┌──────────┐   prediction   ┌──────────────┐
│ camera   │ ─────────► │ YOLO     │ ─────────────► │ AlertEngine  │
└──────────┘            └──────────┘                └──────┬───────┘
                                                          │ decision
┌──────────┐   distance ┌──────────────────┐              ▼
│ lidar /  │ ─────────► │ distance_fusion  │       ┌──────────────┐
│ ultrasonic            └──────────────────┘       │ OutputService │ ──► ESP32 (haptics, buzzer)
└──────────┘                                       │ + Speaker     │ ──► TTS / earpiece
                                                   └──────┬────────┘
                                                          │ persist
                                                          ▼
                                                   ┌──────────────┐
                                                   │ SQLite       │
                                                   └──────────────┘
                                                          ▲
┌──────────┐                                              │
│ GPS      │ ─► LocationService ─────────────────────────┤
│ Battery  │ ─► BatteryService ──► warning callback ─────┤
│ Metrics  │ ─► ElectricalLogger ────────────────────────┘
└──────────┘
```

The HTTP layer reads from the latest snapshots cached by the services or
queries repositories directly; it never reads sensors.

---

## Why each layer exists

| Layer        | Knows about            | Forbidden                                |
| ------------ | ---------------------- | ---------------------------------------- |
| `core/`      | enums, types, config   | I/O, sensors, framework code             |
| `utils/`     | core only              | sensors, storage, FastAPI                |
| `sensors/`   | core, utils            | detection, storage, output, API          |
| `detection/` | core, utils, sensors   | storage, output, API                     |
| `storage/`   | core, utils            | sensors, detection, output               |
| `output/`    | core, utils, esp32     | detection, services, API                 |
| `services/`  | everything below       | (orchestrates — should remain *thin*)    |
| `api/`       | services, schemas only | hardware drivers, raw SQL                |

Following these rules:

- Detection logic is unit-testable without any hardware imports.
- Swapping sensors (real LIDAR vs. simulated) only touches `sensors/`.
- Switching from SQLite to another store only touches `storage/`.
- New endpoints add a route + service method; no other layers change.

---

## Threading model

| Thread              | Owner                  | Cadence                          |
| ------------------- | ---------------------- | -------------------------------- |
| `detection-loop`    | `DetectionLoop`        | `DETECTION_FPS` (default 6 Hz)  |
| `location`          | `LocationService`      | `GPS_UPDATE_INTERVAL_S` (5 s)    |
| `battery`           | `BatteryService`       | `BATTERY_UPDATE_INTERVAL_S` (30 s) |
| `electrical`        | `ElectricalLogger`     | `ELECTRICAL_LOG_INTERVAL_S` (30 s) |
| `output-queue`      | `OutputQueue` worker   | Drains FIFO; never blocks producers |
| Main / uvicorn      | FastAPI                | Per-request                      |

All worker threads are daemons; shutdown is triggered by `Container.stop_all()`
which sets the per-thread stop event and `join`s with a small timeout.

Detection is intentionally **producer/consumer**: the loop fires
`on_detections(...)`; the service hands every output to `OutputQueue` so
disk I/O or ESP32 latency never delays the next frame.

---

## Configuration philosophy

- `core/config.py` reads `os.environ` exactly once at import time and
  exposes typed `Final` attributes.
- No other file reads `os.environ`.
- No file hardcodes paths, ports, pins, or thresholds — every value is in
  `core/config.py` or `core/constants.py`.

---

## Persistence philosophy

- Pydantic models in `storage/models.py` are the single source of truth
  for record shape.
- SQL DDL lives only in `storage/schema.py`.
- Repositories in `storage/repositories.py` own every SQL statement for
  their table.
- Services build records and hand them to repositories — they never write
  SQL directly.

---

## Output philosophy

- All outputs go through `OutputService`, which:
  1. Builds a command with a unique id.
  2. Records the command in `commands` (or `messages` for TTS).
  3. Submits a callable to `OutputQueue`.
- The queue worker executes the callable on a background thread and
  reports success back to the repository. Producers never wait.

---

## Failure handling

- Sensors never raise from `read()`. Failed reads return
  `SensorReading(healthy=False, error=...)` and increment a failure
  counter on the sensor's `SensorStatus`.
- Optional dependencies (`cv2`, `RPi.GPIO`, `smbus2`, `pyserial`,
  `ultralytics`, `pyttsx3`, `psutil`) are imported behind try/except so
  the application boots in any environment.
- Persistence failures are logged at `DEBUG`; the detection loop
  continues so users do not lose alerts when disk is briefly slow.

---

## Open follow-ups

- `GET /api/latest_frame`: requires a shared frame buffer between the
  detection loop and the API. Today returns 501.
- WebSocket streaming for the mobile app.
- IMU-based fall detection wired into `AlertEngine`.
- Firebase sync of daily summaries (cloud is Phase 2).
