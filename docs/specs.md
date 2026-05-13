# Smart Stick Technical Specifications v1.1


---

## **1. System Architecture Overview**

### **1.1 High-Level System**

```
┌─────────────────────────────────────────────────────────┐
│         SMART STICK COMPLETE ECOSYSTEM                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  WEARABLE DEVICE (Stick Hardware)                      │
│  ├─ Autonomous offline operation                       │
│  ├─ Real-time detection (5-6 FPS)                     │
│  ├─ Multiple output methods (vibration + audio)        │
│  └─ Local storage (SQLite + CSV logging)               │
│           ↓                                             │
│    Optional: WiFi/BLE Connection                       │
│           ↓                                             │
│  CAREGIVER MOBILE APP (React Native)                   │
│  ├─ 5 tabs: Home, Location, Find, Message, Video      │
│  ├─ Real-time status monitoring                        │
│  ├─ Remote controls (vibrate, sound, messages)         │
│  └─ Local caching (works offline)                      │
│           ↓                                             │
│    Optional: Cloud Sync (Firebase, )            │
│           ↓                                             │
│  CLOUD BACKEND (Firebase)                              │
│  ├─ Real-time database (Firestore)                     │
│  ├─ Authentication (Firebase Auth)                     │
│  ├─ Push notifications (FCM)                           │
│  └─ Analytics & backup ()                       │
│                                                         │
└─────────────────────────────────────────────────────────┘

Data Flow:
  Sensors → Detection → Alerts → Local Storage
                          ↓
                    Caregiver App (polling)
                          ↓
                    Cloud (optional async sync)
```

### **1.2 Three-Layer Architecture**

**Layer 1: Sensor Input**
- Camera (USB) → YOLO input
- GPS (UART) → Location data
- LIDAR (I2C) → Forward distance
- Ultrasonic #1 (GPIO) → Overhead detection
- Ultrasonic #2 (GPIO) → Step/elevation detection
- IMU (I2C) → Orientation
- Battery (ADC) → Power monitoring

**Layer 2: Processing (RPi 5)**
- Detection loop (5-6 FPS)
- Alert logic (vibration + audio patterns)
- Location tracking
- TTS audio synthesis
- SQLite storage
- FastAPI REST API

**Layer 3: Output & Communication**
- Vibration motor (GPIO PWM)
- Buzzer (GPIO PWM with frequency control)
- Audio jack (3.5mm stereo)
- Bluetooth earpiece (optional)
- WiFi/BLE connectivity

---

## **2. Hardware Architecture**

### **2.1 Complete Hardware Stack**

**Compute:**
- Raspberry Pi 5 (8GB RAM, 8 CPU cores)
- ESP32 WROOM-32 (haptics co-processor)

**Sensors:**
- Camera: Raspberry Pi Camera Module 3 NoIR (12MP, IMX708, 120° FOV)
- GPS: GY-GPS6MV2 (NEO-6M, 9600 baud UART)
- LIDAR: TF Mini S (0.3-40m range, I2C address 0x10)
- Ultrasonic #1: HC-SR04 (overhead detection)
- Ultrasonic #2: HC-SR04 (step/down detection)
- IMU: GY-ICM20948V2 (9-axis, I2C address 0x68)
- Battery: 10Ah lithium (USB-C charging)

**Output Devices:**
- Vibration motor (3V, GPIO 26 PWM)
- Buzzer (24-12V, GPIO 27 PWM, 100-5000 Hz)
- Audio jack (3.5mm stereo)
- Bluetooth earpiece (via RPi 5 Bluetooth)

### **2.2 Pin Assignments (RPi 5)**

```
GPIO 2 (SDA)  → I2C Bus: LIDAR (0x10), IMU (0x68)
GPIO 3 (SCL)  → I2C Bus (same as above)
GPIO 14 (TX)  → UART to ESP32 (115200 baud)
GPIO 15 (RX)  → UART from ESP32 (115200 baud)

GPIO 23 → Ultrasonic #1 Trigger (overhead)
GPIO 24 → Ultrasonic #2 Trigger (down)
GPIO 25 ← Ultrasonic #1 Echo
GPIO 27 ← Ultrasonic #2 Echo

GPIO 26 (PWM) → Vibration motor control
GPIO 27 (PWM) → Buzzer tone generation

USB Port 1 → Camera Module 3
USB Port 2 → GPS Module (via UART adapter)
```

