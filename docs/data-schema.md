# Smart Stick - Complete Data Schema v1.1


## **1. Local Storage Architecture (SQLite)**

### **1.1 Core Tables Overview**

The Smart Stick maintains a local SQLite database with 11 main tables. Data is stored for 7 days rolling (oldest data deleted automatically). This ensures the stick operates 100% offline while maintaining complete operational history.

```
Database: /home/pi/data/smartstick.db
Size limit: ~32MB (7-day rolling window)
Update frequency: Real-time
Backup: Optional sync to Firebase
```

---

## **2. SQLite Table Schemas (Detailed)**

### **2.1 DETECTIONS Table**

**Purpose:** Stores all YOLO object detection results

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing record ID |
| frame_id | TEXT | UNIQUE NOT NULL | Unique frame identifier (timestamp-based) |
| timestamp | DATETIME | NOT NULL | When detection occurred (ISO format) |
| unix_ts | INTEGER | NOT NULL (INDEXED) | Unix timestamp for quick queries |
| detection_json | TEXT | NOT NULL | JSON: {detections: [{class, confidence, bbox, distance_m}]} |
| alert_triggered | INTEGER | 0/1 (INDEXED) | Whether alert was sent (0=no, 1=yes) |
| object_count | INTEGER | >=0 | Number of objects detected in frame |
| created_at | DATETIME | DEFAULT NOW | Record creation timestamp |

**Indexes:**
- idx_timestamp (for time-range queries)
- idx_unix_ts (for fast lookups)
- idx_frame_id (unique check)
- idx_alert (for alert filtering)

**Example Record:**
```
frame_id: "frame_2024_05_06_12_00_23_001"
timestamp: "2024-05-06T12:00:23.456Z"
unix_ts: 1715000423
detection_json: {
  "detections": [
    {"class": "person", "confidence": 0.92, "distance_m": 1.5, "vibration_pattern": "single_pulse"},
    {"class": "car", "confidence": 0.88, "distance_m": 3.2, "vibration_pattern": "double_pulse"}
  ]
}
alert_triggered: 1
object_count: 2
```

**Retention:** 7 days rolling (oldest deleted daily)

---

### **2.2 LOCATIONS Table**

**Purpose:** GPS location history with geofencing data

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing record ID |
| location_id | TEXT | UNIQUE NOT NULL | Unique location identifier |
| timestamp | DATETIME | NOT NULL | When location was recorded |
| unix_ts | INTEGER | NOT NULL (INDEXED) | Unix timestamp |
| latitude | REAL | NOT NULL (INDEXED) | GPS latitude (-90 to 90) |
| longitude | REAL | NOT NULL (INDEXED) | GPS longitude (-180 to 180) |
| altitude | REAL | NULL | Altitude in meters (if available) |
| accuracy | REAL | NULL | GPS accuracy in meters (±5m typical) |
| speed | REAL | NULL | Speed in m/s |
| location_json | TEXT | NOT NULL | Full location object as JSON |
| geohash | TEXT | NULL (INDEXED) | Geohash for spatial queries |
| is_home | INTEGER | 0/1 | Inside home geofence? |
| is_work | INTEGER | 0/1 | Inside work geofence? |
| dwell_time_minutes | INTEGER | NULL | How long spent at this location |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Indexes:**
- idx_timestamp
- idx_location (composite: latitude, longitude)
- idx_geohash

**Example Record:**
```
location_id: "loc_2024_05_06_12_00_23"
timestamp: "2024-05-06T12:00:23.456Z"
latitude: 14.5995
longitude: 120.9842
altitude: 12.5
accuracy: 8.0
speed: 1.2
geohash: "wqdzc"
is_home: 0
is_work: 0
address: "Paterno St, Quezon City"
```

**Retention:** 7 days rolling

---

### **2.3 BATTERY_STATUS Table**

