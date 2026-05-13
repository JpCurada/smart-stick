# Smart Stick for BVI - Requirements Document v1.1

---

## **1. Project Overview**

**Product:** Smart Stick - An AI-powered wearable device providing real-time obstacle detection, navigation guidance, and caregiver monitoring for blind and visually impaired (BVI) individuals.

**Vision:** Enable BVI users to navigate independently with confidence while giving caregivers peace of mind through real-time monitoring and instant communication.

**Target Users:**
- **Primary:** Blind and visually impaired adults (16+)
- **Secondary:** Caregiver parents, guardians, assistants
- **Tertiary:** Healthcare workers, rehabilitation centers

**Success Metrics:**
- Stick operates 3+ hours on single charge
- Detection latency <500ms (real-time alerts)
- Location accuracy ±5m in urban areas
- Caregiver app shows live location within 10 seconds
- Distinct vibration patterns for different obstacles (user can distinguish via haptic feedback)
- Distinct buzzer tones for different alerts (user can distinguish via audio feedback)
- Battery warnings at 50%, 25%, 10% via voice announcements
- User confidence rating >4/5 after 30-minute walk

---

## **2. User Stories**

### **2.1 Blind User Stories**

#### **US-001: Navigate Independently with Real-Time Alerts**
```
As a blind person with a cane,
I want the stick to detect obstacles ahead in real-time,
So that I can walk confidently without hitting unseen hazards.

Acceptance Criteria:
- [ ] Detects people within 2m distance
- [ ] Detects cars within 3m distance
- [ ] Detects stairs/curbs within 1m distance
- [ ] Detects low ceilings and overhead obstacles
- [ ] Detects stairs (both up and down)
- [ ] Alert latency <500ms (from detection to vibration/sound)
- [ ] Works in daylight and low-light conditions
- [ ] False positive rate <5% (no false alarms on normal walking)
- [ ] Different vibration patterns for different object types

Priority: CRITICAL
Effort: 13 points
```

#### **US-002: Distinguish Obstacles by Vibration Feedback**
```
As a blind person,
I want different vibration patterns for different obstacles,
So that I can understand what type of hazard is approaching without waiting for audio feedback.

Acceptance Criteria:
- [ ] Single pulse vibration (sharp) for people
- [ ] Double pulse vibration (rhythmic) for cars/vehicles
- [ ] Triple pulse vibration (faster) for bicycles/motorcycles
- [ ] Steady vibration (continuous) for stairs/overhead obstacles
- [ ] Slow pulse vibration (gentle) for unknown obstacles
- [ ] Each pattern clearly distinguishable by touch
- [ ] Vibration intensity proportional to distance (closer = stronger)
- [ ] Patterns work consistently with no delays
- [ ] Works with various clothing (gloves, winter gear)

Priority: MEDIUM
Effort: 8 points
```

#### **US-003: Detect Overhead Obstacles and Stairs**
```
As a blind person,
I want the stick to detect obstacles above me and elevation changes,
So that I can avoid hitting my head and stepping incorrectly.

Acceptance Criteria:
- [ ] Detects low ceilings (below 0.5m) via overhead ultrasonic
- [ ] Detects hanging branches and overhangs
- [ ] Detects doorway frames
- [ ] Detects elevation changes (stairs, ramps, curbs)
- [ ] Distinguishes step up from step down
- [ ] Triggers different vibration pattern than forward obstacles
- [ ] Triggers distinctive audio tone (1500 Hz) different from standard 1000 Hz
- [ ] Provides sufficient advance warning (0.5-1m before obstacle)
- [ ] Works in various lighting conditions

Priority: HIGH
Effort: 10 points
```

#### **US-004: Receive Caregiver Guidance via Voice Messages**
```
As a blind person walking outdoors,
I want my caregiver to send me voice messages,
So that I can receive real-time guidance ("slow down", "turn left").

Acceptance Criteria:
- [ ] Caregiver sends message from mobile app
- [ ] Message converts to speech within 3 seconds
- [ ] Audio plays through earpiece clearly
- [ ] Messages queued if stick is offline
- [ ] Messages auto-delete after 24 hours (privacy)
- [ ] Can send to blind person without internet (local WiFi)
- [ ] Message arrives intact, understandable pronunciation
- [ ] Volume adequate (can hear over ambient noise)

Priority: HIGH
Effort: 8 points
```

