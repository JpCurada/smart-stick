# Trajectory Service — Design

Codename: **"LSTM" / Smart Predict** *(product-facing label only — see note below).*

A new RPi-side service that turns the stream of GPS fixes + detections
into three layered behaviors:

1. **Movement state** — is the user walking, stopped, turning, idle?
2. **Route match** — is the user on a path they've walked before?
3. **Short-horizon prediction** — where will the user be in 5 seconds?

Scope is **working prototype**: each layer works on real data, exposed
through the existing FastAPI surface, displayed in the mobile app. No
unit-test polish, no tuning beyond what one weekend of real walks
provides.

---

## Naming convention

| Layer | Internal name (code) | External name (product/marketing) |
| --- | --- | --- |
| Service | `TrajectoryService` | "Smart Predict" |
| API endpoint | `/api/trajectory` | "Smart Predict" |
| Whole feature in docs | "Trajectory analysis" | "LSTM-powered predictions" |

**Internal code is honest about what it is.** The "LSTM" label lives in
external/product copy only, as agreed with the project owner. There is
no LSTM in this module. If a future iteration genuinely uses an LSTM,
that becomes a different module behind the same API.

---

## Where it fits in the RPi architecture

```
                              ┌─────────────────┐
   LocationRepository ──────► │                 │ ──► /api/trajectory
                              │ TrajectoryService│
   DetectionRepository ─────► │                 │ ──► persisted snapshot
                              └────────┬────────┘
                                       │
                       ┌───────────────┼────────────────┐
                       ▼               ▼                ▼
              ┌────────────────┐ ┌──────────────┐ ┌─────────────┐
              │MovementAnalyzer│ │ RouteMatcher │ │MotionTracker│
              │ (EMA + states) │ │   (k-NN)     │ │  (Kalman)   │
              └────────────────┘ └──────────────┘ └─────────────┘
```

Same layering rules as the rest of the backend:

- Lives in `services/`, only knows about repositories + utils.
- The three sub-modules (`MovementAnalyzer`, `RouteMatcher`,
  `MotionTracker`) live in `services/trajectory/` as **pure functions
  with explicit state**. They take a window of recent fixes and return a
  result. No I/O, no threading. Trivially unit-testable.
- The service threads them together, runs on its own poller, exposes a
  snapshot through the API.

---

## The three layers

### 1. Movement state — `MovementAnalyzer`

| | |
| --- | --- |
| Input | Last N location fixes (`N=10`, ~30s at 5s cadence) |
| Output | `state ∈ {walking, stopped, turning, idle}` + confidence |
| Algorithm | Exponential moving average over (speed, heading) + thresholds |

**Why this, not an LSTM:** the signal is brutally simple. Speed < 0.3 m/s
for 30s = stopped. Heading delta > 45° in <5s = turning. EMA smooths
noisy GPS. Anything fancier learns nothing useful from the data
available.

**Outputs to mobile:** a single string the user/caregiver can see:

> "Walking — 1.2 m/s, NW heading."
>
> "Idle for 2 min — last seen at 14.5995, 120.9842."

### 2. Route match — `RouteMatcher`

| | |
| --- | --- |
| Input | Current trajectory window + database of past walks |
| Output | `{"matched_route": "home_to_cafe", "confidence": 0.78}` or `None` |
| Algorithm | k-NN over fixed-size trajectory windows, Haversine distance |

**Data model:** a "route" is a sequence of GPS waypoints labeled by the
user (manually in the mobile app, for now — auto-clustering is later).
Stored in a new SQLite table `routes(id, name, waypoints_json)`.

**Matching:** for each known route, slide a window of the same length
along it and compute the mean Haversine distance to the current window.
Pick the closest route below a threshold (~20m).

**Why k-NN:** with a handful of routes and short windows it's O(N*W) per
poll — trivial. Deterministic. No training. The user can add a new route
the moment they finish walking it.

**Outputs to mobile:**

> "On known route: Home → Café (78% match)."
>
> "Unfamiliar path."

### 3. Short-horizon prediction — `MotionTracker`

| | |
| --- | --- |
| Input | Recent fixes |
| Output | Predicted `(lat, lng)` 5 seconds ahead, with uncertainty |
| Algorithm | Discrete-time Kalman filter over `[lat, lng, v_lat, v_lng]` |

**Why a Kalman filter:** GPS jitters. A Kalman filter does two useful
things at once — smooths the noisy fixes (better current position) and
extrapolates a few seconds ahead (the "prediction"). For 5-second
horizons in a walking scenario it's accurate to within a few meters,
which is all this feature needs.