**Purpose:** Track battery voltage, current, health over time

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| timestamp | DATETIME | NOT NULL | When reading was taken |
| unix_ts | INTEGER | NOT NULL (INDEXED) | Unix timestamp |
| voltage | REAL | NOT NULL | Battery voltage in volts (0-5V) |
| current | INTEGER | NULL | Current in milliamps (0-3000mA) |
| percentage | INTEGER | 0-100 (INDEXED) | Battery percentage |
| temperature | REAL | NULL | Battery temperature in Celsius |
| health_status | TEXT | good/warning/critical | Battery health assessment |
| status_json | TEXT | NOT NULL | Complete status object |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Health Status Rules:**
- Good: >80% percentage, voltage 4.5-5V, temp <45°C
- Warning: 20-80% percentage, voltage 3.5-4.5V, temp 45-55°C
- Critical: <20% percentage, voltage <3.5V, temp >55°C

**Example Record:**
```
timestamp: "2024-05-06T12:00:00.000Z"
voltage: 4.8
current: 2100
percentage: 85
temperature: 42.5
health_status: "good"
status_json: {
  "voltage_v": 4.8,
  "current_ma": 2100,
  "percentage": 85,
  "health": "good",
  "estimated_runtime_minutes": 185
}
```

**Retention:** 7 days rolling
**Update Frequency:** Every 30 seconds

---

### **2.4 COMMANDS Table**

**Purpose:** Log all commands sent to ESP32 (vibration, buzzer, messages)

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| command_id | TEXT | UNIQUE NOT NULL | Unique command identifier |
| timestamp | DATETIME | NOT NULL | When command was issued |
| command_type | TEXT | NOT NULL | vibrate/buzz/message/speak |
| params_json | TEXT | NOT NULL | JSON: {intensity, frequency_hz, text, duration_ms} |
| sent_to_esp32 | INTEGER | 0/1 | Was command successfully sent? |
| ack_received | INTEGER | 0/1 | Did ESP32 acknowledge? |
| execution_time_ms | INTEGER | NULL | How long did execution take? |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Command Types:**

| Type | Parameters | Example |
|------|-----------|---------|
| vibrate | intensity (0-255), duration_ms | {intensity: 255, duration_ms: 500} |
| buzz | frequency_hz (100-5000), duration_ms | {frequency_hz: 2500, duration_ms: 500} |
| message | text (0-500 chars), priority | {text: "Slow down", priority: "high"} |
| speak | text, rate | {text: "Battery warning", rate: 150} |

**Example Record:**
```
command_id: "cmd_2024_05_06_12_00_45_001"
timestamp: "2024-05-06T12:00:45.123Z"
command_type: "vibrate"
params_json: {
  "intensity": 255,
  "duration_ms": 500,
  "pattern": "single_pulse"
}
sent_to_esp32: 1
ack_received: 1
execution_time_ms: 45
```

**Retention:** 7 days rolling

---

### **2.5 MESSAGES Table**

**Purpose:** Store incoming TTS messages from caregiver

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| message_id | TEXT | UNIQUE NOT NULL | Unique message identifier |
| timestamp | DATETIME | NOT NULL | When message was received |
| text | TEXT | NOT NULL (≤500 chars) | Message text to be spoken |
| priority | TEXT | low/normal/high | Message priority |
| tts_engine | TEXT | pyttsx3/other | Which TTS engine used |
| estimated_speak_time_ms | INTEGER | NULL | Estimated duration |
| delivered | INTEGER | 0/1 | Was message played? |
| delivered_at | DATETIME | NULL | When message was played |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Priority Impact:**
- Low: Spoken at normal rate (150 wpm)
- Normal: Spoken at normal rate
- High: Spoken at faster rate (180 wpm)

**Example Record:**
```
message_id: "msg_2024_05_06_12_00_50_001"
timestamp: "2024-05-06T12:00:50.000Z"
text: "Slow down, there's a car ahead"
priority: "high"
tts_engine: "pyttsx3"
estimated_speak_time_ms: 3200
delivered: 1
delivered_at: "2024-05-06T12:00:51.200Z"
```

**Retention:** 7 days rolling

---

### **2.6 ALERTS Table**

