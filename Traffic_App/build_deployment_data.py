"""Build compact, repository-friendly data files for Streamlit Cloud."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).parent
DATABASE_PATH = ROOT / "data" / "traffic_data.sqlite"
DEPLOY_DIRECTORY = ROOT / "data" / "deploy"

TABLE_COLUMNS = {
    "fars_crashes": [
        "case_id",
        "year",
        "state_code",
        "state",
        "fatalities",
        "work_zone",
        "weather",
        "light_condition",
        "latitude",
        "longitude",
        "commercial_vehicle_involved",
        "large_truck_bus_involved",
    ],
    "county_business_patterns": [
        "state_fips",
        "industry",
        "establishments",
        "employees",
    ],
    "data_sources": [
        "dataset",
        "description",
        "years",
        "records",
        "refreshed_at",
        "source_url",
    ],
    "county_marketing_analytics": [
        "year",
        "state",
        "county_name",
        "population",
        "fatal_crashes",
        "fatalities",
        "commercial_involved_crashes",
        "fatal_crashes_per_100k",
        "target_establishments",
        "target_industry_employees",
    ],
    "utah_crashes": [
        "crash_id",
        "year",
        "county_name",
        "number_fatalities",
        "motor_carrier_involved_yn",
        "commercial_motor_veh_involved",
        "work_zone_related_ynu",
        "weather_condition_desc",
        "light_condition_desc",
        "latitude",
        "longitude",
        "crash_severity_desc",
        "number_four_injuries",
        "speed_related",
        "distracted_driving",
        "dui",
        "main_road_name",
        "route_id",
        "location_desc",
        "manner_collision_desc",
        "number_vehicles_involved",
    ],
    "utah_county_crash_analytics": [
        "year",
        "county_geoid",
        "county_name",
        "population",
        "all_crashes",
        "all_crashes_per_100k",
        "injury_crashes",
        "injury_crashes_per_100k",
        "suspected_serious_injury_crashes",
        "fatal_crashes",
        "fatalities",
        "motor_carrier_crashes",
        "commercial_vehicle_crashes",
        "target_establishments",
        "target_industry_employees",
    ],
}


def build_deployment_data() -> None:
    """Export only the fields required by the deployed Streamlit app."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Run `python ingest.py` before building deployment data.")

    DEPLOY_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as connection:
        for table, columns in TABLE_COLUMNS.items():
            selected = ", ".join(f'"{column}"' for column in columns)
            frame = pd.read_sql_query(f'SELECT {selected} FROM "{table}"', connection)
            destination = DEPLOY_DIRECTORY / f"{table}.csv.gz"
            frame.to_csv(destination, index=False, compression="gzip")
            print(f"{table}: {len(frame):,} rows -> {destination.stat().st_size / 1_000_000:.2f} MB")


if __name__ == "__main__":
    build_deployment_data()

