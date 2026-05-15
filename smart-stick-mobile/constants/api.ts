/**
 * API configuration.
 *
 * Production: Pi broadcasts `raspberrypi.local` via mDNS — works on the same WiFi, no config.
 *
 * Development (Windows mock server):
 *   1. Run `python mock/run.py` from the repo root — it prints your laptop IP.
 *   2. In smart-stick-mobile/.env.local set:
 *        EXPO_PUBLIC_API_BASE_URL=http://<laptop-ip>:5000
 *   3. Phone and laptop must be on the same WiFi.
 *   Current value in .env.local: http://192.168.1.9:5000
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