**Purpose:** Log all high-level alerts (emergencies, proximity, etc.)

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| alert_id | TEXT | UNIQUE NOT NULL | Unique alert identifier |
| timestamp | DATETIME | NOT NULL (INDEXED) | When alert occurred |
| alert_type | TEXT | proximity/collision/fall/obstacle | Type of alert |
| severity | TEXT | low/medium/high/critical | Alert severity level |
| detection_id | TEXT | FOREIGN KEY | Reference to DETECTIONS record |
| location_latitude | REAL | NULL | Latitude when alert occurred |
| location_longitude | REAL | NULL | Longitude when alert occurred |
| alert_json | TEXT | NOT NULL | Complete alert details |
| acknowledged | INTEGER | 0/1 | Was alert acknowledged? |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Alert Types:**
- proximity: Object within critical distance
- collision: Imminent collision detected
- fall: Fall detected (via IMU)
- obstacle: Generic obstacle detected

**Example Record:**
```
alert_id: "alert_2024_05_06_12_00_23_001"
timestamp: "2024-05-06T12:00:23.456Z"
alert_type: "proximity"
severity: "high"
location_latitude: 14.5995
location_longitude: 120.9842
alert_json: {
  "type": "proximity",
  "object_class": "car",
  "distance_m": 1.5,
  "confidence": 0.92,
  "vibration_pattern": "double_pulse",
  "buzzer_frequency_hz": 1000
}
```

**Retention:** 30 days (longer than detections for analysis)

---

### **2.7 SESSIONS Table**

**Purpose:** Track usage sessions (walk sessions, trip summaries)

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| session_id | TEXT | UNIQUE NOT NULL | Unique session identifier |
| start_time | DATETIME | NOT NULL (INDEXED) | Session start timestamp |
| end_time | DATETIME | NULL | Session end timestamp |
| duration_minutes | INTEGER | NULL | Total session duration |
| distance_km | REAL | NULL | Total distance traveled |
| detection_count | INTEGER | >=0 | Total detections in session |
| alert_count | INTEGER | >=0 | Total alerts in session |
| metadata_json | TEXT | NULL | Additional session data |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Example Record:**
```
session_id: "session_2024_05_06_12_00"
start_time: "2024-05-06T12:00:00.000Z"
end_time: "2024-05-06T12:45:30.000Z"
duration_minutes: 45
distance_km: 2.4
detection_count: 847
alert_count: 12
metadata_json: {
  "start_location": "Home",
  "end_location": "Work",
  "avg_speed_mps": 0.88,
  "top_objects": ["person", "car", "bicycle"]
}
```

**Retention:** 30 days

---

### **2.8 GEOFENCES Table**

**Purpose:** Store geofence boundaries (home, work, etc.)

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| geofence_id | TEXT | UNIQUE NOT NULL | Unique geofence identifier |
| name | TEXT | NOT NULL (INDEXED) | Geofence name (Home, Work) |
| latitude | REAL | NOT NULL | Center latitude |
| longitude | REAL | NOT NULL | Center longitude |
| radius_m | REAL | NOT NULL | Radius in meters |
| enabled | INTEGER | 0/1 | Is geofence active? |
| created_at | DATETIME | DEFAULT NOW | Creation timestamp |

**Example Record:**
```
geofence_id: "geo_home_001"
name: "Home"
latitude: 14.5995
longitude: 120.9842
radius_m: 100
enabled: 1
```

**Retention:** Permanent (user-defined)

---

### **2.9 SENSOR_HEALTH Table**

**Purpose:** Track sensor operational status

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| timestamp | DATETIME | NOT NULL | When status was checked |
| camera_ok | INTEGER | 0/1 | Camera operational? |
| gps_ok | INTEGER | 0/1 | GPS operational? |
| lidar_ok | INTEGER | 0/1 | LIDAR operational? |
| imu_ok | INTEGER | 0/1 | IMU operational? |
| ultrasonic1_ok | INTEGER | 0/1 | Overhead ultrasonic OK? |
| ultrasonic2_ok | INTEGER | 0/1 | Down ultrasonic OK? |
| esp32_ok | INTEGER | 0/1 | ESP32 communication OK? |
| cpu_temp_c | REAL | NULL | CPU temperature |
| uptime_seconds | INTEGER | NULL | System uptime |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Check Frequency:** Every 60 seconds