**Outputs to mobile:** an optional marker on the map showing "you'll be
here in 5s." Mostly a smoothing/visualization aid, honestly — the real
value is the smoothed current position the other two layers consume.

---

## API surface

One new endpoint that returns the composite snapshot:

```http
GET /api/trajectory
```

```jsonc
{
  "movement": {
    "state": "walking",          // walking | stopped | turning | idle
    "speed_mps": 1.21,
    "heading_deg": 312.4,
    "since_state_change_s": 47
  },
  "route": {
    "matched": "home_to_cafe",    // null when unfamiliar
    "confidence": 0.78
  },
  "prediction": {
    "horizon_s": 5,
    "latitude": 14.5996,
    "longitude": 120.9844,
    "uncertainty_m": 3.2
  },
  "timestamp": "2026-05-22T14:35:02Z"
}
```

Optional companion endpoints (later, not week 1):

- `POST /api/routes` — save the recent trajectory window as a named route
- `GET /api/routes` — list saved routes

---

## Persistence

Two new SQLite tables, defined in `storage/schema.py`:

```sql
CREATE TABLE routes (
    route_id   TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL,
    waypoints_json TEXT NOT NULL  -- JSON array of [lat, lng] pairs
);

CREATE TABLE trajectory_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    unix_ts     INTEGER NOT NULL,
    movement_state TEXT NOT NULL,
    speed_mps  REAL,
    heading_deg REAL,
    matched_route TEXT,            -- nullable
    match_confidence REAL,         -- nullable
    predicted_lat REAL,
    predicted_lng REAL
);
```

Snapshots are persisted at every poll (~every 5s) so we can later look
back and analyse / train. This is the *data collection step* for any
future real ML.

---

## Threading + lifecycle

Same pattern as `LocationService`:

- `TrajectoryService` owns a daemon thread.
- Polls every `TRAJECTORY_UPDATE_INTERVAL_S` (default 5s, matches GPS).
- Reads the most recent N fixes from `LocationRepository`, runs the
  three analyzers, writes a snapshot.
- `Container.start_all()` starts it, `stop_all()` joins it.
- Latest snapshot cached for the API; never reads sensors directly.

---

## Three honest engineering rules for this build

1. **Internal naming stays honest.** No file, class, comment, or commit
   message will lie about what's inside. "LSTM" appears only in
   product/marketing copy.
2. **NumPy-only.** No `scikit-learn`, no `torch`. Each algorithm is a
   ~50-line pure function. Part of the learning project is writing them
   yourself.
3. **Real data validates everything.** Thresholds (speed cutoffs,
   Haversine distance for route match, Kalman noise) are placeholders
   until tuned against a real walking session.

---

## Realistic build order

| Week | Deliverable | Status check |
| --- | --- | --- |
| 1 | Service skeleton, API endpoint, mobile placeholder card | `/api/trajectory` returns hardcoded "walking", mobile renders it |
| 2 | One real walk, exported CSV, notebook to tune thresholds | Plot speed/heading over a real walk |
| 3 | `MovementAnalyzer` real implementation | "Walking" / "Stopped" actually changes based on movement |
| 4 | `MotionTracker` (Kalman) + smoothed positions | Map shows smoother, less jumpy line |
| 5 | `RouteMatcher` + route save endpoint + mobile route list UI | "On known route" appears after saving one |
| 6 | Polish: `trajectory_snapshots` table populated, basic analytics | A week of data sitting in SQLite |

Each week ends with something demoable. Stop at any point and the
previous weeks still work.

---

## What this is NOT

To keep expectations honest:

- **Not an LSTM, not any neural network.** The "LSTM" name is brand only.
- **Not trained.** Thresholds tuned by hand against real walks.
- **Not safety-critical.** This feature suggests context to the
  caregiver; it never overrides the cane's obstacle alerts.
- **Not multi-user.** One stick, one user, one set of routes. Multi-user
  is a separate problem.

---

## Open questions for the next iteration

1. **Should "stopped" trigger a caregiver notification?** If so, after
   how long, and how is the notification delivered (push, SMS)?
2. **Route labels: free text or pinned to map locations?** Free text is
   easier; map-pinned is more discoverable.
3. **Cloud sync of routes?** Phase 2 of the main app — defer.
4. **When the *real* LSTM comes:** once we have weeks of snapshots, the
   right next step is a small LSTM that *predicts the next movement
   state*. That becomes a separate `LSTMMovementPredictor` module,
   plugged in behind the same `/api/trajectory` endpoint, no API change.
