"""SQL DDL statements. Single source of truth for table definitions."""

from __future__ import annotations

from typing import Final

DETECTIONS_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS detections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id        TEXT UNIQUE NOT NULL,
    timestamp       TEXT NOT NULL,
    unix_ts         INTEGER NOT NULL,
    detection_json  TEXT NOT NULL,
    alert_triggered INTEGER NOT NULL DEFAULT 0,
    object_count    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


LOCATIONS_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS locations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id     TEXT UNIQUE NOT NULL,
    timestamp       TEXT NOT NULL,
    unix_ts         INTEGER NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    altitude        REAL,
    accuracy        REAL,
    speed           REAL,
    location_json   TEXT NOT NULL,
    geohash         TEXT,
    is_home         INTEGER NOT NULL DEFAULT 0,
    is_work         INTEGER NOT NULL DEFAULT 0,
    dwell_time_minutes INTEGER,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


BATTERY_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS battery_status (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    unix_ts         INTEGER NOT NULL,
    voltage         REAL NOT NULL,
    current         INTEGER,
    percentage      INTEGER NOT NULL,
    temperature     REAL,
    health_status   TEXT NOT NULL,
    status_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


COMMANDS_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS commands (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id      TEXT UNIQUE NOT NULL,
    timestamp       TEXT NOT NULL,
    command_type    TEXT NOT NULL,
    params_json     TEXT NOT NULL,
    sent_to_esp32   INTEGER NOT NULL DEFAULT 0,
    ack_received    INTEGER NOT NULL DEFAULT 0,
    execution_time_ms INTEGER,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


MESSAGES_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id      TEXT UNIQUE NOT NULL,
    timestamp       TEXT NOT NULL,
    text            TEXT NOT NULL,
    priority        TEXT NOT NULL DEFAULT 'normal',
    tts_engine      TEXT,
    estimated_speak_time_ms INTEGER,
    delivered       INTEGER NOT NULL DEFAULT 0,
    delivered_at    TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


ALERTS_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id        TEXT UNIQUE NOT NULL,
    timestamp       TEXT NOT NULL,
    alert_type      TEXT NOT NULL,
    severity        TEXT NOT NULL,
    detection_id    TEXT,
    location_latitude REAL,
    location_longitude REAL,
    alert_json      TEXT NOT NULL,
    acknowledged    INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


SESSIONS_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT UNIQUE NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    duration_minutes INTEGER,
    distance_km     REAL,
    detection_count INTEGER NOT NULL DEFAULT 0,
    alert_count     INTEGER NOT NULL DEFAULT 0,
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


ELECTRICAL_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS electrical_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    battery_voltage_v REAL NOT NULL,
    battery_current_ma INTEGER,
    battery_percentage INTEGER,
    rpi_temp_c      REAL,
    esp32_temp_c    REAL,
    wifi_signal_strength_db INTEGER,
    detection_fps   REAL,
    inference_time_ms INTEGER,
    memory_usage_mb INTEGER,
    memory_usage_percent REAL,
    uptime_seconds  INTEGER,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


SENSOR_HEALTH_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS sensor_health (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    camera_ok       INTEGER NOT NULL DEFAULT 0,
    gps_ok          INTEGER NOT NULL DEFAULT 0,
    lidar_ok        INTEGER NOT NULL DEFAULT 0,
    imu_ok          INTEGER NOT NULL DEFAULT 0,
    ultrasonic1_ok  INTEGER NOT NULL DEFAULT 0,
    ultrasonic2_ok  INTEGER NOT NULL DEFAULT 0,
    esp32_ok        INTEGER NOT NULL DEFAULT 0,
    cpu_temp_c      REAL,
    uptime_seconds  INTEGER,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


GEOFENCES_DDL: Final[str] = """
CREATE TABLE IF NOT EXISTS geofences (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    geofence_id     TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    radius_m        REAL NOT NULL,
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


INDEXES: Final[tuple[str, ...]] = (
    "CREATE INDEX IF NOT EXISTS idx_detections_ts ON detections(unix_ts);",
    "CREATE INDEX IF NOT EXISTS idx_detections_alert ON detections(alert_triggered);",
    "CREATE INDEX IF NOT EXISTS idx_locations_ts ON locations(unix_ts);",
    "CREATE INDEX IF NOT EXISTS idx_locations_latlon ON locations(latitude, longitude);",
    "CREATE INDEX IF NOT EXISTS idx_locations_geohash ON locations(geohash);",
    "CREATE INDEX IF NOT EXISTS idx_battery_ts ON battery_status(unix_ts);",
    "CREATE INDEX IF NOT EXISTS idx_battery_pct ON battery_status(percentage);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_ts ON alerts(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_sessions_start ON sessions(start_time);",
    "CREATE INDEX IF NOT EXISTS idx_electrical_ts ON electrical_log(timestamp);",
)


ALL_TABLES: Final[tuple[str, ...]] = (
    DETECTIONS_DDL,
    LOCATIONS_DDL,
    BATTERY_DDL,
    COMMANDS_DDL,
    MESSAGES_DDL,
    ALERTS_DDL,
    SESSIONS_DDL,
    ELECTRICAL_DDL,
    SENSOR_HEALTH_DDL,
    GEOFENCES_DDL,
)