**Example Record:**
```
timestamp: "2024-05-06T12:00:00.000Z"
camera_ok: 1
gps_ok: 1
lidar_ok: 1
imu_ok: 1
ultrasonic1_ok: 1
ultrasonic2_ok: 1
esp32_ok: 1
cpu_temp_c: 42.5
uptime_seconds: 86400
```

**Retention:** 30 days

---

### **2.10 ELECTRICAL_LOG Table**

**Purpose:** Electrical performance logging for analysis

**Fields:**

| Field | Type | Constraints | Description |
|-------|------|-----------|-------------|
| id | INTEGER | PRIMARY KEY AUTO | Auto-incrementing ID |
| timestamp | DATETIME | NOT NULL (INDEXED) | When logged |
| battery_voltage_v | REAL | NOT NULL | Battery voltage |
| battery_current_ma | INTEGER | NULL | Current consumption |
| battery_percentage | INTEGER | 0-100 | Battery % |
| rpi_temp_c | REAL | NULL | RPi CPU temperature |
| esp32_temp_c | REAL | NULL | ESP32 temperature |
| wifi_signal_strength_db | INTEGER | NULL | WiFi signal (-100 to 0 dBm) |
| detection_fps | REAL | NULL | Current FPS |
| inference_time_ms | INTEGER | NULL | Average inference time |
| memory_usage_mb | INTEGER | NULL | Total RAM used |
| memory_usage_percent | REAL | NULL | Percentage of 8GB used |
| uptime_seconds | INTEGER | NULL | System uptime |
| created_at | DATETIME | DEFAULT NOW | Record creation time |

**Update Frequency:** Every 30 seconds

**Example Record:**
```
timestamp: "2024-05-06T12:00:00.000Z"
battery_voltage_v: 4.8
battery_current_ma: 2100
battery_percentage: 85
rpi_temp_c: 42.5
esp32_temp_c: 38.2
wifi_signal_strength_db: -45
detection_fps: 5.8
inference_time_ms: 175
memory_usage_mb: 6400
memory_usage_percent: 78.1
uptime_seconds: 86400
```

**Retention:** 7 days rolling

---

### **2.11 DATABASE_VIEWS**

**Purpose:** Pre-calculated summaries for quick queries

#### **View: v_daily_summary**

**Purpose:** Daily aggregate statistics

**Columns:**
- date (DATE)
- detection_count (COUNT)
- alert_count (COUNT)
- location_fixes (COUNT)
- distance_km (REAL)
- session_count (INTEGER)
- top_objects (TEXT array)

**Update:** Daily at 2 AM

#### **View: v_hourly_summary**

**Purpose:** Hourly aggregate statistics

**Columns:**
- hour (DATETIME)
- detection_count
- alert_count
- avg_fps
- battery_avg_percent
- temperature_avg

---

## **3. Cloud Storage Architecture (Firestore, )**

### **3.1 Firestore Collections Structure**

```
sticks/
├── {stick_id}/
│   ├── metadata (document)
│   ├── latest_status (document)
│   ├── daily_summary/ (collection)
│   │   └── {date}/ (documents)
│   ├── hourly_stats/ (collection)
│   ├── location_history/ (collection)
│   │   └── {date}/ (subcollection)
│   ├── alerts/ (collection)
│   │   └── {date}/ (subcollection)
│   └── sync_log/ (collection)
│
users/
├── {user_id}/
│   ├── profile (document)
│   ├── linked_sticks (document)
│   ├── preferences (document)
│   ├── notification_settings (document)
│   ├── activity_log/ (collection)
│   └── messages/ (collection)
│
emergencies/
├── {emergency_id}/ (document)
│
geofences/
├── {user_id}/
│   ├── {geofence_id}/ (documents)
│
analytics/
├── daily_summary/ (collection)
└── hourly_stats/ (collection)
```

### **3.2 Firestore Document Schemas**

#### **sticks/{stick_id}/metadata**