#### **US-005: Know Current Location**
```
As a blind person,
I want my stick to know my GPS location,
So that I can tell my caregiver "I'm on Paterno Street" if needed.

Acceptance Criteria:
- [ ] GPS lock within 60 seconds (cold start)
- [ ] Location accuracy within 10m
- [ ] Works outdoors (not indoors)
- [ ] Location available via TTS ("You are at...")
- [ ] Location logged for safety review later
- [ ] Updates every 5 seconds when moving

Priority: MEDIUM
Effort: 5 points
```

#### **US-006: Emergency SOS Activation**
```
As a blind person in distress,
I want to trigger an emergency alert,
So that my caregiver knows immediately that I need help.

Acceptance Criteria:
- [ ] Physical button press triggers SOS
- [ ] Caregiver receives immediate notification
- [ ] Current location sent with alert
- [ ] Visual + audio indication that SOS is active
- [ ] SOS can be cancelled within 10 seconds
- [ ] Distinct audio tone for SOS (different from other alerts)
- [ ] Repeating buzzer pattern so user confirms activation

Priority: CRITICAL
Effort: 8 points
```

#### **US-007: Monitor Battery Status with Voice Warnings**
```
As a blind person using the stick,
I want to know battery status through voice announcements,
So that I don't run out of power mid-journey.

Acceptance Criteria:
- [ ] Voice alert at 50% battery: "Battery at 50 percent"
- [ ] Voice alert at 25% battery: "Battery at 25 percent. Consider charging."
- [ ] Voice alert at 10% battery: "Battery critically low at 10 percent"
- [ ] Buzzer accompanies each warning (distinct 800 Hz tone)
- [ ] Announcements clear and easy to understand
- [ ] Can hear warnings over ambient noise
- [ ] No repeated announcements for same level (only once per threshold)
- [ ] Graceful shutdown at 2% (no data loss)

Priority: MEDIUM
Effort: 5 points
```

#### **US-008: Receive Audio Through Earpiece**
```
As a blind person,
I want all audio feedback (object alerts and messages) to play through an earpiece,
So that I can hear clearly and enjoy independent navigation.

Acceptance Criteria:
- [ ] 3.5mm audio jack connection works
- [ ] Bluetooth earpiece pairing works
- [ ] Audio quality is clear and audible
- [ ] Vibration motor still works independently
- [ ] Object detection sounds play in earpiece
- [ ] TTS messages play in earpiece
- [ ] Battery warnings play in earpiece
- [ ] Works with mono or stereo earpieces
- [ ] No audio delays or lag

Priority: MEDIUM
Effort: 6 points
```

#### **US-009: Track Daily Activity**
```
As a blind person,
I want my stick to track where I walked,
So that I can discuss my journey with caregivers or healthcare providers.

Acceptance Criteria:
- [ ] GPS locations logged every 5 seconds
- [ ] Location history stored locally (7 days)
- [ ] Distance traveled calculated per day
- [ ] Time spent walking tracked
- [ ] Number of obstacles detected counted
- [ ] Data available for caregiver review

Priority: LOW
Effort: 5 points
```

---

### **2.2 Caregiver Stories**

#### **US-101: Monitor Location in Real-Time**
```
As a caregiver (parent/assistant),
I want to see my loved one's location on a map,
So that I know they are safe and can reach them if needed.

Acceptance Criteria:
- [ ] Mobile app shows stick location on Google Maps
- [ ] Location updates every 5 seconds (when online)
- [ ] Map shows current position with accuracy radius
- [ ] History shows last 24 hours of movement
- [ ] Can set geofences (home, work, school)
- [ ] Alert if stick leaves geofence
- [ ] Works on iOS and Android

Priority: CRITICAL
Effort: 13 points
```

#### **US-102: Watch Live Camera Feed**
```
As a caregiver,
I want to see what the stick's camera sees,
So that I understand the blind person's environment.

Acceptance Criteria:
- [ ] Mobile app shows live camera feed from stick
- [ ] Feed updates frequently (at least 1-5 FPS)
- [ ] Shows detected objects with visual markers (optional)
- [ ] Can start/stop stream from app
- [ ] Shows current FPS and latency
- [ ] Works on same WiFi or BLE connection
- [ ] Feed cached locally if offline
- [ ] Image quality adequate for context awareness

Priority: HIGH
Effort: 10 points
```

