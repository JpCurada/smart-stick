"""SPI master link to the ESP32 sensor-hub co-processor.

The ESP32 is an SPI slave (see ``smart-stick-firmware/src/spi_comm.cpp``);
the RPi is the master. The firmware owns the LiDAR, both ultrasonic
sensors and the GPS, and confirms the drop / overhead / SOS conditions
itself — the RPi consumes those results.

Wire protocol
-------------
Every poll is one fixed 64-byte full-duplex transfer:

* MISO (ESP32 -> RPi): a 15-byte ``esp_to_rpi_t`` telemetry packet,
  zero-padded to 64 bytes.
* MOSI (RPi -> ESP32): a 4-byte ``rpi_to_esp_t`` command packet,
  zero-padded to 64 bytes.

``esp_to_rpi_t`` (little-endian, ``#pragma pack(1)``, 15 bytes)::

    float   lat            GPS latitude  (0.0 if no fix)
    float   lng            GPS longitude (0.0 if no fix)
    int16_t lidar_dist     LiDAR distance in cm, -1 = no reading
    uint8_t sos_active     1 = SOS active
    uint8_t drop_detected  1 = bottom-ultrasonic drop confirmed
    uint8_t overhead_detected  1 = overhead obstacle confirmed
    uint8_t gps_valid      1 = GPS fix acquired
    uint8_t seq            rolling 0-255 sequence number

``rpi_to_esp_t`` (little-endian, packed, 4 bytes)::

    uint8_t buzzer_cmd     0=off 1=drop 2=overhead 3=sos
    uint8_t vibrator_cmd   0=off 1=on
    uint8_t reserved[2]

The firmware ignores an all-zero command packet, so sending zeros means
"no override" — the firmware keeps driving its own outputs.
"""

from __future__ import annotations

import struct
import threading
from typing import Any

from core.config import Config
from utils.logger import get_logger

try:
    import spidev  # type: ignore[import-not-found]

    _SPIDEV_AVAILABLE = True
except Exception:  # pragma: no cover
    spidev = None  # type: ignore[assignment]
    _SPIDEV_AVAILABLE = False


# struct layouts — must match the #pragma pack(1) C structs in spi_comm.h.
# Note: the firmware comments esp_to_rpi_t as "16 bytes" but under pack(1)
# it is genuinely 15 (4+4+2+1+1+1+1+1). The SPI transfer is a fixed
# 64-byte frame regardless, so only the field offsets need to agree.
_ESP_TO_RPI = struct.Struct("<ffhBBBBB")  # 15 bytes, packed
_RPI_TO_ESP = struct.Struct("<BBBB")  # 4 bytes
TRANSFER_SIZE = 64  # SPI_RX_SIZE in the firmware — fixed padded frame

assert _ESP_TO_RPI.size == 15
assert _RPI_TO_ESP.size == 4


def parse_telemetry(frame: bytes) -> dict[str, Any] | None:
    """Decode the ``esp_to_rpi_t`` prefix of an SPI frame.

    ``frame`` is the raw 64-byte transfer; only the first 15 bytes carry
    data. Returns ``None`` if the frame is too short or looks empty
    (all-zero — the ESP32 has not loaded a packet yet).
    """
    if len(frame) < _ESP_TO_RPI.size:
        return None
    head = frame[: _ESP_TO_RPI.size]
    if not any(head):
        return None  # all-zero: no telemetry loaded yet
    lat, lng, lidar_cm, sos, drop, overhead, gps_valid, seq = _ESP_TO_RPI.unpack(head)
    return {
        "latitude": lat,
        "longitude": lng,
        "lidar_distance_m": (lidar_cm / 100.0) if lidar_cm >= 0 else None,
        "sos_active": bool(sos),
        "drop_detected": bool(drop),
        "overhead_detected": bool(overhead),
        "gps_valid": bool(gps_valid),
        "seq": seq,
    }


def build_command(buzzer_cmd: int = 0, vibrator_cmd: int = 0) -> bytes:
    """Build a 64-byte transfer carrying a 4-byte ``rpi_to_esp_t`` command.

    All-zero (the default) is the "no override" frame the firmware ignores.
    """
    packet = _RPI_TO_ESP.pack(buzzer_cmd & 0xFF, vibrator_cmd & 0xFF, 0, 0)
    return packet + bytes(TRANSFER_SIZE - len(packet))


class Esp32SpiLink:
    """Owns the spidev handle and the single 64-byte full-duplex transfer.

    Thread-safe: the detection loop reads telemetry while the output queue
    worker may send commands, so every transfer is serialised on a lock.
    """

    def __init__(
        self,
        bus: int | None = None,
        device: int | None = None,
        speed_hz: int | None = None,
        mode: int | None = None,
    ) -> None:
        self._bus = bus if bus is not None else Config.ESP32_SPI_BUS
        self._device = device if device is not None else Config.ESP32_SPI_DEVICE
        self._speed_hz = speed_hz if speed_hz is not None else Config.ESP32_SPI_SPEED_HZ
        self._mode = mode if mode is not None else Config.ESP32_SPI_MODE
        self._spi: Any = None
        self._lock = threading.Lock()
        self._log = get_logger("sensors.esp32_spi")

    @property
    def available(self) -> bool:
        return self._spi is not None

    def open(self) -> None:
        """Open the SPI device. Safe to call repeatedly."""
        if self._spi is not None:
            return
        if not _SPIDEV_AVAILABLE:
            self._log.warning("spidev not installed — ESP32 SPI link disabled")
            return
        spi = spidev.SpiDev()  # type: ignore[union-attr]
        spi.open(self._bus, self._device)
        spi.max_speed_hz = self._speed_hz
        spi.mode = self._mode
        self._spi = spi
        self._log.info(
            "ESP32 SPI link open (bus=%d dev=%d %dHz mode=%d)",
            self._bus,
            self._device,
            self._speed_hz,
            self._mode,
        )

    def _xfer(self, buzzer_cmd: int, vibrator_cmd: int) -> bytes | None:
        """Run one raw 64-byte transfer. Returns the RX bytes, or None."""
        if self._spi is None:
            return None
        tx = build_command(buzzer_cmd, vibrator_cmd)
        try:
            with self._lock:
                return bytes(self._spi.xfer2(list(tx)))
        except Exception as exc:
            self._log.debug("SPI transfer failed: %s", exc)
            return None

    def transfer(self, buzzer_cmd: int = 0, vibrator_cmd: int = 0) -> dict[str, Any] | None:
        """Do one full-duplex transfer: send a command, return telemetry.

        Returns the decoded telemetry dict, or ``None`` when the link is
        unavailable or the ESP32 returned an empty frame. Never raises.
        """
        rx = self._xfer(buzzer_cmd, vibrator_cmd)
        return parse_telemetry(rx) if rx is not None else None

    def send_command(self, buzzer_cmd: int = 0, vibrator_cmd: int = 0) -> bool:
        """Send a command override; ignore the telemetry returned alongside.

        Returns True when the transfer itself completed (the firmware acts
        on the command), regardless of what telemetry came back.
        """
        return self._xfer(buzzer_cmd, vibrator_cmd) is not None

    def close(self) -> None:
        if self._spi is not None:
            try:
                self._spi.close()
            except Exception as exc:  # pragma: no cover
                self._log.debug("SPI close raised: %s", exc)
            self._spi = None
