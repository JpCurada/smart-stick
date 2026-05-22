# Smart Stick AI — ESP32 Firmware Design

Design layout of the firmware in [smart-stick-firmware/](../smart-stick-firmware/).

## Purpose & Role

The ESP32-DEVKIT-V1 is the **real-time sensor hub**. It owns all hard-timed
work — ultrasonic pulse timing, LiDAR UART parsing, alert state machines — and
reports a compact status packet to the Raspberry Pi 5 over SPI. The Pi handles
vision, TTS, and the API; the ESP32 handles "is something in front of me, right
now."

## Module Map

```
                  ┌─────────────────────────────────────┐
                  │            main.cpp                 │
                  │  setup(): init + 3s calibration     │
                  │  loop():  read → decide → actuate    │
                  │  owns: SOS button FSM, lidar ground  │
                  │        filter, SPI packet assembly   │
                  └──┬───────┬───────┬───────┬───────┬───┘
        ┌────────────┘       │       │       │       └────────────┐
   ┌────▼─────┐   ┌──────────▼──┐  ┌─▼─────┐  ┌─▼──────┐   ┌──────▼─────┐
   │  SENSORS │   │   SENSORS   │  │ ACTU. │  │ ACTU.  │   │   COMMS    │
   ├──────────┤   ├─────────────┤  ├───────┤  ├────────┤   ├────────────┤
   │ lidar    │   │ ultrasonic  │  │vibrator│ │ buzzer │   │ gps  spi   │
   │ (UART2)  │   │ bot + top   │  │(GPIO12)│ │(GPIO33)│   │(UART1)(SPI2)│
   └──────────┘   └─────────────┘  └───────┘  └────────┘   └────────────┘
        │                                                         │
   config.h ── single source of pins, baud rates, all thresholds ─┘
```

Each module is a flat C-style unit: a `.h` with an opaque API plus a `.cpp`
holding all state in file-static variables. There are no classes and no dynamic
allocation. `config.h` is the only shared dependency — every pin and tunable
lives there, nothing is hardcoded elsewhere.

| File | Responsibility |
|---|---|
| `main.cpp` | Boot calibration, SOS button FSM, LiDAR ground filter, loop orchestration, SPI packet assembly |
| `config.h` | All pin assignments, baud rates, thresholds, timing constants |
| `lidar.cpp/.h` | TFmini-S on UART2; ring-buffer framing, checksum, `lidar_data_t` |
| `ultrasonic.cpp/.h` | Both HC-SR04 sensors; pulse timing, leaky-bucket debounce, rolling baseline |
| `vibrator.cpp/.h` | ERM motor; distance→pulse-interval mapping, non-blocking pulse FSM |
| `buzzer.cpp/.h` | Mode-based alert patterns (OFF/DROP/OVERHEAD/SOS), priority + burst FSM |
| `gps.cpp/.h` | NEO-6M on UART1; TinyGPSPlus NMEA parsing, `gps_data_t` |
| `spi_comm.cpp/.h` | SPI slave on SPI2; status out, command in, IRQ handshake |

## Data Flow (one `loop()` iteration)

```
sos_button_update()  ──► sos_active (toggle, 2s hold)
gps_update()         ──► parses queued NMEA, updates gps_data

READ:
  lidar_read()           → ld {distance, strength, temp}   (ring-buffer framed)
  ultrasonic_bot_read()  → bot_dist  (cm or -1)
  ultrasonic_top_read()  → top_dist  (cm or -1)

DECIDE:
  obstacle_dist = lidar, if valid & strong & not-ground & ≤100cm
  drop          = ultrasonic_bot_update()   (leaky debounce vs baseline)
  overhead      = ultrasonic_top_update()   (leaky debounce vs range)
  buzz_mode     = SOS > drop > overhead > off

ACTUATE:
  vibrator_update(obstacle_dist)   → pulse interval ∝ distance
  buzzer_update(buzz_mode)         → pattern state machine

REPORT:
  spi_comm_update(esp_to_rpi_t)    → 16-byte status to Pi
  spi_comm_get_cmd()               → optional Pi override of buzzer/vibrator
```

