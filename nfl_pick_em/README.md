# NFL Pick'em Streamlit Prototype

This is a small Streamlit app for a Week 1 NFL pick'em pool.

It reads games from the public Google Sheet CSV, filters to `GameID` values that start with `2026_` and `Week = 1`, lets users pick a winner for each game, and saves submissions to a local SQLite database at:

```text
data/pickem_results.sqlite
```

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What saves today

Each submission stores:

- player name
- optional email
- season and week
- tiebreaker total points
- one selected winner per game
- optional confidence score per game
- submission timestamp

You can view saved submissions in the app and download them as CSV.

## Publishing notes

This can be published to Streamlit Community Cloud as-is, but the local SQLite file is best for prototyping. For a real public pool where submissions need to survive redeploys and multiple server instances, use a hosted database such as Supabase, Neon/Postgres, Firebase, or a private Google Sheet write-back.

The UI and app logic are already separated enough that the `save_submission()` and `load_submissions()` functions are the only pieces you would need to swap for a hosted backend.
