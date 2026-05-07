# NFL Schedule Release

A Streamlit dashboard for exploring and analyzing the NFL regular-season schedule. Designed for preseason use, it bundles a league-wide grid view, per-team deep dives, primetime/weekly breakdowns, travel maps, and strength-of-schedule analytics into a single interactive app.

## Features

- **Season selector** — switch between 2025 and 2026 schedules.
- **League View** — full league grid by division, weekly slate, primetime-only schedule, league-wide travel map, and analytics.
- **Team View** — team-banner header with O/U, record, DVOA splits, and bye week, plus per-team Schedule, Analytics (strength / continuity / fantasy heatmaps), and Travel (legs, miles, motion map).
- **Travel maps** — animated arc maps powered by `pydeck`, computed via haversine distance with international stops handled (London, Munich, Madrid, etc.).
- **Custom theming** — branded with NFL colors, Bebas Neue / Barlow Condensed typography, and per-team accent colors.

## Quick Start

```bash
pip install streamlit pandas numpy pydeck
streamlit run Schedule_App/app.py
```

The app reads schedule, team metadata, stadium coordinates, and international-game data into the in-memory frames `ALL_GAMES`, `Team_Info`, `Other_Locations`, and the `TEAM_*_MAP` / `INTL_DATA` lookups used throughout `app.py`.

## Data Inputs (expected)

| Frame / Map | Purpose |
|---|---|
| `ALL_GAMES` | Every game across seasons (`_season`, `Week`, `Date`, `Home`, `Away`, `Location`, `International`, `Game Type`, `Primetime Flag`). |
| `Team_Info` | Team metadata: `Team`, `Abb`, `City`, `Nickname`, `Conference`, `Division`, `Logo`, `Wordmark`, `Color1`/`Color2`, `Bye`, `Vegas O/U`, `2025 Wins`, DVOA splits, coordinator tenures, fantasy ranks. |
| `Other_Locations` | Neutral-site / non-team venues used in the grid. |
| `TEAM_CITY_MAP`, `TEAM_STAD_MAP`, `TEAM_LAT_MAP`, `TEAM_LON_MAP`, `TEAM_TZ_MAP` | Per-team city, stadium, lat/lon, timezone. |
| `INTL_DATA`, `NEUTRAL_LOCATION_SET` | International venue metadata (stadium, lat/lon, tz). |

## Repo Layout

```
NFL_Schedule_Release/
├── README.md
└── Schedule_App/
    └── app.py     # Single-file Streamlit dashboard (~2,600 lines)
```

---

## `Schedule_App/app.py` — Table of Contents

| Lines | Section |
|---:|---|
| 1–28 | **Inline CSS / typography** — page styles, masthead, "Under Construction" placeholder. |
| 30–43 | **Masthead** — NFL logo + "Schedule Hub" title bar. |
| 45–60 | **Season selector** — filters `ALL_GAMES` into the active `Games` frame. |
| 62–75 | **Global config** — `DAY_CFG` color map per game day, `WEEKS`, row/header background constants. |
| 77–101 | **Game classification helpers** — `is_snf_game`, `get_forced_venue` (Super Bowl / Feb 14), `get_day_type`. |
| 103–119 | **Travel math utilities** — `travel_valid_coord`, `travel_haversine`. |
| 120–241 | **`build_team_travel`** — per-team leg builder with international handling and "stay vs return" logic (Jaguars London edge case). |
| 242–282 | **`travel_map_rows`** — converts legs into pydeck arc/node DataFrames. |
| 283–435 | **`render_travel_motion_map`** — animated arc map renderer. |
| 436–461 | **`build_cells`** — assembles the league-grid cells (one per team / week). |
| 462–489 | **`make_legend`** — day-of-week color legend HTML. |
| 490–587 | **`make_division_table`** — division-row HTML for the league grid. |
| **588** | **Top-level tabs**: `🌐 League View` / `🏈 Team View`. |
| 590–1088 | **League View** (`tabs[0]`) |
| &nbsp;&nbsp;592 | &nbsp;&nbsp;Sub-tabs declaration. |
| &nbsp;&nbsp;593–612 | &nbsp;&nbsp;League-view lookup tables (logos, colors, stadium/lat/lon/tz, intl). |
| &nbsp;&nbsp;614–639 | &nbsp;&nbsp;📋 **Full Schedule** — division-grouped league grid. |
| &nbsp;&nbsp;641–812 | &nbsp;&nbsp;🗓️ **Weekly Schedule** — week selector with matchup rows. |
| &nbsp;&nbsp;814–1000 | &nbsp;&nbsp;🌙 **Primetime Schedule** — TNF / SNF / MNF and special windows. |
| &nbsp;&nbsp;1002–1084 | &nbsp;&nbsp;✈️ **Travel** — league flight totals, motion map, miles ranking table. |
| &nbsp;&nbsp;1086–1087 | &nbsp;&nbsp;📊 **Analytics** *(placeholder)*. |
| 1089–2600 | **Team View** (`tabs[1]`) |
| &nbsp;&nbsp;1091–1148 | &nbsp;&nbsp;Team-view utilities — color/luminance helpers, `SCHED_DAY_CFG`, `tv_day_key`. |
| &nbsp;&nbsp;1150–1163 | &nbsp;&nbsp;Lookup tables (abb, logo, wordmark, colors, geo). |
| &nbsp;&nbsp;1163–1224 | &nbsp;&nbsp;Team selector + metric extraction (O/U, DVOA, ST, bye). |
| &nbsp;&nbsp;1225–1264 | &nbsp;&nbsp;**Team Banner** — gradient header with logo, wordmark, stat blocks. |
| &nbsp;&nbsp;1266 | &nbsp;&nbsp;Sub-tabs declaration: Schedule / Analytics / Travel. |
| &nbsp;&nbsp;1269–1511 | &nbsp;&nbsp;📅 **Schedule** — week-by-week opponent rows, TBA-week handling for 2026. |
| &nbsp;&nbsp;1513–2114 | &nbsp;&nbsp;📊 **Analytics** — strength / continuity / fantasy heatmaps with normalized scoring. |
| &nbsp;&nbsp;2116–2600 | &nbsp;&nbsp;✈️ **Travel** — leg list, total miles, time-zone deltas, animated route map. |

### Key Functions Reference

| Function | Lines | Purpose |
|---|---:|---|
| `is_snf_game(row)` | 77 | Detect Sunday Night Football flag. |
| `get_forced_venue(row)` | 84 | Override venue for Super Bowl / Feb 14. |
| `get_day_type(row)` | 93 | Map a game to its day-of-week color key. |
| `travel_haversine(...)` | 112 | Great-circle distance in miles. |
| `build_team_travel(...)` | 120 | Compute a team's full travel itinerary. |
| `travel_map_rows(...)` | 242 | Build pydeck arc + node DataFrames. |
| `render_travel_motion_map(...)` | 283 | Render animated arc map. |
| `build_cells(...)` | 436 | Build league-grid cell dict. |
| `make_legend()` | 462 | League-grid legend HTML. |
| `make_division_table(...)` | 490 | Division-row HTML for league grid. |

## Notes

- The app uses `st.html` heavily for custom-styled tables and banners rather than `st.dataframe` — restyling means editing inline CSS strings.
- 2026 schedule entries use a TBA-week mode that pushes non-regular-season games to the end of the team-schedule list (see lines 1274–1287).
- The Jaguars get special-cased as a "stay in London" team between consecutive international games (line 176, line 2188).