### **2.3 Sensor Positioning on Stick**

```
TOP (30cm):
  ├─ Ultrasonic #1 (pointing UP)
  │   └─ Detects ceiling, branches, overhangs
  └─ Camera (forward-facing)
      └─ For YOLO detection

MIDDLE (15cm):
  ├─ LIDAR (forward-facing)
  │   └─ Detects obstacles ahead (0.3-40m)
  ├─ IMU (orientation sensing)
  └─ GPS (antenna facing up)

BOTTOM (0cm):
  ├─ Ultrasonic #2 (pointing DOWN/BACK)
  │   └─ Detects stairs, elevation changes
  └─ Buzzer + Vibration motor
```

---

## **3. Alert System Design**

### **3.1 Vibration Feedback Patterns**

**Five Distinct Patterns (User Distinguishes by Touch):**

| Object Type | Pattern Name | Intensity | Duration | Feel Description |
|-------------|------------|-----------|----------|------------------|
| Person | Single Pulse | 255 max | 200ms | Sharp jab, immediate stop |
| Car/Vehicle | Double Pulse | 200 | 150ms × 2 (100ms gap) | Rhythmic bump-bump |
| Bicycle/Motorcycle | Triple Pulse | 180 | 100ms × 3 (50ms gap) | Quick vibration burst |
| Stairs/Overhead | Steady Vibration | 220 | 500ms continuous | Sustained rumble |
| Unknown Obstacle | Slow Pulse | 150 | 300ms (200ms gap) | Gentle recurring beat |

**Design Principles:**
- Intensity inversely proportional to distance (closer = stronger)
- Rate limiting: 2-5 second cooldown per object class
- Vibration provides advance warning (0.5-1m before impact)
- Different enough that user can feel distinction even with gloves

### **3.2 Buzzer Tone System**

**Eight Distinct Frequencies for Different Alerts:**

| Alert Type | Frequency | Duration | Pattern | Use Case |
|-----------|-----------|----------|---------|----------|
| Standard Object Alert | 1000 Hz | 200ms | Single tone | Person/car/obstacle detected |
| Elevation Alert | 1500 Hz | 300ms | Single tone | Stairs, low ceiling detected |
| Emergency SOS | 2500 Hz | 500ms | Repeating (500ms on/200ms off) | SOS button pressed |
| Battery Warning | 800 Hz | 100ms | Triple beep (50ms gaps) | Battery at 50/25/10% |
| Message Received | 2000 Hz | 300ms | Single tone | New TTS message arriving |
| Good WiFi Signal | 1200 Hz | 100ms | Single beep | Strong connection |
| Weak WiFi Signal | 1000 Hz | 200ms | Slow beep | Weak connection |
| Disconnected | 800 Hz | 500ms | Long beep | WiFi disconnected |

**Design Principles:**
- Each frequency visibly distinct (400+ Hz difference between critical alerts)
- SOS tone (2500 Hz) clearly different from all others
- Battery warning (800 Hz) uses pattern (beep-beep-beep) for recognition
- User learns to associate frequency with alert type

### **3.3 Combined Alert Response**

**When Overhead Obstacle Detected (Example):**
1. **Vibration:** Steady vibration (220 intensity, 500ms)
2. **Audio:** Distinct buzzer tone (1500 Hz, 300ms)
3. **Voice (if enabled):** TTS "Low ceiling ahead"
4. **Earpiece:** All audio routes through 3.5mm or Bluetooth
5. **Timing:** User hears AND feels within 100ms of detection

---

## **4. Battery Monitoring & Warnings**

### **4.1 Battery Warning System**

**Three Threshold Warnings:**

| Percentage | Voice Announcement | Buzzer | Frequency |
|------------|-------------------|--------|-----------|
| 50% | "Battery at 50 percent. Consider charging." | 800 Hz × 3 | Once at threshold |
| 25% | "Battery at 25 percent. Charging recommended soon." | 800 Hz × 3 | Once at threshold |
| 10% | "Battery critically low at 10 percent." | 800 Hz × 3 | Once per minute |

