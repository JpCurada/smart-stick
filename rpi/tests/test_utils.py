"""Tests for utils/ helpers — pure functions, no I/O."""

from __future__ import annotations

from utils.converters import geohash_encode, iso_timestamp, unix_timestamp
from utils.geometry import distance_to_intensity, haversine_distance_m
from utils.validators import (
    clamp,
    is_valid_frequency,
    is_valid_intensity,
    is_valid_latitude,
    is_valid_longitude,
    is_valid_percentage,
)


class TestValidators:
    def test_latitude_bounds(self) -> None:
        assert is_valid_latitude(0.0)
        assert is_valid_latitude(-90.0)
        assert is_valid_latitude(90.0)
        assert not is_valid_latitude(90.1)
        assert not is_valid_latitude(-90.1)

    def test_longitude_bounds(self) -> None:
        assert is_valid_longitude(120.0)
        assert not is_valid_longitude(181.0)
        assert not is_valid_longitude(-181.0)

    def test_percentage_bounds(self) -> None:
        assert is_valid_percentage(0)
        assert is_valid_percentage(100)
        assert not is_valid_percentage(-1)
        assert not is_valid_percentage(101)

    def test_intensity_bounds(self) -> None:
        assert is_valid_intensity(0)
        assert is_valid_intensity(255)
        assert not is_valid_intensity(256)

    def test_frequency_bounds(self) -> None:
        assert is_valid_frequency(100)
        assert is_valid_frequency(5000)
        assert not is_valid_frequency(50)
        assert not is_valid_frequency(6000)

    def test_clamp(self) -> None:
        assert clamp(5, 0, 10) == 5
        assert clamp(-5, 0, 10) == 0
        assert clamp(15, 0, 10) == 10


class TestGeometry:
    def test_haversine_zero_for_same_point(self) -> None:
        assert haversine_distance_m(14.6, 120.98, 14.6, 120.98) == 0.0

    def test_haversine_known_distance(self) -> None:
        # Quezon City -> Manila roughly 11 km.
        d = haversine_distance_m(14.6760, 121.0437, 14.5995, 120.9842)
        assert 9_000 < d < 13_000

    def test_distance_to_intensity_inverse(self) -> None:
        # Closer => stronger.
        near = distance_to_intensity(0.5, max_distance_m=2.0, max_intensity=255)
        far = distance_to_intensity(1.9, max_distance_m=2.0, max_intensity=255)
        assert near > far

    def test_distance_to_intensity_clamps(self) -> None:
        assert distance_to_intensity(0.0, 2.0) == 255
        assert distance_to_intensity(3.0, 2.0) == 0


class TestConverters:
    def test_unix_and_iso_consistent(self) -> None:
        unix = unix_timestamp()
        iso = iso_timestamp()
        assert unix > 1_700_000_000  # post-2023
        assert iso.endswith("Z")

    def test_geohash_deterministic(self) -> None:
        # Same input -> same hash.
        a = geohash_encode(14.5995, 120.9842, precision=6)
        b = geohash_encode(14.5995, 120.9842, precision=6)
        assert a == b
        assert len(a) == 6