```
Field               Type        Description
stick_id            String      Unique stick identifier
friendly_name       String      User-friendly name ("Dad's Stick")
owner_id            String      Owner user ID
authorized_users    Array       List of user IDs with access
firmware_version    String      Current firmware version
hardware_version    String      Hardware version
created_at          Timestamp   Creation date
last_sync           Timestamp   Last cloud sync
status              String      active/inactive/lost
settings            Map         Configuration settings
```

#### **sticks/{stick_id}/latest_status**

```
Field                   Type        Description
is_online               Boolean     Currently online?
battery_percentage      Integer     Current battery %
battery_health          String      good/warning/critical
location                Map         {latitude, longitude, accuracy_m, address, timestamp}
last_detection          Map         {class, distance_m, confidence, timestamp}
memory_usage_percent    Real        RAM usage %
temperature_c           Real        CPU temperature
last_updated            Timestamp   When this record was updated
```

#### **sticks/{stick_id}/daily_summary/{date}**

```
Field               Type        Description
date                String      ISO date (YYYY-MM-DD)
distance_km         Real        Total distance traveled
duration_minutes    Integer     Total active time
detection_count     Integer     Total detections
alert_count         Integer     Total alerts
session_count       Integer     Number of sessions
top_objects         Array       Top 5 detected objects
geofence_visits     Map         {geofence_name: count}
battery_drain_percent Integer    Battery used today
created_at          Timestamp   Creation timestamp
```

#### **users/{user_id}/profile**

```
Field           Type        Description
email           String      User email
name            String      Full name
phone           String      Phone number
role            String      caregiver/doctor/healthcare_worker
language        String      Preferred language
timezone        String      User timezone
avatar_url      String      Profile picture URL
created_at      Timestamp   Account creation
updated_at      Timestamp   Last update
is_active       Boolean     Account active?
```

#### **users/{user_id}/linked_sticks**

```
Field                   Type        Description
{stick_id}              Map         Stick linking info
  ├─ stick_id           String      Stick identifier
  ├─ stick_name         String      Display name
  ├─ paired_at          Timestamp   When paired
  ├─ permission_level   String      full/view_only/emergency_only
  ├─ is_primary         Boolean     Primary caregiver?
  └─ notifications      Boolean     Notifications enabled?
```

#### **emergencies/{emergency_id}**

```
Field                   Type        Description
emergency_id            String      Unique emergency ID
stick_id                String      Which stick triggered
user_id                 String      Which user
triggered_at            Timestamp   When SOS pressed
triggered_by            String      manual_press/fall_detected
location                Map         {latitude, longitude, address}
status                  String      active/resolved/ignored
acknowledged_by         String      Which user acknowledged
acknowledged_at         Timestamp   When acknowledged
resolved_at             Timestamp   When resolved
emergency_contacts_notified Array   User IDs notified
sms_sent                Boolean     SMS sent?
call_initiated          Boolean     Call made?
notes                   String      Additional notes
```

---

## **4. CSV Export Format (Electrical Logging)**

### **4.1 CSV File Structure**

**File Location:** `/home/pi/data/electrical_parameters.csv`
**Update Frequency:** Every 30 seconds
**Export Format:** RFC 4180 compliant

**CSV Headers:**
```
timestamp,battery_voltage_v,battery_current_ma,battery_percentage,
rpi_temp_c,esp32_temp_c,wifi_signal_strength_db,detection_fps,
inference_time_ms,memory_usage_mb,uptime_seconds
```

**Example Rows:**
```
2024-05-06T12:00:00.000Z,4.80,2100,85,42.5,38.2,-45,5.8,175,6400,86400
2024-05-06T12:00:30.000Z,4.79,2150,85,43.1,38.5,-46,5.7,180,6420,86430
2024-05-06T12:01:00.000Z,4.78,2200,84,43.5,38.8,-44,5.9,172,6440,86460
```

### **4.2 Excel Export Format**

**Spreadsheet Name:** `electrical_logs_YYYY-MM-DD.xlsx`

**Tabs:**
1. **Data Sheet:** Raw CSV data with formatting
2. **Battery Chart:** Voltage over time (line chart)
3. **Temperature Chart:** CPU and ESP32 temp (line chart)
4. **FPS Chart:** Detection FPS consistency (line chart)
5. **Memory Chart:** RAM usage trend (line chart)
6. **Summary:** Daily/weekly statistics