The entire loop is **cooperative and non-blocking** by design —
`vibrator_update()` and `buzzer_update()` are called every iteration and advance
internal `millis()`-based state machines rather than calling `delay()`. The one
exception is `read_sensor()` in `ultrasonic.cpp`, which uses a short
`delay(60ms)` between trigger pulses (acceptable; the loop has no tighter
deadline).

## Sensor → Actuator Mappings

| Sensor | Faces | Drives | Logic |
|---|---|---|---|
| TFmini-S LiDAR | Forward | Vibration motor | Distance maps linearly to pulse gap (20cm→80ms, 100cm→900ms). Ground baseline from boot calibration suppresses floor returns. |
| HC-SR04 bottom | Down | Buzzer (drop) | Rolling baseline tracks flat ground; >25cm drop = stair/curb. 3 short beeps. |
| HC-SR04 overhead | Up | Buzzer (overhead) | Obstacle within 80cm. 2 long beeps. |
| SOS button | — | Buzzer (SOS) | 2s-hold toggle; plays morse `···———···`. |

## Key Design Patterns

**Leaky-bucket debounce** (`ultrasonic.cpp`, `leaky_update`) — shared by both
ultrasonic sensors. Alert readings increment a hit counter (capped at
`2×confirm`), non-alert readings decrement it; the alert latches at `confirm`
hits. The cap means a confirmed alert needs several clean readings to clear,
preventing flicker. Non-alert readings within a band also drift the baseline
(`×0.95 + new×0.05`) to follow slopes without absorbing sudden drops.

**Buzzer priority state machine** (`buzzer.cpp`) — `SOS` interrupts instantly;
`drop`/`overhead` use a `finishing` flag so a mode change waits for the current
burst to complete (no abrupt mid-beep cutoff). Sub-states
`ST_BEEP → ST_GAP → ST_PAUSE` drive both burst patterns from one switch,
parameterized by mode. Priority order: `SOS > Drop > Overhead > Off`.

**LiDAR framing** (`lidar.cpp`) — bytes accumulate in a 256-byte ring buffer;
each call linearizes and scans *backwards* for the freshest valid `0x59 0x59`
frame with a good checksum. Stale data falls back to `last_good`.

**SPI slave + IRQ handshake** (`spi_comm.cpp`) — ESP32 is the SPI *slave* on
`SPI2_HOST`. `PIN_ESP_IRQ` (GPIO4 → Pi GPIO23) is pulled LOW to signal "fresh
data ready." A `post_trans_cb` ISR copies inbound commands under a critical
section; a non-zero check rejects all-zero idle transfers. Fixed 64-byte padded
transfers; 16-byte status out, 4-byte command in.

## SPI Packet Contract

> Note: the firmware comments `esp_to_rpi_t` as "16 bytes", but under
> `#pragma pack(1)` the struct is genuinely **15 bytes**
> (`4+4+2+1+1+1+1+1`). Each SPI transfer is a fixed **64-byte** padded
> frame regardless, so only the field offsets need to agree between the
> two sides.

**ESP32 → RPi (`esp_to_rpi_t`, 15 bytes, packed):**

| Field | Type | Description |
|---|---|---|
| `lat` | float | GPS latitude (0.0 if no fix) |
| `lng` | float | GPS longitude (0.0 if no fix) |
| `lidar_dist` | int16 | LiDAR distance in cm, -1 = no reading |
| `sos_active` | uint8 | 1 = SOS active |
| `drop_detected` | uint8 | 1 = drop confirmed |
| `overhead_detected` | uint8 | 1 = overhead obstacle confirmed |
| `gps_valid` | uint8 | 1 = GPS fix acquired |
| `seq` | uint8 | Rolling sequence number |

