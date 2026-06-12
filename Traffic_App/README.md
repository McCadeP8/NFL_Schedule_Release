# Elysium Traffic Accident Insights

A professional Streamlit application for exploring car accident frequency, severity,
risk factors, and geographic patterns for Elysium Wealth Management.

## Project Structure

```text
Traffic_App/
|-- app.py              # Streamlit user interface
|-- data.py             # Data loading and access utilities
|-- data/               # Optional default accident dataset
|-- requirements.txt    # Python dependencies
`-- README.md
```

## Getting Started

Create and activate a Python virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Launch the application:

```powershell
streamlit run app.py
```

Load the official FARS and Census datasets:

```powershell
python ingest.py
```

The ingestion command downloads nationwide FARS fatal-crash records for 2019-2023
and 2023 Census County Business Patterns for target commercial-driving industries.
It normalizes the data into `data/traffic_data.sqlite`, which is intentionally excluded
from source control.

The refresh also creates clean CSV exports in `data/exports/` for analysis in R:

- `fars_crashes_2019_2023.csv`
- `county_target_industries_2023.csv`
- `county_population_2020_2024.csv`
- `county_marketing_analytics.csv`
- `utah_crashes_2019_2024.csv.gz`
- `utah_county_crash_analytics_2019_2024.csv`

Start with `analysis/eda_starter.R` and `analysis/DATA_DICTIONARY.md`.

The pipeline also loads UDOT's anonymized Utah Crash Locations service for all reported
crash severities from 2019-2024. UDOT refreshes the public service nightly; recent-year
records may be preliminary or delayed, so the app intentionally uses completed years.

The app accepts CSV and Excel files from the sidebar. A default dataset may also be
placed at `data/accidents.csv`.

## Brand

- Company: Elysium Wealth Management
- Primary navy: `#213F57`
- Accent aqua: `#31D5D0`
- Neutral: `#FFFFFF`