#### **US-103: Send Voice Messages**
```
As a caregiver,
I want to send voice messages to the blind person,
So that I can provide real-time guidance.

Acceptance Criteria:
- [ ] Quick message templates (6 pre-written)
- [ ] Custom message input (up to 500 chars)
- [ ] Message converts to speech on stick
- [ ] Message plays through earpiece
- [ ] Shows estimated speak time
- [ ] Messages queued if offline
- [ ] Message history visible in app
- [ ] Delivery confirmation visible

Priority: HIGH
Effort: 6 points
```

#### **US-104: Find Stick with Remote Controls**
```
As a caregiver,
I want to make the stick vibrate or emit sound,
So that I can locate it if it's lost.

Acceptance Criteria:
- [ ] Vibrate button triggers strong vibration (500ms)
- [ ] Sound button triggers distinct SOS tone
- [ ] SOS tone (2500 Hz) clearly different from all other sounds
- [ ] Commands work even if stick offline (via BLE)
- [ ] Confirmation message shows "Signal sent"
- [ ] Works reliably within 50m range
- [ ] Can trigger repeatedly without delay

Priority: MEDIUM
Effort: 5 points
```

#### **US-105: Monitor Battery Status**
```
As a caregiver,
I want to see the stick's battery percentage,
So that I know if it needs charging.

Acceptance Criteria:
- [ ] Mobile app displays battery %
- [ ] Shows health status (good, warning, critical)
- [ ] Estimated runtime remaining shown
- [ ] Alert if battery <20%
- [ ] Updates every 30 seconds
- [ ] Historical battery trend (last 24 hours)
- [ ] Shows voltage reading

Priority: MEDIUM
Effort: 4 points
```

#### **US-106: Emergency SOS Response**
```
As a caregiver,
I want to receive instant notifications when SOS is pressed,
So that I can respond immediately.

Acceptance Criteria:
- [ ] Push notification on phone
- [ ] SMS alert (optional, if enabled)
- [ ] Shows current location of stick
- [ ] One-tap call to blind person (optional)
- [ ] Notification includes "Tap to view location"
- [ ] SOS marked in location history
- [ ] Receive notification within 2 seconds

Priority: CRITICAL
Effort: 8 points
```

#### **US-107: View Performance Analytics**
```
As a caregiver,
I want to see daily/weekly activity summaries,
So that I can track the blind person's independence and patterns.

Acceptance Criteria:
- [ ] Daily summary: distance traveled, active time, obstacles detected
- [ ] Weekly summary: total distance, alerts triggered, frequent locations
- [ ] Top detected objects (people, cars, stairs)
- [ ] Trends over time (independence improving?)
- [ ] Export data as CSV/PDF
- [ ] Share with healthcare provider (optional)

Priority: LOW
Effort: 8 points
```

---

### **2.3 System & Operations Stories**

#### **US-201: Offline-First Operation**
```
As the system,
I want the stick to work completely offline,
So that it never depends on internet connectivity.

Acceptance Criteria:
- [ ] All detection runs on-device (RPi 5)
- [ ] All alerts work without WiFi
- [ ] GPS works independently
- [ ] Data syncs to cloud only when WiFi available
- [ ] No dropped features when offline
- [ ] Seamless transition from offline → online

Priority: CRITICAL
Effort: 13 points
```

#### **US-202: Low-Latency Alert Response**
```
As the system,
I want detection to trigger alerts <500ms from obstacle appearance,
So that blind users get real-time warnings.

Acceptance Criteria:
- [ ] YOLO inference: <300ms per frame
- [ ] Alert decision logic: <100ms
- [ ] ESP32 motor activation: <100ms
- [ ] Total latency: <500ms (frame capture to motor vibration)
- [ ] Measured and documented consistently

Priority: CRITICAL
Effort: 5 points
```

#### **US-203: Data Privacy & Consent**
```
As the system,
I want to respect user privacy,
So that data is not collected without consent.

Acceptance Criteria:
- [ ] Raw camera frames never uploaded to cloud
- [ ] Location data requires explicit opt-in
- [ ] Data retention policy shown (7 days local, 30 days cloud)
- [ ] Users can delete all data on demand
- [ ] GDPR-compliant data export
- [ ] No tracking without consent

Priority: HIGH
Effort: 8 points
```