**Design Principles:**
- Voice + buzzer combination for redundancy
- Only one announcement per threshold (no repeated alerts)
- Clear, understandable speech
- Audible over ambient noise
- Critical (10%) repeats to emphasize urgency

### **4.2 Battery Life Estimates**

**Expected Runtime by Activity:**

| Scenario | Duration | Power Draw |
|----------|----------|-----------|
| Offline detection + GPS only | 4+ hours | ~2A |
| WiFi on + detection | 3-3.5 hours | ~2.5A |
| Full activity (detection + WiFi + buzzer/vibration) | 2.5-3 hours | ~3A |
| Idle (WiFi only, no detection) | 6+ hours | ~1.5A |

**Estimated Battery: 10Ah at 3.7V = 37Wh**

---

## **5. Audio Output Architecture**

### **5.1 Audio Routing Options**

**Option 1: 3.5mm Audio Jack (Built-in)**
- Direct connection to standard earpiece
- Simple, reliable, no pairing needed
- Always available (no battery needed)
- Recommended for primary use

**Option 2: Bluetooth Earpiece (Wireless)**
- Requires pairing once
- Battery on earpiece (separate charging)
- Freedom of movement
- Recommended for mobility

**Option 3: Both Simultaneously (Advanced)**
- Dual audio output
- Fallback if one fails
- Recommended for critical use

### **5.2 Audio Routing Flow**

```
Audio Sources:
├─ Object detection sounds (buzzer tone synthesized)
├─ TTS messages (text-to-speech conversion)
├─ Battery warnings (1000 Hz + voice)
└─ Feedback sounds (confirmation beeps)

     ↓ (All route through)

Audio Engine:
├─ Volume control (0-100%)
├─ Frequency generation (100-5000 Hz)
└─ TTS synthesis (pyttsx3 or alternative)

     ↓ (Routes to)

Output Devices (Priority):
1. 3.5mm audio jack (if connected)
2. Bluetooth earpiece (if paired)
3. Speaker fallback (if both unavailable)
```

---

## **6. Mobile App Architecture**

### **6.1 Five App Tabs with Features**

**Tab 1: HOME - Status & Battery**
- Device name display ("Dad's Stick")
- Online/Offline status badge (color-coded)
- Battery card:
  - Large percentage (85%)
  - Progress bar
  - Health status (Good/Warning/Critical)
  - Voltage reading (4.8V)
  - Estimated runtime (185 minutes)
- Last sync timestamp
- Quick links to other tabs

**Tab 2: LOCATION - Real-Time Map**
- Google Maps integration
- Red pin showing stick position
- Accuracy radius circle (±5m)
- Reverse geocoded address
- Refresh button
- View history (shows path from last 24h)
- Distance traveled today

**Tab 3: FIND - Remote Control**
- Same map as Tab 2
- Vibrate Stick button (green)
  - Sends max vibration (500ms)
  - Visual feedback "Vibrating..."
- Play Sound button (orange)
  - Sends SOS tone (2500 Hz repeating)
  - Visual feedback "Sound playing..."
- Confirmation message appears after command
- Can trigger repeatedly

**Tab 4: MESSAGE - Text-to-Speech**
- Quick message templates (6 buttons):
  1. "I'm on my way!"
  2. "Stay where you are"
  3. "Call me when you can"
  4. "Are you okay?"
  5. "I'll be there soon"
  6. "Take a break"
- Custom message input (max 500 chars)
- Character counter
- Send button
- Estimated speak time shown
- Message history (last 20 messages)
- Delivery status (Queued/Sent/Delivered)

**Tab 5: VIDEO - Live Camera**
- Large camera feed area
- Start Stream button (green)
- Stop Stream button (gray/disabled when not streaming)
- FPS counter (shows detection rate)
- Last frame timestamp
- Manual refresh button (for polling mode)
- Status indicator (streaming/cached/offline)

### **6.2 App Features Summary**