**RPi → ESP32 (`rpi_to_esp_t`, 4 bytes, packed):**

| Field | Type | Description |
|---|---|---|
| `buzzer_cmd` | uint8 | 0=off 1=drop 2=overhead 3=sos |
| `vibrator_cmd` | uint8 | 0=off 1=on |
| `reserved` | uint8[2] | padding |

## RPi Integration

The Raspberry Pi backend ([rpi/](../rpi/)) consumes this firmware as the
SPI master:

- **`sensors/esp32_spi.py`** — `Esp32SpiLink` opens `spidev`, runs the
  64-byte full-duplex transfer, and packs/unpacks the structs with
  `struct` (`<ffhBBBBB>` in, `<BBBB>` out). `parse_telemetry()` and
  `build_command()` are pure functions, unit-tested without hardware.
- **`sensors/stick_telemetry.py`** — `StickTelemetrySensor` wraps the
  link as one `SensorBase`; goes unhealthy when no fresh packet arrives
  within `ESP32_FRAME_TIMEOUT_S`.
- **`detection/detector.py`** — takes LiDAR distance plus the
  firmware-confirmed `drop_detected` / `overhead_detected` flags from the
  telemetry packet. The RPi trusts those flags rather than re-deriving
  them from raw distance.
- **`services/location_service.py`** — reads GPS lat/lng from the packet;
  skips frames until `gps_valid` is set.
- **`output/haptics.py`, `output/buzzer.py`** — send the 4-byte
  `rpi_to_esp_t` command override through the same SPI link. The firmware
  ignores an all-zero command, so "no override" leaves the firmware
  driving its own outputs.

An all-zero telemetry packet means the ESP32 has booted but not yet
published — the RPi treats it as no reading.

## Boot Sequence (`setup()`)

1. Serial at 115200 baud.
2. Init all GPIO, sensors, GPS, SPI slave.
3. Single vibration motor test pulse (300ms).
4. **3-second calibration window** — averages LiDAR + both ultrasonic readings
   (min 5 samples) to establish ground/flat-floor baselines. Hold the cane at
   normal walking angle during this window.

## Observations / Known Issues

1. **GPS RX/TX pin mismatch.** `config.h` defines `PIN_GPS_RX=14,
   PIN_GPS_TX=27`, but the firmware README wiring table says GPS RX→GPIO27,
   GPS TX→GPIO14. `gps.cpp` passes `(PIN_GPS_RX, PIN_GPS_TX)` to `begin(baud,
   config, rxPin, txPin)`, so as defined the ESP32 *receives* on GPIO14. The
   config and the wiring doc disagree — one is wrong. Since GPS only needs the
   ESP32's RX line, the ESP32 RX pin must match the NEO-6M TX wire.

2. **GPIO34 is input-only** — correctly used for `PIN_US_TOP_ECHO`. No issue,
   noted for awareness.

3. **LiDAR ground filter lives in `main.cpp`, not `vibrator.cpp`.**
   `vibrator_update()` receives `obstacle_dist`, which `main.cpp` has already
   ground-filtered. The vibrator module itself has no concept of ground.

4. **`test/` and `lib/` are empty stubs.** No unit tests exist for the debounce
   or buzzer FSM — the most logic-heavy and most testable parts of the firmware.

5. **Double `buzzer_update()` on Pi override.** When the Pi sends a command,
   `main.cpp` calls `buzzer_update()` a second time in the same loop with the
   override mode. This re-enters the FSM; if the override differs from the local
   decision it can set `finishing` unexpectedly. The override path is less clean
   than the sensor path.

6. **Documentation drift.** This firmware lives in `smart-stick-firmware/` (its
   own git repo), while the root `CLAUDE.md` still references an empty
   `firmware/` stub.

## Build & Flash

PlatformIO, `env:esp32dev`, Arduino framework. Dependency: `TinyGPSPlus`.

```bash
pio run --target upload      # build + flash
pio device monitor           # serial, 115200 baud
```
