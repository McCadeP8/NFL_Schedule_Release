# NHL State Lab

A Streamlit MVP for analyzing NHL performance by manpower and score state.

The ingestion pipeline preserves raw NHL API responses, reconstructs one-second
on-ice states from official shift charts, labels every play with the score
before the event, and optionally joins MoneyPuck shot-level expected goals.

## What is included

- 2025-26 regular-season and playoff schedule discovery
- NHL play-by-play, box scores, and shift-chart downloads
- Exact score-before-event labels
- Skater count and goalie-presence dimensions
- Strict and configurable post-transition carryover goal attribution
- Goals and xGoals by score differential and exact score
- Score-flow Sankey-style transition view
- 2026-27-ready incremental ingestion
- Raw JSON cache, retry support, and resumable processing

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ingest

Download and process the completed 2025-26 season:

```powershell
python -m nhl_state_lab.pipeline --season 20252026 --game-types 2 3
```

Add or refresh 2026-27 later:

```powershell
python -m nhl_state_lab.pipeline --season 20262027 --game-types 1 2 3
```

The command is resumable. Existing raw files are reused unless `--refresh` is
provided. To skip the optional MoneyPuck import, add `--skip-moneypuck`.

## Run the app

```powershell
streamlit run app.py
```

## Data notes

- NHL situation codes and shift charts occasionally disagree. The pipeline
  retains both the official event state and the reconstructed on-ice state.
- A carryover goal is never silently rewritten. It retains its official state
  plus `prior_state`, `seconds_since_state_change`, and a carryover flag.
- Empty-net and delayed-penalty situations remain distinguishable through
  separate skater-count and goalie-presence fields.
- MoneyPuck data requires attribution and is subject to its published usage
  terms. This project reads only its documented downloadable files.

