# Design system: dashboard

One small set of rules so every chart reads the same way. Theme file: `.streamlit/config.toml`. Colour constants: top of `dashboard/app.py`.

## 1. Colour tokens

| Token | Hex | Used for |
|---|---|---|
| Background | `#0E1621` | Page |
| Surface | `#17212E` | Tables, info boxes |
| Text | `#E6EDF3` | All text |
| Primary | `#4DA3FF` | Links, selected controls, single-series bars |
| `ARRIVAL` | `#8EC5FF` | Arrivals (light blue: "coming in") |
| `DEPARTURE` | `#1F6FEB` | Departures (strong blue: "going out") |
| `SERIES_2` | `#F2A33A` | Second line in a two-line chart (unique aircraft) |
| `COMPLETE` | `#3FB950` | Complete airport day (good) |
| `INCOMPLETE` | `#F2A33A` | Incomplete day / OpenSky gap (attention) |
| Map points | `#FF4B4B` | Aircraft positions on the dark map |

Rules:
- Meaning, not decoration: green = trustworthy, amber = look at this. Red is not used for data (nothing on the dashboard is an error state).
- Arrivals and departures are always the same two blues, in every chart.
- Amber is shared by "second series" and "incomplete" because they never appear in the same chart.
- Dark theme because the dashboard is meant for an operations screen; all colours checked for contrast on `#0E1621`.

## 2. Chart types and when to use each

| Question | Chart | Example |
|---|---|---|
| How does a value change over time? | Line | Airborne aircraft per hour |
| How do a few categories compare? | Vertical bar | Flight phase mix, registration countries |
| Two related quantities per hour | Grouped bar | Arrivals vs departures by local hour |
| Value per day with a status | Bar coloured by status | Movements per day (complete / incomplete) |
| Where is something? | Map (latest snapshot only) | Latest snapshot positions |
| Exact values someone will look up | Table | Busiest routes, pipeline health, data quality |

Not used: pie charts (hard to compare slices), 3D, dual y-axes.

## 3. Layout (top to bottom = most to least important for the reader)
1. Title, one-line subtitle with the data path, demo banner if in demo mode.
2. KPI row: 4 numbers (unique aircraft, airborne now, p95 latency, data as of).
3. Traffic over Germany: hourly line, then phase mix + countries side by side, then map.
4. Airports: picker, KPI row, typical day + busiest routes side by side, movements per day.
5. Trust: data freshness, pipeline health, data quality.

Two columns at most; on a narrow screen Streamlit stacks them.

## 4. Numbers and time
- Thousands separator: `12,980`. Percentages with one decimal: `8.0%`. Latency in whole ms.
- Live traffic in **UTC** (that is how OpenSky stamps it); airport profiles by **local hour (Europe/Berlin)** because that is how airports plan. Every chart says which.
- Averages use complete days only; the caption says so.

## 5. Text
- Titles say what is shown, not how ("Movements per day: Frankfurt (FRA)").
- Captions explain a caveat in one line (e.g. what `median_min` means).
- Warnings (`st.warning`) only for things the reader must know before trusting a number (incomplete airport days).