| Feature | Status | Implementation |
|---------|--------|-----------------|
| Battery monitoring | Required | Display %, voltage, health, runtime |
| Location tracking | Required | Google Maps, real-time updates (every 5s) |
| Find my stick | Required | Remote vibrate & sound with SOS tone |
| Message sending | Required | Quick templates + custom text, TTS playback |
| Live camera | Required | Polling mode (MVP), WebSocket streaming () |
| Offline support | Required | Local caching, works without WiFi |
| Push notifications |  | Firebase Cloud Messaging |
| Analytics |  | Daily/weekly summaries |
| Data export |  | CSV/PDF download |

---

## **7. Data Storage Architecture**

### **7.1 SQLite Database Schema (Local, RPi)**

**Detections Table:**
- frame_id (unique)
- timestamp
- detection_json (YOLO results)
- alert_triggered (boolean)
- object_count

**Locations Table:**
- location_id (unique)
- timestamp
- latitude, longitude
- accuracy (meters)
- geohash (for indexing)
- is_home, is_work (boolean)

**Battery Status Table:**
- timestamp
- voltage (volts)
- current (milliamps)
- percentage (0-100)
- temperature (celsius)
- health_status (good/warning/critical)

**Commands Table (ESP32 Communication):**
- command_id (unique)
- command_type (vibrate/buzz/message/speak)
- params_json
- sent_to_esp32
- ack_received
- execution_time_ms

**Messages Table:**
- message_id (unique)
- timestamp
- text (up to 500 chars)
- priority (low/normal/high)
- delivered (boolean)
- delivered_at

**Alerts Table:**
- alert_id (unique)
- timestamp
- alert_type (proximity/collision/fall/obstacle)
- severity (low/medium/high/critical)
- location (lat/lon)

**Sessions Table:**
- session_id (unique)
- start_time, end_time
- duration_minutes
- distance_km
- detection_count
- alert_count

**Electrical Log Table:**
- timestamp
- voltage_v
- current_ma
- battery_percentage
- rpi_temp_c
- esp32_temp_c
- memory_usage_mb
- wifi_signal_strength_db
- detection_fps
- uptime_seconds

### **7.2 Electrical Logging (CSV Export)**

**CSV Headers:**
```
timestamp, battery_voltage_v, battery_current_ma, battery_percentage,
rpi_temp_c, esp32_temp_c, wifi_signal_strength_db, detection_fps,
inference_time_ms, memory_usage_mb, uptime_seconds
```

**Update Frequency:** Every 30 seconds
**Storage Duration:** 7 days rolling
**Export Format:** Excel with charts

### **7.3 Cloud Storage (Firebase, )**

**Firestore Collections:**
- `sticks/{stick_id}/metadata` - Device info
- `sticks/{stick_id}/latest_status` - Current state
- `sticks/{stick_id}/daily_summary/{date}` - Day aggregates
- `sticks/{stick_id}/location_history/{date}` - GPS locations
- `sticks/{stick_id}/alerts/{date}` - Alert log
- `users/{user_id}/profile` - Caregiver info
- `users/{user_id}/linked_sticks` - Stick assignments
- `emergencies/{emergency_id}` - SOS alerts
- `analytics/{date}` - System-wide stats

---

## **8. API Endpoints**

### **8.1 Complete Endpoint List**

**Detection Endpoints:**
- `GET /api/latest_detections` - Current detections
- `GET /api/detections/history?hours=24` - Historical detections

**Location Endpoints:**
- `GET /api/location` - Current GPS location
- `GET /api/history/location?hours=24` - Location history
- `GET /api/history/location/geojson` - GeoJSON format for maps

**Battery Endpoint:**
- `GET /api/battery` - Current battery status

**Camera Endpoints:**
- `GET /api/latest_frame` - Latest JPEG image
- `GET /api/stream` - WebSocket for real-time stream ()

**Haptics Endpoints:**
- `POST /api/vibrate` - Send vibration command
- `POST /api/buzz` - Send buzzer tone

**Message Endpoints:**
- `POST /api/message` - Send text message (TTS)
- `GET /api/message/history` - Message history

**Health Endpoints:**
- `GET /api/health` - System health status
- `GET /api/status` - Detailed status

