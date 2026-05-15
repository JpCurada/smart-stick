"""HTTP endpoints. Thin layer — every handler delegates to a service."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from api.dependencies import Container, get_container
from api.schemas import BuzzRequest, CommandAck, MessageRequest, VibrateRequest
from storage import DetectionRepository, LocationRepository
from utils.converters import iso_timestamp, unix_timestamp

router = APIRouter(prefix="/api")


def _container() -> Container:
    return get_container()


# --------------------------- Detection --------------------------------------- #


@router.get("/latest_detections")
def latest_detections(c: Container = Depends(_container)) -> dict[str, Any]:
    return {
        "detections": c.detection_service.latest_detections(),
        "alert": c.detection_service.latest_alert(),
        "fps": round(c.detection_service.fps(), 2),
        "inference_time_ms": c.detection_service.inference_time_ms(),
        "timestamp": iso_timestamp(),
    }


@router.get("/detections/history")
def detections_history(
    hours: int = Query(default=24, ge=1, le=168),
    c: Container = Depends(_container),
) -> dict[str, Any]:
    since = unix_timestamp() - hours * 3600
    return {"detections": DetectionRepository(c.database).since(since)}


# --------------------------- Location ---------------------------------------- #


@router.get("/location")
def current_location(c: Container = Depends(_container)) -> dict[str, Any]:
    latest = c.location_service.latest()
    if latest is None:
        raise HTTPException(status_code=404, detail="no GPS fix yet")
    return {
        "latitude": latest["latitude"],
        "longitude": latest["longitude"],
        "altitude": latest.get("altitude"),
        "accuracy_m": latest.get("accuracy_m"),
        "timestamp": latest.get("timestamp"),
    }


@router.get("/history/location")
def location_history(
    hours: int = Query(default=24, ge=1, le=168),
    c: Container = Depends(_container),
) -> dict[str, Any]:
    since = unix_timestamp() - hours * 3600
    return {"locations": LocationRepository(c.database).since(since)}


@router.get("/history/location/geojson")
def location_geojson(
    hours: int = Query(default=24, ge=1, le=168),
    c: Container = Depends(_container),
) -> dict[str, Any]:
    since = unix_timestamp() - hours * 3600
    locations = LocationRepository(c.database).since(since)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "timestamp": row["timestamp"],
                    "accuracy_m": row["accuracy"],
                },
            }
            for row in locations
        ],
    }


# --------------------------- Battery ----------------------------------------- #


@router.get("/battery")
def battery_status(c: Container = Depends(_container)) -> dict[str, Any]:
    latest = c.battery_service.latest()
    if latest is None:
        raise HTTPException(status_code=404, detail="no battery reading yet")
    return {
        "percentage": latest["percentage"],
        "voltage": latest["voltage_v"],
        "current": latest.get("current_ma"),
        "health": latest["health"],
        "runtime_minutes": latest.get("estimated_runtime_minutes"),
        "temperature_c": latest.get("temperature_c"),
        "timestamp": iso_timestamp(),
    }


# --------------------------- Camera ------------------------------------------ #


@router.get("/latest_frame")
def latest_frame(c: Container = Depends(_container)) -> Response:
    jpeg, _ = c.frame_buffer.latest()
    if jpeg is None:
        raise HTTPException(status_code=503, detail="no frame available yet")
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/stream")
def stream(c: Container = Depends(_container)) -> StreamingResponse:
    import time

    boundary = "frame"

    def generator():
        last_ts = 0.0
        target_interval = 1.0 / 15.0
        while True:
            jpeg, ts = c.frame_buffer.latest()
            if jpeg is not None and ts != last_ts:
                last_ts = ts
                yield (
                    b"--" + boundary.encode() + b"\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n" + jpeg + b"\r\n"
                )
            time.sleep(target_interval)

    return StreamingResponse(
        generator(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary}",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


# --------------------------- Haptics / Buzzer -------------------------------- #


@router.post("/vibrate", response_model=CommandAck)
def vibrate(request: VibrateRequest, c: Container = Depends(_container)) -> CommandAck:
    command_id = c.output_service.trigger_vibration(request.intensity, request.duration_ms)
    return CommandAck(success=True, command_id=command_id)


@router.post("/buzz", response_model=CommandAck)
def buzz(request: BuzzRequest, c: Container = Depends(_container)) -> CommandAck:
    command_id = c.output_service.trigger_buzz(request.frequency_hz, request.duration_ms)
    return CommandAck(success=True, command_id=command_id)


# --------------------------- Messages ---------------------------------------- #


@router.post("/message", response_model=CommandAck)
def send_message(request: MessageRequest, c: Container = Depends(_container)) -> CommandAck:
    result = c.message_service.send(request.text, priority=request.priority)
    return CommandAck(success=True, command_id=result["message_id"])


@router.get("/message/history")
def message_history(c: Container = Depends(_container)) -> dict[str, Any]:
    return {"messages": c.message_service.history()}


# --------------------------- Emergency --------------------------------------- #


@router.post("/emergency/sos", response_model=CommandAck)
def emergency_sos(c: Container = Depends(_container)) -> CommandAck:
    command_id = c.output_service.emergency_sos()
    return CommandAck(success=True, command_id=command_id)


# --------------------------- Health ------------------------------------------ #


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "timestamp": iso_timestamp()}


@router.get("/status")
def status(c: Container = Depends(_container)) -> dict[str, Any]:
    return {
        "battery": c.battery_service.latest(),
        "location": c.location_service.latest(),
        "session": c.session_service.snapshot(),
        "detection": {
            "fps": round(c.detection_service.fps(), 2),
            "inference_time_ms": c.detection_service.inference_time_ms(),
            "latest_alert": c.detection_service.latest_alert(),
        },
        "timestamp": iso_timestamp(),
    }
