# Smart Stick — Caregiver App

React Native / Expo app for monitoring a Smart Stick over the local network.
Talks to the FastAPI backend running on the Raspberry Pi (see [`../rpi`](../rpi)).

> **Network requirement:** the caregiver's phone must be on the **same WiFi
> network** as the stick. Remote access over cellular or from a different
> network is a Phase 2 feature that requires the Firebase cloud sync layer
> described in [`docs/specs.md §11.3`](../docs/specs.md). The MVP is
> deliberately home-network-only — see [requirements.md US-101](../docs/requirements.md).

---

## Five tabs

| Tab          | Purpose                                                  | Backend endpoints                                      |
| ------------ | -------------------------------------------------------- | ------------------------------------------------------ |
| **Home**     | Online status, battery, detection FPS, distance today    | `GET /api/battery`, `GET /api/status`                  |
| **Location** | Current GPS fix + accuracy, link out to Google Maps      | `GET /api/location`                                    |
| **Find**     | Remote vibrate (255 / 500 ms) and SOS sound (2500 Hz)    | `POST /api/vibrate`, `POST /api/emergency/sos`         |
| **Message**  | 6 quick templates + custom TTS, last 20 messages         | `POST /api/message`, `GET /api/message/history`        |
| **Video**    | Live frame polling (~1 FPS), detection stats             | `GET /api/latest_frame`, `GET /api/latest_detections`  |

---

## Setup

```bash
cd smart-stick-mobile
npm install
```

The app defaults to `http://raspberrypi.local:5000`. As long as both your
phone and the Pi are on the same WiFi, this resolves automatically via
mDNS — no IP configuration needed.

Override only if you renamed the Pi's hostname or your device cannot
resolve `.local` (some Android networks):

```bash
# Bash
EXPO_PUBLIC_API_BASE_URL=http://192.168.1.42:5000 npx expo start

# PowerShell
$env:EXPO_PUBLIC_API_BASE_URL="http://192.168.1.42:5000"; npx expo start
```

---

## Run

```bash
npx expo start                 # interactive launcher
npx expo start --android       # open on Android emulator
npx expo start --ios           # open on iOS simulator (macOS only)
```

Scan the QR code with **Expo Go** to load the app on a physical device.

---

## Project layout

```
smart-stick-mobile/
├── app/                       File-based routing (expo-router)
│   ├── _layout.tsx            Root stack + theme provider
│   └── (tabs)/
│       ├── _layout.tsx        Tab navigator (5 tabs)
│       ├── index.tsx          Home
│       ├── location.tsx       Location
│       ├── find.tsx           Find
│       ├── message.tsx        Message
│       └── video.tsx          Video
├── components/                Reusable UI primitives
│   ├── action-button.tsx
│   ├── battery-card.tsx
│   ├── info-row.tsx
│   ├── status-badge.tsx
│   ├── themed-text.tsx
│   ├── themed-view.tsx
│   ├── haptic-tab.tsx
│   └── ui/icon-symbol*.tsx
├── constants/
│   ├── api.ts                 API base URL + poll intervals
│   └── theme.ts               Colours + fonts
├── hooks/
│   ├── use-poll.ts            Focus-aware polling hook
│   ├── use-color-scheme.ts
│   └── use-theme-color.ts
├── lib/
│   ├── api.ts                 Typed fetch wrapper for the FastAPI backend
│   └── types.ts               Response shapes (mirrors rpi/api/schemas.py)
└── assets/
```

---

## Known gaps / next steps

- **Map view (Tab 2).** The current build shows coordinates textually plus a
  "Open in Google Maps" link. To embed a live map, add
  `react-native-maps` and replace the placeholder block in
  [`app/(tabs)/location.tsx`](app/(tabs)/location.tsx). Requires a custom
  Expo dev build (Expo Go ships without that native module).
- **Live camera (Tab 5).** Polls `/api/latest_frame`, which currently
  returns HTTP 501 on the Pi. Wire a shared frame buffer in the detection
  loop to serve the latest JPEG, or upgrade to WebSocket streaming.
- **BLE Find fallback (Tab 3).** US-104 requires BLE so commands work
  when the stick is offline. Add `react-native-ble-plx` and a BLE-mode
  branch in `lib/api.ts`. Needs a custom dev build (no Expo Go support).
- **Push notifications (Phase 2).** Wire `@react-native-firebase/messaging`
  for the SOS-response notification flow described in US-106.