**Emergency:**
- `POST /api/emergency/sos` - Trigger SOS

### **8.2 Response Format Example**

**Battery Status Response:**
```
{
  "percentage": 85,
  "voltage": 4.8,
  "current": 2.1,
  "health": "good",
  "runtime_minutes": 185,
  "timestamp": "2024-05-06T12:00:23Z"
}
```

**Location Response:**
```
{
  "latitude": 14.5995,
  "longitude": 120.9842,
  "accuracy_m": 8.0,
  "address": "Paterno St, Quezon City",
  "timestamp": "2024-05-06T12:00:23Z"
}
```

---

## **9. System Constraints & Performance Limits**

### **Performance**

| Constraint | Value | Notes |
|-----------|-------|-------|
| Detection FPS | 5-6 | YOLO Nano on RPi 5 CPU |
| Detection latency | <500ms | Frame to alert vibration |
| GPS update rate | 1 per 5s | 5-second intervals |
| Battery life (offline) | 3-4 hours | Full activity |
| Battery life (WiFi on) | 2.5-3 hours | WiFi + detection |
| Alert response time | <100ms | ESP32 motor activation |
| API response time | <200ms | Local WiFi connection |
| Vibration intensity | 0-255 | Linear scale |
| Buzzer frequency | 100-5000 Hz | PWM-based |
| Memory usage | ~6-7GB | Out of 8GB total |
| Storage (SQLite) | ~32MB max | 7-day rolling window |
| BLE range | ~50m | Line of sight |
| WiFi range | 30-50m | Typical home network |

### **Reliability**

| Metric | Target |
|--------|--------|
| Uptime | 99.5% (no crashes in 24h) |
| MTBF (mean time between failures) | >24 hours |
| False positive rate | <5% |
| Detection accuracy | 85-95% (YOLO Nano) |
| Location accuracy | ±5m outdoor, ±50m urban |
| Vibration consistency | >99% |
| Buzzer frequency accuracy | ±10% |

---

## **10. Testing Strategy**

### **10.1 Unit Testing Areas**

**Sensor Testing:**
- Camera frame capture rate
- GPS lock time and accuracy
- LIDAR distance measurement
- Ultrasonic readings (both units)
- IMU orientation
- Battery voltage/current readings

**Detection Testing:**
- YOLO model inference speed
- Object classification accuracy
- Confidence score reliability
- Multi-object handling
- Frame drop handling

**Alert Testing:**
- Vibration pattern generation (5 patterns)
- Buzzer frequency generation (8 frequencies)
- Pattern distinctness (user can feel difference)
- Frequency distinctness (user can hear difference)
- Rate limiting (cooldowns work)

**Database Testing:**
- SQLite write speed
- Query performance
- Data integrity
- CSV export format
- Cleanup operations (7-day rotation)

### **10.2 Integration Testing**

**Hardware-Software Integration:**
- Camera detection pipeline (capture to alert)
- GPS to SQLite flow
- Sensor to alert (latency testing)
- Battery monitoring accuracy
- Electrical logging completeness

**API Testing:**
- All endpoints return correct data
- Response times <200ms
- Error handling
- Offline caching

**Mobile App Testing:**
- Tab rendering
- Real-time updates
- Offline mode
- API connectivity
- Google Maps integration

**Communication Testing:**
- WiFi API connection
- BLE advertisement
- Message delivery
- Firebase sync ()

### **10.3 User Acceptance Testing**

**Real-World Scenarios:**
- 1km walk with various obstacles
- Alert distinctness testing (vibration patterns)
- Alert distinctness testing (buzzer tones)
- Caregiver receives notifications
- Battery warnings at thresholds
- GPS tracking accuracy
- Message delivery
- Find my stick feature
- Overhead detection (ceiling, branches)
- Stair detection (both up and down)
- Earpiece audio quality

**Performance Benchmarks:**
- Battery drain at various activity levels
- Detection FPS consistency
- Temperature under load
- Memory usage patterns
- WiFi stability

**Safety Testing:**
- SOS button reliability
- Emergency notification delivery
- Location accuracy in emergency
- Data backup integrity