#### **US-204: Monitor Electrical Performance**
```
As a system operator,
I want to log all electrical parameters,
So that we can analyze performance and optimize the system.

Acceptance Criteria:
- [ ] Voltage logged every 30 seconds
- [ ] Current consumption logged every 30 seconds
- [ ] Temperature readings logged (RPi and ESP32)
- [ ] Memory usage percentage logged
- [ ] WiFi signal strength logged
- [ ] Detection FPS logged
- [ ] Data stored in CSV file for export
- [ ] Data also stored in database for trends
- [ ] Can export to Excel format
- [ ] No performance impact from logging

Priority: MEDIUM
Effort: 6 points
```

#### **US-205: Graceful System Degradation**
```
As the system,
I want all features to degrade gracefully,
So that stick remains useful if sensors fail.

Acceptance Criteria:
- [ ] If LIDAR fails: use ultrasonic + heuristic
- [ ] If GPS fails: use cached location + IMU
- [ ] If camera fails: alerts still work via ultrasonic
- [ ] If battery low: reduce FPS, prioritize core features
- [ ] System never crashes on sensor error
- [ ] User notified of degraded mode

Priority: MEDIUM
Effort: 8 points
```

---

## **3. MVP Acceptance Criteria**

### **Must Have (CRITICAL)** - Required for
- [x] Real-time object detection (5-6 FPS)
- [x] Distinct vibration patterns (5 types)
- [x] Distinct audio tones (5+ frequencies)
- [x] Overhead obstacle detection
- [x] Stair/elevation detection (up and down)
- [x] Battery warnings (50%, 25%, 10%) via voice
- [x] GPS location tracking (every 5s)
- [x] Mobile app with 5 tabs
- [x] Real-time location on Google Maps
- [x] Quick message sending (6 templates)
- [x] Custom message sending (TTS)
- [x] Find my stick (vibrate/sound remote)
- [x] Battery percentage display in app
- [x] 3+ hours battery life
- [x] Offline-first operation (no internet required)
- [x] Works on same WiFi network
- [x] Earpiece audio output (3.5mm or Bluetooth)
- [x] Emergency SOS button
- [x] SOS distinct tone (2500 Hz)

### **Should Have (HIGH)** - Nice to have for
- [ ] Live camera feed in app
- [ ] Location history visualization (24 hours)
- [ ] Electrical parameters logging (CSV export)
- [ ] Excel charts for performance analysis
- [ ] Geofence alerts (leave home/work)
- [ ] Message delivery confirmation

### **Nice to Have (LOW)** - +
- [ ] Firebase cloud backup
- [ ] Caregiver push notifications
- [ ] Weekly analytics dashboard
- [ ] Multi-stick caregiver dashboard
- [ ] iOS native app
- [ ] Android native app

---

## **4. Non-Functional Requirements**

### **Performance**
- Detection latency: <500ms (frame to alert)
- API response time: <200ms (local WiFi)
- Battery life: 3-4 hours minimum
- Frame rate: 5-6 FPS on RPi 5 CPU
- Update frequency: GPS every 5s, battery every 30s
- Vibration response: <100ms from trigger

### **Reliability**
- Uptime: 99.5% (stick never crashes in normal use)
- Mean time between failures: >24 hours
- Graceful handling of sensor failures
- No data loss on power cycle
- Consistent vibration patterns

### **Scalability**
- MVP: 1 stick, 1-2 caregivers
- : 10-100 sticks on cloud
- Phase 3: 1000+ sticks with federation

### **Security**
- Local data encrypted (SQLite)
- Cloud data TLS 1.2+
- Firebase Auth for user access
- No PII in logs
- GDPR compliant

### **Usability**
- Non-visual interface (audio + haptics only)
- Mobile app intuitive (no training needed)
- Voice feedback clear (TTS at 150 words/min)
- Vibration patterns distinct (can feel difference)
- Audio tones distinct (can hear difference)
- All features accessible without vision

### **Accessibility**
- All alerts non-visual (sound + haptic)
- No reliance on screen reading
- Caregiver app accessible (but visual for caregivers)
- Emergency SOS reachable within 2 taps

---

## **5. Constraints & Assumptions**

### **Hardware Constraints**
- RPi 5 8GB (limited RAM for ML models)
- Battery 10Ah (limited runtime, 3-4 hours max)
- WiFi range 30-50m (typical home network)
- GPS only works outdoors
- Vibration motor has intensity limits (0-255)
- Buzzer frequency range: 100-5000 Hz

### **Software Constraints**
- YOLO Nano (smaller model, ~85% accuracy)
- On-device inference (no real-time cloud processing)
- Python 3.10+ only
- Linux RPi OS only
- Single detection thread (5-6 FPS max on RPi 5)