**Formatting:**
- Headers: Bold white text on blue background
- Numbers: 2 decimal places for floats
- Dates: ISO 8601 format
- Charts: Auto-scaling axis, trend lines

---

## **5. Data Relationships & Integrity**

### **5.1 Foreign Key Relationships**

```
COMMANDS → None (standalone)
  └─ Records ESP32 interactions

MESSAGES → None (standalone)
  └─ Received from caregiver app

DETECTIONS → ALERTS (optional)
  └─ Detection can trigger alert

LOCATIONS → GEOFENCES (spatial join)
  └─ Location checked against all geofences

ALERTS → LOCATIONS (by lat/lon)
  └─ Alert stores location context

SESSIONS → DETECTIONS (by timestamp range)
  └─ Session aggregates detections

SESSIONS → LOCATIONS (by timestamp range)
  └─ Session aggregates locations

BATTERY_STATUS → None
  └─ Standalone electrical data

SENSOR_HEALTH → None
  └─ Standalone health check
```

### **5.2 Data Consistency Rules**

**Uniqueness Constraints:**
- frame_id: Unique (one detection per frame)
- location_id: Unique (one location per GPS fix)
- message_id: Unique (one message per send)
- command_id: Unique (one command per trigger)
- alert_id: Unique (one alert per occurrence)
- session_id: Unique (one session per start)
- geofence_id: Unique (one geofence per definition)

**Referential Integrity:**
- All timestamps must be valid ISO 8601 format
- All coordinates must be valid (lat: -90 to 90, lon: -180 to 180)
- All percentages must be 0-100
- All temperatures must be realistic (-10°C to 80°C)
- All distances must be >= 0

**Data Validation:**
- Battery percentage cannot exceed 100%
- Accuracy cannot be negative
- Detection confidence must be 0-1
- Vibration intensity must be 0-255
- Buzzer frequency must be 100-5000 Hz

---

## **6. Data Lifecycle**

### **6.1 Retention Policy**

| Table | Retention | Reason |
|-------|-----------|--------|
| DETECTIONS | 7 days | Real-time operational data |
| LOCATIONS | 7 days | Location history for user |
| BATTERY_STATUS | 7 days | Battery trends |
| COMMANDS | 7 days | Recent command history |
| MESSAGES | 7 days | Message history |
| ALERTS | 30 days | Longer analysis period |
| SESSIONS | 30 days | Activity tracking |
| GEOFENCES | Permanent | User-defined |
| SENSOR_HEALTH | 30 days | Diagnostics |
| ELECTRICAL_LOG | 7 days | Recent performance |

### **6.2 Cleanup Schedule**

**Daily (2:00 AM UTC):**
- Delete DETECTIONS records older than 7 days
- Delete LOCATIONS records older than 7 days
- Delete BATTERY_STATUS records older than 7 days
- Delete COMMANDS records older than 7 days
- Delete MESSAGES records older than 7 days
- Delete ELECTRICAL_LOG records older than 7 days
- Run VACUUM to reclaim space

**Weekly (Sunday 3:00 AM UTC):**
- Delete ALERTS records older than 30 days
- Delete SESSIONS records older than 30 days
- Delete SENSOR_HEALTH records older than 30 days
- Archive weekly summary to Firestore

**Monthly (1st of month, 4:00 AM UTC):**
- Export all data to Firestore ()
- Verify data integrity
- Generate monthly report

### **6.3 Database Size Management**

**Current Size Estimates:**

| Table | Records/Day | Size/Day | 7-Day Size |
|-------|-------------|----------|-----------|
| DETECTIONS | 432,000 | ~15MB | ~105MB |
| LOCATIONS | 17,280 | ~1.5MB | ~10MB |
| BATTERY_STATUS | 2,880 | ~150KB | ~1MB |
| COMMANDS | ~100 | ~50KB | ~350KB |
| MESSAGES | ~50 | ~25KB | ~175KB |
| ALERTS | ~50 | ~50KB | ~350KB |
| SESSIONS | ~3 | ~1KB | ~20KB |
| ELECTRICAL_LOG | 2,880 | ~200KB | ~1.4MB |
| Other | - | ~100KB | ~700KB |
| **TOTAL** | - | **~17MB** | **~120MB** |

