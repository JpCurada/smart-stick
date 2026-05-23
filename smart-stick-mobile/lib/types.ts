/**
 * Shared types matching the FastAPI response shapes.
 * Source of truth: rpi/api/routes.py and rpi/api/schemas.py.
 */

export type HealthStatus = 'good' | 'warning' | 'critical';
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type MessagePriority = 'low' | 'normal' | 'high';

export interface BatteryStatus {
  percentage: number;
  voltage: number;
  current: number | null;
  health: HealthStatus;
  runtime_minutes: number | null;
  temperature_c: number | null;
  timestamp: string;
}

export interface LocationFix {
  latitude: number;
  longitude: number;
  altitude: number | null;
  accuracy_m: number | null;
  timestamp: string;
}

export interface DetectionDto {
  class: string;
  confidence: number;
  distance_m: number;
  bbox: [number, number, number, number] | null;
  timestamp: string;
}

export interface AlertDto {
  type: string;
  object_class: string;
  distance_m: number;
  confidence: number;
  vibration_pattern: string | null;
  buzzer_frequency_hz: number | null;
  severity: AlertSeverity;
}

export interface LatestDetectionsResponse {
  detections: DetectionDto[];
  alert: AlertDto | null;
  fps: number;
  inference_time_ms: number;
  timestamp: string;
}

export interface MessageHistoryItem {
  message_id: string;
  timestamp: string;
  text: string;
  priority: MessagePriority;
  delivered: number;
  delivered_at: string | null;
}

export interface CommandAck {
  success: boolean;
  command_id: string | null;
  message: string | null;
}

export interface SosEvent {
  type: 'sos';
  trigger: 'button' | 'test';
  timestamp: string;
  latitude: number | null;
  longitude: number | null;
  maps_url: string | null;
  deep_link: string;
}

export interface StatusResponse {
  battery: BatteryStatus | null;
  location: LocationFix | null;
  session: SessionSnapshot | null;
  detection: {
    fps: number;
    inference_time_ms: number;
    latest_alert: AlertDto | null;
  };
  sos: SosEvent | null;
  timestamp: string;
}

export interface SessionSnapshot {
  session_id: string | null;
  start_time: string | null;
  duration_minutes: number | null;
  distance_km: number;
  detection_count: number;
  alert_count: number;
}
