"""Type and unit conversion helpers."""

from __future__ import annotations

from datetime import datetime, timezone

_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def now_utc() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def unix_timestamp(dt: datetime | None = None) -> int:
    """Convert datetime to integer unix seconds."""
    return int((dt or now_utc()).timestamp())


def iso_timestamp(dt: datetime | None = None) -> str:
    """Return ISO 8601 UTC string with millisecond precision."""
    moment = dt or now_utc()
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def geohash_encode(latitude: float, longitude: float, precision: int = 8) -> str:
    """Encode (lat, lon) into a geohash string."""
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    geohash: list[str] = []
    bits: list[int] = []
    bit = 0
    even = True

    while len(geohash) < precision:
        if even:
            mid = (lon_range[0] + lon_range[1]) / 2.0
            if longitude > mid:
                bits.append(1)
                lon_range[0] = mid
            else:
                bits.append(0)
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2.0
            if latitude > mid:
                bits.append(1)
                lat_range[0] = mid
            else:
                bits.append(0)
                lat_range[1] = mid

        even = not even
        bit += 1
        if bit == 5:
            index = (bits[0] << 4) | (bits[1] << 3) | (bits[2] << 2) | (bits[3] << 1) | bits[4]
            geohash.append(_GEOHASH_BASE32[index])
            bits = []
            bit = 0

    return "".join(geohash)
