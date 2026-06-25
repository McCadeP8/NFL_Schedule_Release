# Astrix Law Traffic Accident Insights

A professional Streamlit application for exploring car accident frequency, severity,
risk factors, and geographic patterns for Astrix Law.

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
- `all_state_crashes_2019_2024.csv.gz`
- `all_state_county_crash_analytics_2019_2024.csv`
- `all_crash_source_status.csv`

Start with `analysis/eda_starter.R` and `analysis/DATA_DICTIONARY.md`.

The pipeline also loads automated all-severity crash sources where official public APIs
are available. Current automated all-crash states are Utah and Virginia:

- Utah: UDOT anonymized Utah Crash Locations FeatureServer, 2019-2024.
- Virginia: Virginia Roads/VDOT Full_Crash FeatureServer sourced from DMV TREDS, 2019-2024.

Other priority states are tracked in `all_crash_source_status.csv`; most require portal
access, a formal data request, or source-specific credential review before they can be
loaded responsibly.

To rebuild the compact data bundle committed for Streamlit Cloud:

```powershell
python build_deployment_data.py
```

The app reads the full SQLite database locally and automatically falls back to the
compressed files in `data/deploy/` when deployed without SQLite.

The app accepts CSV and Excel files from the sidebar. A default dataset may also be
placed at `data/accidents.csv`.

## Brand

- Company: Astrix Law
- Primary blue: `#2596BE`
- Secondary gold: `#FBAD41`
- Neutral: `#FFFFFF`