### **Operational Constraints**
- GPS cold start: 30-60 seconds
- WiFi cold connect: 5-10 seconds
- Battery degrades ~1% per 2-3 months (wear)
- Vibration motor heat dissipation
- Stick must be worn consistently for data gathering

### **Assumptions**
- User will walk during daylight or well-lit areas
- Caregiver always has smartphone
- Home has stable WiFi (2.4 GHz or 5 GHz)
- Stick will be worn/carried consistently
- User somewhat familiar with basic audio navigation
- Bluetooth earpiece supports HFP or A2DP profiles

---

## **6. Phase Roadmap**

### **: MVP (Weeks 1-3)** - Proof of Concept
**Goal:** Stick works autonomously with mobile app monitoring

**Critical Stories:** US-001, US-002, US-003, US-004, US-005, US-006, US-007, US-008, US-101, US-102, US-103, US-104, US-105, US-106, US-201

**Deliverables:**
- Hardware fully assembled & tested
- All sensors operational
- YOLO detection running (5-6 FPS)
- FastAPI server online
- SQLite database operational
- Mobile app built (React Native)
- All 5 tabs functional
- 3+ hour battery verified
- Real-time location tracking
- Distinct vibration patterns working
- Distinct audio tones working
- User can walk 1km with alerts

### **: Cloud & Analytics (Weeks 4-6)**
**Goal:** Real-time monitoring and data analysis

**Stories:** US-107, US-204, US-205 + cloud infrastructure

**Deliverables:**
- Firebase project created
- Firestore database operational
- Cloud Functions deployed
- Push notifications working
- Electrical logging with export
- Daily analytics dashboard
- Caregiver authentication
- Data trending & charts

### **Phase 3: Intelligence (Weeks 7-12)**
**Goal:** Predictive alerts and learning

**Deliverables:**
- LSTM trajectory prediction
- Route learning
- Anomaly detection
- Cloud-based processing
- Integration with navigation apps

### **Phase 4: Production (Months 3-6)**
**Goal:** Market-ready product

**Deliverables:**
- iOS native app
- Android native app
- Manufacturing design
- Regulatory compliance
- Customer support

---

## **7. Success Metrics**

### **User Satisfaction**
- **Target:** >4.0/5 stars
- **Measurement:** In-app feedback after 30-min walk

### **Technical Performance**
- Detection latency: <500ms
- Battery life: 3-4 hours
- GPS accuracy: ±5m outdoor
- Uptime: 99.5%
- Vibration pattern distinction: >90% accuracy
- Buzzer tone distinction: >90% accuracy

### **Adoption**
- : 1 user (self)
- : 3-5 users
- Phase 3: 20+ users

### **Cost Metrics**
- Cost per stick: <$200 (hardware)
- Cloud cost: $0/month (MVP)
- Development: <50,000 PHP

---

## **8. Dependencies & Risks**

### **Key Dependencies**
- Hardware availability (sensors, RPi 5, battery)
- TensorFlow/PyTorch support on RPi
- WiFi network stability
- GPS signal availability
- Firebase free tier coverage

### **Risks & Mitigations**

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| YOLO detection too slow | High | Delays possible | Use INT8 quantization, reduce resolution |
| Battery drains faster | Medium | Users stranded | Extensive testing, conservative estimates |
| GPS doesn't lock | Low | Poor experience | WiFi triangulation fallback, compass |
| Vibration motor failure | Low | Loss of haptic | Dual motors () |
| Audio jack connection issues | Low | TTS not heard | Bluetooth earpiece fallback |

---

## **9. Glossary**

| Term | Definition |
|------|-----------|
| **BVI** | Blind and Visually Impaired |
| **MVP** | Minimum Viable Product () |
| **YOLO** | You Only Look Once (object detection model) |
| **RPi** | Raspberry Pi 5 (main compute device) |
| **FPS** | Frames Per Second (detection rate) |
| **TTS** | Text-To-Speech engine |
| **Haptic** | Touch/vibration feedback |
| **Latency** | Time delay from action to response |
| **Geofence** | Virtual boundary (home, work, etc) |
| **Graceful degradation** | System continues with reduced features |
| **Ultrasonic** | Sound-based distance measurement |
| **LIDAR** | Laser-based distance measurement |
| **IMU** | Inertial Measurement Unit (accelerometer + gyro) |
| **BLE** | Bluetooth Low Energy (wireless protocol) |

---
