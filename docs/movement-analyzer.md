# MovementAnalyzer — How "LSTM" Works in Smart Stick

> **About the name.** In product copy and pitches we call this feature
> "LSTM" or "Smart Predict." In the code it is `MovementAnalyzer`, and
> there is **no actual LSTM (no neural network of any kind) inside.**
> See [trajectory-design.md](trajectory-design.md) for why we made that
> choice; this doc is about how the *real* algorithm works.

This is a plain-English walkthrough of how Smart Stick understands what
the cane user is doing — walking, stopped, turning, idle — by analyzing
the GPS stream. It is the first of three trajectory layers; route
matching and short-horizon prediction live alongside it.

---

## The job, in one sentence

**Every few seconds, decide which of four states best describes the user's
recent motion: `walking`, `stopped`, `turning`, or `idle`.**

That label drives the in-app card the caregiver sees ("Walking, 1.2 m/s,
heading NW") and feeds into future features like anomaly alerts ("user
has been idle for 5 minutes in an unfamiliar location").

---

## What's the input

A rolling buffer of the **most recent ~10 GPS fixes** from
`LocationRepository`. Each fix is just three numbers:

```
(timestamp, latitude, longitude)
```

At a 5-second cadence, ten fixes = the last ~50 seconds of walking.

```
fix[0]   2026-05-23T11:24:50Z  14.59950  120.98420   ← oldest
fix[1]   2026-05-23T11:24:55Z  14.59952  120.98421
...
fix[9]   2026-05-23T11:25:35Z  14.59970  120.98432   ← newest
```

We **never look further back than the buffer**. State is intentionally
recent — if the user paused 10 minutes ago, that doesn't affect "are
they walking right now."

---

## What's the output

Every poll, the analyzer emits:

```python
{
  "state": "walking",           # one of: walking | stopped | turning | idle
  "speed_mps": 1.21,            # smoothed scalar speed
  "heading_deg": 312.4,         # bearing of recent motion (0=N, 90=E, ...)
  "since_state_change_s": 47,   # how long we've been in this state
}
```

That's it. Four states, three numbers. No probabilities, no
distributions, no model files. Anyone can debug it.

---

## How the four states are decided

Two signals drive the decision: **how fast** and **how straight**.

### Signal 1 — Smoothed speed

Between every pair of consecutive fixes, compute Haversine distance
(great-circle distance on Earth's surface) and divide by the time gap.
That gives raw m/s per pair.

Raw GPS speed is **noisy** — even standing still, fix-to-fix jitter
makes it look like you're walking at 0.4 m/s. So we smooth it with an
exponential moving average:

```
smoothed = α × raw + (1 − α) × smoothed_prev
```

With α ≈ 0.3, recent readings count more than old ones, but a single
jitter spike can't flip the state. ~3 fixes of consistent change before
the smoothed value catches up.

### Signal 2 — Heading change

The compass bearing between consecutive fixes tells us which way the user
is going. Compare the **most recent** bearing to the bearing 2-3 fixes
ago: a big delta means "turning."

### The decision rule

Plain thresholds — deliberately simple, deliberately editable:

```
if smoothed_speed < 0.3 m/s  for ≥ 30 seconds   →  "stopped"
if smoothed_speed < 0.3 m/s  for ≥ 5 minutes    →  "idle"
if |heading_change| > 45° in last 5 seconds      →  "turning"
if 0.3 ≤ smoothed_speed ≤ 2.5 m/s                →  "walking"
otherwise                                         →  most recent state
```

`stopped` vs. `idle` is purely a duration distinction — stopped at a
crosswalk (30 seconds) vs. resting on a bench (5 minutes). Both are
"not moving," but the caregiver-facing alert behaves differently for
each.

---

## Walking through one real example

Suppose the last 50 seconds look like this:

| Time (s) | Lat → Lng change | Computed speed | Smoothed |
|---|---|---|---|
| 0  | start of window | — | — |
| 5  | +6m N           | 1.2 m/s | 1.20 |
| 10 | +6m N           | 1.2 m/s | 1.20 |
| 15 | +6m N           | 1.2 m/s | 1.20 |
| 20 | +1m random (GPS jitter while paused at corner) | 0.2 m/s | 0.90 |
| 25 | +6m E (turned!) | 1.2 m/s | 0.99 |
| 30 | +6m E           | 1.2 m/s | 1.05 |

State transitions:

- Window 0–20s: smoothed speed = 1.2 m/s → `walking`
- Window 25s: heading changed N → E (90° delta in <5s) → `turning`
- Window 30s: heading stable again, speed back to 1.2 m/s → `walking`

That's the entire algorithm. No training. No model. Sixty lines of
NumPy.

---

## Where this fits in the wider system

```
ESP32 firmware (sensors over SPI)
        │
        ▼ "sos_active=0, lat=14.5995, lng=120.9842, gps_valid=1"
StickTelemetrySensor
        │
        ▼
LocationService  ──► persists GPS fix to SQLite
        │
        ▼ last N fixes
MovementAnalyzer  ──► emits {state, speed, heading}
        │
        ▼ part of /api/trajectory snapshot
Mobile app  ──► renders "Walking, 1.2 m/s" card
```

The analyzer **never touches sensors directly** — it reads from
`LocationRepository`. That keeps it pure, testable, and replaceable.

---

## Why not an actual LSTM?

For BVI-cane-on-RPi with no training data, an LSTM is the wrong tool:

| Concern | LSTM | EMA + thresholds (what we use) |
|---|---|---|
| Data needed to ship | Weeks of labeled walks | Zero |
| Tuning | Hyperparameter search | Edit a number, see the change |
| Compute on RPi | Acceptable but non-trivial | <1% CPU |
| Debuggability | "Why did it say walking?" | Step through with `pdb` |
| Honest about uncertainty | Yes (with calibration) | No (deterministic) |
| Future migration path | Already neural | Swap in an LSTM behind same API |

When we *do* have weeks of real walk data (see "Future work" below),
swapping the threshold logic for an LSTM is a one-file change: it
implements the same input/output contract.

---

## What makes this prone to being wrong

Three honest failure modes:

1. **GPS jitter near buildings.** Tall walls reflect signals. A
   stationary user near a glass facade can show 0.5 m/s false motion;
   the EMA buys us 15 seconds before the wrong state flips, but if the
   jitter is sustained the analyzer will lie. There is no software-only
   fix — Kalman filtering (in `MotionTracker`) helps but doesn't
   eliminate it.

2. **Indoors → useless.** No GPS, no fixes, no buffer to analyze. The
   API will return `state: null` until the user steps outside.

3. **First 30 seconds after startup.** The buffer needs to fill before
   any classification is reliable. Until then, the API may return
   `walking` simply because that was the *initial* assumption.

These limits live in the algorithm by design. We surface uncertainty in
the API:

```json
{ "state": "walking", "confidence": "low", "reason": "buffer-warming" }
```

…so the mobile UI can grey-out the card during warm-up.

---

## Thresholds you'll want to tune

All in `services/trajectory/movement_analyzer.py` as module constants:

| Constant | Default | What it controls |
|---|---|---|
| `EMA_ALPHA` | 0.30 | How fast the smoothed speed responds to changes |
| `WINDOW_FIXES` | 10 | How many GPS fixes feed each decision |
| `WALKING_MIN_MPS` | 0.30 | Below this is "stopped" |
| `WALKING_MAX_MPS` | 2.50 | Above this is "anomaly" (currently logged, not alerted) |
| `STOPPED_TO_IDLE_S` | 300 | How long "stopped" before promoting to "idle" |
| `TURN_HEADING_DEG` | 45 | Heading delta that counts as a turn |
| `TURN_WINDOW_S` | 5 | Time window the heading delta is measured over |

**Tune these against real walks.** The defaults are placeholders. Week 2
of the build plan is specifically a notebook session where you load a
day's worth of GPS data, label segments by hand, and adjust until the
analyzer agrees with your labels.

---

## Snapshot persistence (for later learning)

Every poll, the analyzer also writes a row to a new SQLite table
`trajectory_snapshots`:

```sql
CREATE TABLE trajectory_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  timestamp   TEXT NOT NULL,
  movement_state TEXT,
  speed_mps      REAL,
  heading_deg    REAL,
  -- (other layers' fields too)
);
```

This is the **data collection step** for any future real ML. A month
of these snapshots, exported as CSV, is exactly what you'd train an
LSTM on. **We never train on synthetic data** (see [trajectory-design.md](trajectory-design.md)
for why).

---

## API surface

A single endpoint returns the composite trajectory snapshot:

```http
GET /api/trajectory
```

```jsonc
{
  "movement": {
    "state": "walking",
    "speed_mps": 1.21,
    "heading_deg": 312.4,
    "since_state_change_s": 47,
    "confidence": "high"
  },
  "route":      { /* from RouteMatcher,  see trajectory-design.md */ },
  "prediction": { /* from MotionTracker, see trajectory-design.md */ },
  "timestamp": "2026-05-23T14:35:02Z"
}
```

The mobile app polls this on the existing cadence (~5 s) and renders
the result.

---

## What the user / caregiver actually sees

On the **Home tab**:

```
┌───────────────────────────────┐
│ Movement                      │
│ Walking                       │
│ 1.2 m/s, heading NW           │
│ for 0:47                      │
└───────────────────────────────┘
```

Or when stopped:

```
┌───────────────────────────────┐
│ Movement                      │
│ Stopped                       │
│ Idle for 0:32                 │
└───────────────────────────────┘
```

Plain text. The point isn't to look impressive — it's to give a
caregiver a one-glance answer to "what is the user doing right now."

---

## Future work (when we have real data)

In order of likely value:

1. **Tune thresholds against real walks.** Mandatory before anything
   else.
2. **Add an "unfamiliar pace" anomaly** — if smoothed speed drifts >2σ
   from the user's personal baseline, surface a soft alert. Statistical,
   not ML.
3. **Add an HMM** (hidden Markov model) over the four states. Smooths
   out spurious flips at state boundaries. Still not a neural network,
   but a smarter state machine.
4. **Add a real LSTM** (if and only if HMM proves insufficient). At
   that point we'd predict the next state 30s ahead — useful for
   pre-emptive caregiver notifications ("user usually stops here for
   several minutes; expect them at their destination at 14:42").

Each step is a strict superset of the previous one. The MovementAnalyzer
API contract stays the same; only the implementation grows.

---

## Honest current state

- **Algorithm: designed, not yet implemented.** Code lives at
  [services/trajectory/](../rpi/services/trajectory/) as a stub.
- **Data: not collected yet.** We need outdoor GPS fixes from the
  ESP32-mounted GPS module first (the firmware issue tracked in
  [firmware-design.md](firmware-design.md)).
- **Hardware-validated: no.** Like the rest of the SPI pipeline.

The build order in [trajectory-design.md](trajectory-design.md) makes
this concrete: scaffold the service first, walk with the cane once
GPS works, tune thresholds in a notebook, ship the real implementation.