**Target:** Keep database <32MB (typical 7-day window)

---

## **7. Data Access Patterns**

### **7.1 Common Queries**

**Get Latest Detection:**
```
Query: SELECT * FROM detections
       WHERE alert_triggered = 1
       ORDER BY timestamp DESC
       LIMIT 1
Result: ~1ms
Used by: Real-time alert status
```

**Get Current Location:**
```
Query: SELECT * FROM locations
       ORDER BY timestamp DESC
       LIMIT 1
Result: <1ms
Used by: Mobile app location tab
```

**Get Today's Distance:**
```
Query: SELECT SUM(distance_km) FROM sessions
       WHERE DATE(start_time) = CURDATE()
Result: ~10ms
Used by: Daily activity summary
```

**Get Hourly Detection Stats:**
```
Query: SELECT COUNT(*) FROM detections
       WHERE timestamp >= NOW() - INTERVAL '1 hour'
Result: ~5ms
Used by: Analytics dashboard
```

**Get Battery Trend (24 hours):**
```
Query: SELECT timestamp, percentage FROM battery_status
       WHERE timestamp >= NOW() - INTERVAL '24 hours'
       ORDER BY timestamp
Result: ~20ms
Used by: Battery chart in app
```

### **7.2 Index Strategy**

**Indexes Created:** 8 total

| Table | Index | Purpose |
|-------|-------|---------|
| detections | idx_timestamp | Time-range queries |
| detections | idx_unix_ts | Fast lookups |
| detections | idx_alert | Filter by alert status |
| locations | idx_timestamp | Time queries |
| locations | idx_location | Spatial queries (lat/lon) |
| locations | idx_geohash | Geofence lookups |
| battery_status | idx_percentage | Filter by battery level |
| alerts | idx_timestamp | Alert history |

**Index Impact:**
- Write performance: -5% (slightly slower inserts)
- Read performance: +95% (much faster queries)
- Storage: +2MB (small overhead)

---

## **8. Data Synchronization ()**

### **8.1 Sync Strategy**

**Pull-based (Not real-time):**
- Mobile app polls API every 5 seconds for location
- Stick syncs to cloud every 30 minutes
- No continuous connection required
- Battery-friendly approach

**Push-based (Emergency):**
- SOS button → immediate cloud notification
- Emergency → all caregivers notified within 2 seconds
- Critical alerts → pushed immediately

**Batch Operations:**
- Detections: Aggregated hourly before cloud sync
- Locations: Hourly summaries sent to cloud
- Battery: Daily statistics sent
- Alerts: Sent immediately to cloud

### **8.2 Conflict Resolution**

**Timestamp Priority:** Cloud receives multiple sources
- Local timestamp (RPi 5 system clock) is source of truth
- Cloud stores timestamp exactly as received
- No retry/reconciliation (append-only)

**Data Completeness:** Stick must have local copy
- Always sync local-first
- Cloud is backup only
- Never delete local data based on cloud

---

## **Appendix: Database Management**

### **A.1 Backup Strategy**

**Local Backup (on stick):**
- Automatic daily backup to `/home/pi/backups/`
- Keep last 3 backups only
- Compressed (gzip)

**Cloud Backup ():**
- Daily export to Firestore
- Keep 30 days of daily snapshots
- Can restore any day in past month

**Disaster Recovery:**
- Stick loses data: Restore from last 24h local backup
- Complete stick failure: Restore from cloud backup (30 days)
- Cloud backup corrupted: Local backup is source of truth

### **A.2 Schema Versioning**

**Current Version:** 1.1
**Upgrade Path:** Migrations stored in `/home/pi/migrations/`

**Future Changes:**
- Version 1.2: Add motion tracking table
- Version 1.3: Add ML model inference logs
- Version 2.0: Add predictive analytics tables
