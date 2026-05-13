/**
 * API configuration.
 *
 * The Pi's FastAPI service is reached over mDNS at `raspberrypi.local`.
 * Raspberry Pi OS broadcasts that hostname by default; iOS and most modern
 * Androids resolve it without any extra setup. As long as the phone and the
 * Pi are on the same WiFi, no IP configuration is needed.
 *
 * Override at build/run-time via the EXPO_PUBLIC_API_BASE_URL env var
 * (useful when the Pi's hostname was changed via `raspi-config`, or when a
 * device doesn't support mDNS — fall back to the numeric IP).
 */
import Constants from 'expo-constants';

const DEFAULT_BASE_URL = 'http://raspberrypi.local:5000';

export const API_BASE_URL: string =
  (process.env.EXPO_PUBLIC_API_BASE_URL as string | undefined) ??
  (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ??
  DEFAULT_BASE_URL;

export const POLL_INTERVALS = {
  location: 5_000,
  battery: 30_000,
  detections: 5_000,
  cameraFrame: 1_000,
} as const;

export const REQUEST_TIMEOUT_MS = 5_000;
