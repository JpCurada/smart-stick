/**
 * Thin HTTP client for the Smart Stick FastAPI backend.
 *
 * Uses `fetch` directly (no axios) to keep the dependency footprint small.
 * Every call has a hard timeout via AbortController so the UI never hangs
 * when the stick is offline.
 */
import { API_BASE_URL, REQUEST_TIMEOUT_MS } from '@/constants/api';
import type {
  CommandAck,
  LatestDetectionsResponse,
  LocationFix,
  MessageHistoryItem,
  MessagePriority,
  NavigationLogResponse,
  StatusResponse,
} from './types';

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        ...(init.headers ?? {}),
      },
    });
    if (!response.ok) {
      throw new ApiError(response.status, `${response.status} ${response.statusText}`);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  // --- Status & Health ---
  health: () => request<{ status: string; timestamp: string }>('/api/health'),
  status: () => request<StatusResponse>('/api/status'),

  // --- Location ---
  location: () => request<LocationFix>('/api/location'),
  locationHistory: (hours = 24) =>
    request<{ locations: LocationFix[] }>(`/api/history/location?hours=${hours}`),

  // --- Detections ---
  latestDetections: () => request<LatestDetectionsResponse>('/api/latest_detections'),

  // --- Navigation (LSTM) ---
  navigationLog: (limit = 50) =>
    request<NavigationLogResponse>(`/api/navigation_log?limit=${limit}`),

  // --- Camera ---
  latestFrameUrl: () => `${API_BASE_URL}/api/latest_frame?ts=${Date.now()}`,
  streamUrl: () => `${API_BASE_URL}/api/stream`,

  // --- Output ---
  vibrate: (intensity: number, durationMs: number) =>
    request<CommandAck>('/api/vibrate', {
      method: 'POST',
      body: JSON.stringify({ intensity, duration_ms: durationMs }),
    }),
  buzz: (frequencyHz: number, durationMs: number) =>
    request<CommandAck>('/api/buzz', {
      method: 'POST',
      body: JSON.stringify({ frequency_hz: frequencyHz, duration_ms: durationMs }),
    }),
  emergencySos: () => request<CommandAck>('/api/emergency/sos', { method: 'POST' }),
  findMyStick: () => request<CommandAck>('/api/find', { method: 'POST' }),

  // --- Messages ---
  sendMessage: (text: string, priority: MessagePriority = 'normal') =>
    request<CommandAck>('/api/message', {
      method: 'POST',
      body: JSON.stringify({ text, priority }),
    }),
  messageHistory: () => request<{ messages: MessageHistoryItem[] }>('/api/message/history'),

  // --- SOS test ---
  // Fire a synthetic SOS event without holding the physical button. The
  // in-app banner will appear on the next /api/status poll. Handy for QA.
  testSos: () =>
    request<{ sent: number; suppressed?: boolean }>('/api/notifications/test', {
      method: 'POST',
    }),
};

export { ApiError };