---

## **11. Deployment Architecture**

### **11.1 Stick Deployment (RPi 5)**

**Operating Environment:**
- OS: Raspberry Pi OS (Bookworm)
- Python: 3.10+
- Runtime: ~8GB RAM (out of 8GB available)
- Storage: 64GB microSD
- Battery: 10Ah USB-C

**Service Management:**
- Systemd service for auto-start
- Automatic restart on crash
- Log rotation
- Health monitoring

**Network:**
- WiFi: 2.4GHz preferred (5GHz backup)
- BLE: ESP32 Bluetooth for Find feature
- API Port: 5000 (HTTP)
- CORS enabled for mobile app

### **11.2 Mobile Deployment**

**Platforms:**
- iOS 14+ (React Native)
- Android 10+ (React Native)

**Toolchain:**
- React Native 0.74+ (bare workflow for BLE support)
- TypeScript
- Metro bundler
- Native iOS build via Xcode (or Codemagic / EAS Build on macOS runners)
- Native Android build via Gradle (runs on Windows/macOS/Linux)

**Distribution:**
- : TestFlight (iOS) + APK (Android)
- : Google Play Store
- Phase 3: Apple App Store

**Key Libraries:**
- `react-native-maps` — Google Maps integration
- `react-native-ble-plx` — BLE communication with the stick
- `react-native-geolocation-service` — phone-side location
- `@react-native-async-storage/async-storage` or `react-native-mmkv` — local caching
- `axios` — HTTP client for the FastAPI backend
- `react-native-websocket` — live camera streaming (Phase 2)
- `victory-native` or `react-native-svg-charts` — battery / analytics charts
- `@react-native-firebase/*` — Firebase Auth, Firestore, FCM (Phase 2)

**Key Integrations:**
- Google Maps API
- Firebase ()
- Local storage (AsyncStorage / MMKV)

### **11.3 Cloud Deployment ()**

**Firebase Project:**
- Authentication: Firebase Auth
- Database: Firestore
- Functions: Node.js Cloud Functions
- Messaging: FCM
- Storage: Cloud Storage
- Region: Asia Southeast 1 (Singapore)

**Billing:**
- MVP: $0 (free tier)
- : $5-20/month

---

## **12. Success Metrics & KPIs**

### **Technical Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| Detection latency | <500ms | Stopwatch + log timestamps |
| Battery life | 3-4 hours | Full activity runtime test |
| GPS accuracy | ±5m outdoor | Multiple location captures |
| Uptime | 99.5% | Continuous 24h+ monitoring |
| Vibration distinctness | >90% | User feedback (blindfolded test) |
| Buzzer distinctness | >90% | User feedback (listen test) |
| Location update rate | 1 per 5s | API polling verification |

### **User Experience Metrics**

| Metric | Target | Measurement |
|--------|--------|-------------|
| User confidence | >4/5 stars | Post-walk survey |
| Alert response confidence | >90% | Can user identify obstacle type |
| Message clarity | >95% | TTS understandability |
| Find feature success | 100% | Remote vibrate/sound test |
| Earpiece quality | 5/5 | Audio clarity rating |

### **Business Metrics**

| Metric | Target | Timeline |
|--------|--------|----------|
| MVP completion | 3 weeks |  |
| Beta users | 3-5 | Week 4 |
| Full deployment | 6 months | Production ready |
| Cost per unit | <$200 | Hardware cost |
| Cloud cost | <$20/month | Operating cost |

---

## **13. Open Design Questions**

| Question | Options | Decision |
|----------|---------|----------|
| Audio output default | 3.5mm or Bluetooth | **3.5mm primary, BLE optional** |
| Vibration intensity | Fixed or distance-based | **Distance-based (closer = stronger)** |
| Alert frequency | Constant or adaptive | **Constant patterns + rate limiting** |
| TTS voice | Male/Female/Adjustable | **Male (deeper frequency), adjustable in settings** |
| Camera resolution | 640×480 vs 1280×720 | **640×480 for faster inference** |
| Battery warning repeat | Once per threshold or repeated | **Once per threshold, 10% repeats every minute** |
