"""Download and normalize official crash and market-opportunity datasets."""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd


DATA_DIRECTORY = Path(__file__).parent / "data"
RAW_DIRECTORY = DATA_DIRECTORY / "raw"
DATABASE_PATH = DATA_DIRECTORY / "traffic_data.sqlite"
EXPORT_DIRECTORY = DATA_DIRECTORY / "exports"

FARS_URL = (
    "https://static.nhtsa.gov/nhtsa/downloads/FARS/{year}/National/"
    "FARS{year}NationalCSV.zip"
)
CENSUS_CBP_URL = (
    "https://www2.census.gov/programs-surveys/cbp/datasets/{year}/cbp{short_year}co.zip"
)
CENSUS_POPULATION_URL = (
    "https://www2.census.gov/programs-surveys/popest/datasets/2020-2024/"
    "counties/totals/co-est2024-alldata.csv"
)
UTAH_CRASH_SERVICE = (
    "https://services.arcgis.com/pA2nEVnB6tquxgOW/arcgis/rest/services/"
    "Utah_Crash_Locations/FeatureServer"
)
UTAH_CRASH_LAYERS = {
    2019: 7,
    2020: 6,
    2021: 5,
    2022: 4,
    2023: 3,
    2024: 2,
}

TARGET_INDUSTRIES = {
    "238": "Specialty Trade Contractors",
    "484": "Truck Transportation",
    "492": "Couriers and Messengers",
    "561730": "Landscaping Services",
}


def download_file(url: str, destination: Path) -> Path:
    """Download a file once and reuse the local copy on future refreshes."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return destination

    print(f"Downloading {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "ElysiumTrafficAnalytics/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        destination.write_bytes(response.read())
    return destination


def fetch_arcgis_page(layer_id: int, offset: int, page_size: int = 2000) -> dict:
    """Fetch one page from Utah's official anonymized crash feature service."""
    parameters = urllib.parse.urlencode(
        {
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "orderByFields": "OBJECTID",
            "f": "json",
        }
    )
    url = f"{UTAH_CRASH_SERVICE}/{layer_id}/query?{parameters}"
    request = urllib.request.Request(url, headers={"User-Agent": "ElysiumTrafficAnalytics/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    return {}


def load_utah_crash_year(year: int, layer_id: int) -> pd.DataFrame:
    """Load one completed year of all reported Utah crashes."""
    cache_path = RAW_DIRECTORY / f"utah_crashes_{year}.csv"
    if cache_path.exists():
        return pd.read_csv(cache_path, low_memory=False)

    print(f"Downloading Utah all-crash records: {year}")
    rows: list[dict] = []
    offset = 0
    while True:
        payload = fetch_arcgis_page(layer_id, offset)
        features = payload.get("features", [])
        if not features:
            break
        for feature in features:
            row = feature.get("attributes", {}).copy()
            geometry = feature.get("geometry", {})
            row["longitude"] = geometry.get("x")
            row["latitude"] = geometry.get("y")
            row["year"] = year
            rows.append(row)
        offset += len(features)
        print(f"  {offset:,} records")
        if len(features) < 2000:
            break

    crashes = pd.DataFrame(rows)
    if "crash_datetime" in crashes:
        crashes["crash_datetime"] = pd.to_datetime(
            crashes["crash_datetime"], unit="ms", errors="coerce", utc=True
        ).dt.strftime("%Y-%m-%d %H:%M:%S")
    crashes.to_csv(cache_path, index=False)
    return crashes


def find_zip_member(archive: zipfile.ZipFile, file_name: str) -> str:
    """Find a case-insensitive CSV filename within a FARS archive."""
    matches = [
        name
        for name in archive.namelist()
        if Path(name).name.lower() == file_name.lower()
    ]
    if not matches:
        raise FileNotFoundError(f"{file_name} was not found in the FARS archive.")
    return matches[0]


def clean_coordinate(series: pd.Series, maximum: float) -> pd.Series:
    """Remove FARS coordinate sentinel values and impossible coordinates."""
    coordinates = pd.to_numeric(series, errors="coerce")
    return coordinates.where(coordinates.abs() <= maximum)


def load_fars_year(year: int) -> pd.DataFrame:
    """Download and normalize one year of nationwide FARS crash data."""
    archive_path = download_file(
        FARS_URL.format(year=year),
        RAW_DIRECTORY / f"FARS{year}NationalCSV.zip",
    )

    with zipfile.ZipFile(archive_path) as archive:
        accident = pd.read_csv(
            archive.open(find_zip_member(archive, "accident.csv")),
            encoding="latin1",
            low_memory=False,
        )
        vehicle = pd.read_csv(
            archive.open(find_zip_member(archive, "vehicle.csv")),
            encoding="latin1",
            low_memory=False,
            usecols=lambda column: column
            in {"ST_CASE", "MCARR_IDNAME", "BODY_TYPNAME", "V_CONFIGNAME"},
        )
    accident.columns = [column.lstrip("\ufeffï»¿") for column in accident.columns]
    vehicle.columns = [column.lstrip("\ufeffï»¿") for column in vehicle.columns]

    carrier_name = vehicle.get("MCARR_IDNAME", pd.Series(index=vehicle.index, dtype="object"))
    valid_carrier = ~carrier_name.fillna("Unknown").isin(
        {"Not Applicable", "Unknown", "Not Reported"}
    )
    body_description = vehicle.get(
        "BODY_TYPNAME", pd.Series(index=vehicle.index, dtype="object")
    ).fillna("")
    configuration = vehicle.get(
        "V_CONFIGNAME", pd.Series(index=vehicle.index, dtype="object")
    ).fillna("")
    large_truck_or_bus = (
        body_description.str.contains(
            "truck-tractor|straight truck|medium/heavy|bus", case=False, regex=True
        )
        | configuration.str.contains(
            "truck|tractor|bus", case=False, regex=True
        )
    )

    vehicle_flags = (
        pd.DataFrame(
            {
                "ST_CASE": vehicle["ST_CASE"],
                "commercial_vehicle_involved": valid_carrier.astype(int),
                "large_truck_bus_involved": large_truck_or_bus.astype(int),
            }
        )
        .groupby("ST_CASE", as_index=False)
        .max()
    )

    crashes = accident.merge(vehicle_flags, on="ST_CASE", how="left")
    crashes["latitude"] = clean_coordinate(crashes["LATITUDE"], 90)
    crashes["longitude"] = clean_coordinate(crashes["LONGITUD"], 180)
    crashes["crash_date"] = pd.to_datetime(
        dict(
            year=pd.to_numeric(crashes["YEAR"], errors="coerce"),
            month=pd.to_numeric(crashes["MONTH"], errors="coerce"),
            day=pd.to_numeric(crashes["DAY"], errors="coerce"),
        ),
        errors="coerce",
    ).dt.strftime("%Y-%m-%d")

    normalized = pd.DataFrame(
        {
            "case_id": crashes["ST_CASE"],
            "year": year,
            "crash_date": crashes["crash_date"],
            "state_code": crashes["STATE"],
            "state": crashes["STATENAME"],
            "county_code": crashes["COUNTY"],
            "county": crashes["COUNTYNAME"],
            "city": crashes["CITYNAME"],
            "latitude": crashes["latitude"],
            "longitude": crashes["longitude"],
            "fatalities": crashes["FATALS"],
            "vehicles": crashes["VE_TOTAL"],
            "persons": crashes["PERSONS"],
            "roadway": crashes["TWAY_ID"],
            "route_type": crashes["ROUTENAME"],
            "urban_rural": crashes["RUR_URBNAME"],
            "weather": crashes["WEATHERNAME"],
            "light_condition": crashes["LGT_CONDNAME"],
            "work_zone": crashes["WRK_ZONENAME"],
            "commercial_vehicle_involved": crashes[
                "commercial_vehicle_involved"
            ].fillna(0),
            "large_truck_bus_involved": crashes[
                "large_truck_bus_involved"
            ].fillna(0),
        }
    )
    return normalized


def load_cbp_year(year: int) -> pd.DataFrame:
    """Load nationwide county business counts for target industries."""
    archive_path = download_file(
        CENSUS_CBP_URL.format(year=year, short_year=str(year)[-2:]),
        RAW_DIRECTORY / f"cbp{str(year)[-2:]}co.zip",
    )
    archive_codes = {
        "238///": ("238", TARGET_INDUSTRIES["238"]),
        "484///": ("484", TARGET_INDUSTRIES["484"]),
        "492///": ("492", TARGET_INDUSTRIES["492"]),
        "561730": ("561730", TARGET_INDUSTRIES["561730"]),
    }
    with zipfile.ZipFile(archive_path) as archive:
        member = next(name for name in archive.namelist() if name.lower().endswith(".txt"))
        businesses = pd.read_csv(
            archive.open(member),
            dtype={"fipstate": str, "fipscty": str, "naics": str},
            low_memory=False,
        )
    businesses = businesses[businesses["naics"].isin(archive_codes)].copy()
    businesses["industry_code"] = businesses["naics"].map(
        lambda code: archive_codes[code][0]
    )
    businesses["industry"] = businesses["naics"].map(
        lambda code: archive_codes[code][1]
    )
    businesses = businesses.rename(
        columns={
            "est": "establishments",
            "emp": "employees",
            "ap": "annual_payroll_thousands",
            "fipstate": "state_fips",
            "fipscty": "county_fips",
        }
    )
    businesses["year"] = year
    businesses["county_name"] = ""
    for column in ("establishments", "employees", "annual_payroll_thousands"):
        businesses[column] = pd.to_numeric(businesses[column], errors="coerce")
    businesses["state_fips"] = businesses["state_fips"].str.zfill(2)
    businesses["county_fips"] = businesses["county_fips"].str.zfill(3)
    businesses["county_geoid"] = businesses["state_fips"] + businesses["county_fips"]
    return businesses[
        [
            "year",
            "county_geoid",
            "state_fips",
            "county_fips",
            "county_name",
            "industry_code",
            "industry",
            "establishments",
            "employees",
            "annual_payroll_thousands",
        ]
    ]


def load_county_population() -> pd.DataFrame:
    """Load official 2020-2024 Census county population estimates."""
    population_path = download_file(
        CENSUS_POPULATION_URL,
        RAW_DIRECTORY / "co-est2024-alldata.csv",
    )
    population = pd.read_csv(population_path, encoding="latin1", low_memory=False)
    population = population[population["SUMLEV"] == 50].copy()
    population["state_fips"] = population["STATE"].astype(str).str.zfill(2)
    population["county_fips"] = population["COUNTY"].astype(str).str.zfill(3)
    population["county_geoid"] = population["state_fips"] + population["county_fips"]

    year_columns = [f"POPESTIMATE{year}" for year in range(2020, 2025)]
    return population[
        ["county_geoid", "state_fips", "county_fips", "STNAME", "CTYNAME", *year_columns]
    ].rename(
        columns={
            "STNAME": "state",
            "CTYNAME": "county_name",
            **{f"POPESTIMATE{year}": f"population_{year}" for year in range(2020, 2025)},
        }
    )


def build_county_analytics(
    crashes: pd.DataFrame,
    businesses: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """Create a clean county-level analytical mart for EDA."""
    crash_summary = (
        crashes.assign(
            state_fips=crashes["state_code"].astype(int).astype(str).str.zfill(2),
            county_fips=crashes["county_code"].astype(int).astype(str).str.zfill(3),
        )
        .assign(county_geoid=lambda frame: frame["state_fips"] + frame["county_fips"])
        .groupby(["year", "county_geoid"], as_index=False)
        .agg(
            fatal_crashes=("case_id", "count"),
            fatalities=("fatalities", "sum"),
            commercial_involved_crashes=("commercial_vehicle_involved", "sum"),
            large_truck_bus_crashes=("large_truck_bus_involved", "sum"),
        )
    )
    business_summary = businesses.groupby("county_geoid", as_index=False).agg(
        target_establishments=("establishments", "sum"),
        target_industry_employees=("employees", "sum"),
        target_annual_payroll_thousands=("annual_payroll_thousands", "sum"),
    )

    analytics = crash_summary.merge(population, on="county_geoid", how="left")
    analytics = analytics.merge(business_summary, on="county_geoid", how="left")
    analytics["population"] = analytics.apply(
        lambda row: row.get(f"population_{int(row['year'])}", pd.NA),
        axis=1,
    )
    analytics["population"] = pd.to_numeric(analytics["population"], errors="coerce")
    analytics["fatal_crashes_per_100k"] = (
        analytics["fatal_crashes"] / analytics["population"] * 100_000
    )
    analytics["fatalities_per_100k"] = (
        analytics["fatalities"] / analytics["population"] * 100_000
    )
    analytics["commercial_share"] = (
        analytics["commercial_involved_crashes"] / analytics["fatal_crashes"]
    )
    return analytics


def build_utah_county_analytics(
    utah_crashes: pd.DataFrame,
    businesses: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """Create a complete all-severity Utah county-year analytical mart."""
    utah_population = population[population["state_fips"] == "49"].copy()
    utah_population["county_join_key"] = (
        utah_population["county_name"]
        .str.replace(r"\s+County$", "", regex=True)
        .str.upper()
    )
    utah_businesses = (
        businesses[businesses["state_fips"] == "49"]
        .groupby("county_geoid", as_index=False)
        .agg(
            target_establishments=("establishments", "sum"),
            target_industry_employees=("employees", "sum"),
            target_annual_payroll_thousands=("annual_payroll_thousands", "sum"),
        )
    )

    crashes = utah_crashes.copy()
    crashes["county_join_key"] = crashes["county_name"].str.upper()
    yes = lambda column: crashes[column].eq("Y").astype(int)
    crashes["injury_crash"] = crashes["crash_severity_desc"].ne("No Injury/PDO").astype(int)
    crashes["property_damage_only_crash"] = crashes["crash_severity_desc"].eq("No Injury/PDO").astype(int)
    crashes["fatal_crash"] = crashes["crash_severity_desc"].eq("Fatal").astype(int)
    crashes["suspected_serious_injury_crash"] = crashes["crash_severity_desc"].eq(
        "Suspected Serious Injury"
    ).astype(int)
    crashes["motor_carrier_crash"] = yes("motor_carrier_involved_yn")
    crashes["commercial_vehicle_crash"] = yes("commercial_motor_veh_involved")
    for source, target in (
        ("dui", "dui_crash"),
        ("distracted_driving", "distracted_driving_crash"),
        ("speed_related", "speed_related_crash"),
        ("pedestrian_involved", "pedestrian_crash"),
        ("bicyclist_involved", "bicyclist_crash"),
        ("motorcycle_involved", "motorcycle_crash"),
        ("work_zone_related_ynu", "work_zone_crash"),
    ):
        crashes[target] = yes(source)

    summary = (
        crashes.groupby(["year", "county_join_key"], as_index=False)
        .agg(
            all_crashes=("crash_id", "count"),
            property_damage_only_crashes=("property_damage_only_crash", "sum"),
            injury_crashes=("injury_crash", "sum"),
            suspected_serious_injury_crashes=("suspected_serious_injury_crash", "sum"),
            fatal_crashes=("fatal_crash", "sum"),
            fatalities=("number_fatalities", "sum"),
            motor_carrier_crashes=("motor_carrier_crash", "sum"),
            commercial_vehicle_crashes=("commercial_vehicle_crash", "sum"),
            dui_crashes=("dui_crash", "sum"),
            distracted_driving_crashes=("distracted_driving_crash", "sum"),
            speed_related_crashes=("speed_related_crash", "sum"),
            pedestrian_crashes=("pedestrian_crash", "sum"),
            bicyclist_crashes=("bicyclist_crash", "sum"),
            motorcycle_crashes=("motorcycle_crash", "sum"),
            work_zone_crashes=("work_zone_crash", "sum"),
        )
    )

    analytics = summary.merge(
        utah_population,
        on="county_join_key",
        how="left",
        validate="many_to_one",
    ).merge(utah_businesses, on="county_geoid", how="left", validate="many_to_one")
    analytics["population"] = analytics.apply(
        lambda row: row.get(f"population_{int(row['year'])}", pd.NA),
        axis=1,
    )
    analytics["population"] = pd.to_numeric(analytics["population"], errors="coerce")
    for metric in (
        "all_crashes",
        "injury_crashes",
        "suspected_serious_injury_crashes",
        "fatal_crashes",
        "motor_carrier_crashes",
        "commercial_vehicle_crashes",
    ):
        analytics[f"{metric}_per_100k"] = analytics[metric] / analytics["population"] * 100_000
    analytics["injury_crash_share"] = analytics["injury_crashes"] / analytics["all_crashes"]
    analytics["motor_carrier_share"] = analytics["motor_carrier_crashes"] / analytics["all_crashes"]
    analytics["commercial_vehicle_share"] = (
        analytics["commercial_vehicle_crashes"] / analytics["all_crashes"]
    )
    return analytics.drop(columns=["county_join_key"])


def export_analysis_files(
    crashes: pd.DataFrame,
    businesses: pd.DataFrame,
    population: pd.DataFrame,
    county_analytics: pd.DataFrame,
    utah_crashes: pd.DataFrame,
    utah_county_analytics: pd.DataFrame,
) -> None:
    """Export clean, analysis-ready CSV files for R and other tools."""
    EXPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    crashes.to_csv(EXPORT_DIRECTORY / "fars_crashes_2019_2023.csv", index=False)
    businesses.to_csv(EXPORT_DIRECTORY / "county_target_industries_2023.csv", index=False)
    population.to_csv(EXPORT_DIRECTORY / "county_population_2020_2024.csv", index=False)
    county_analytics.to_csv(EXPORT_DIRECTORY / "county_marketing_analytics.csv", index=False)
    utah_county_analytics.to_csv(
        EXPORT_DIRECTORY / "utah_county_crash_analytics_2019_2024.csv", index=False
    )
    utah_crashes.to_csv(
        EXPORT_DIRECTORY / "utah_crashes_2019_2024.csv.gz",
        index=False,
        compression="gzip",
    )


def write_database(fars_years: list[int], cbp_year: int) -> None:
    """Refresh the normalized SQLite database."""
    DATA_DIRECTORY.mkdir(exist_ok=True)
    print(f"Loading FARS years: {', '.join(map(str, fars_years))}")
    crashes = pd.concat([load_fars_year(year) for year in fars_years], ignore_index=True)
    print(f"Loading Census County Business Patterns: {cbp_year}")
    businesses = load_cbp_year(cbp_year)
    print("Loading Census county population estimates: 2020-2024")
    population = load_county_population()
    county_analytics = build_county_analytics(crashes, businesses, population)
    print("Loading UDOT all-crash records: 2019-2024")
    utah_crashes = pd.concat(
        [
            load_utah_crash_year(year, layer_id)
            for year, layer_id in UTAH_CRASH_LAYERS.items()
        ],
        ignore_index=True,
    )
    utah_county_analytics = build_utah_county_analytics(
        utah_crashes, businesses, population
    )

    refreshed_at = datetime.now(UTC).isoformat()
    sources = pd.DataFrame(
        [
            {
                "dataset": "NHTSA FARS",
                "description": "Nationwide census of fatal motor vehicle crashes",
                "years": f"{min(fars_years)}-{max(fars_years)}",
                "records": len(crashes),
                "refreshed_at": refreshed_at,
                "source_url": "https://www.nhtsa.gov/research-data/fatality-analysis-reporting-system-fars",
            },
            {
                "dataset": "Census County Business Patterns",
                "description": "County establishments and employment in target industries",
                "years": str(cbp_year),
                "records": len(businesses),
                "refreshed_at": refreshed_at,
                "source_url": "https://www.census.gov/programs-surveys/cbp.html",
            },
            {
                "dataset": "Census Population Estimates",
                "description": "Annual county population estimates for rate denominators",
                "years": "2020-2024",
                "records": len(population),
                "refreshed_at": refreshed_at,
                "source_url": "https://www.census.gov/programs-surveys/popest.html",
            },
            {
                "dataset": "UDOT Utah Crash Locations",
                "description": "Anonymized locations and characteristics for all reported Utah crashes",
                "years": "2019-2024",
                "records": len(utah_crashes),
                "refreshed_at": refreshed_at,
                "source_url": UTAH_CRASH_SERVICE,
            },
        ]
    )

    with sqlite3.connect(DATABASE_PATH) as connection:
        crashes.to_sql("fars_crashes", connection, if_exists="replace", index=False)
        businesses.to_sql(
            "county_business_patterns", connection, if_exists="replace", index=False
        )
        sources.to_sql("data_sources", connection, if_exists="replace", index=False)
        population.to_sql("county_population", connection, if_exists="replace", index=False)
        county_analytics.to_sql(
            "county_marketing_analytics", connection, if_exists="replace", index=False
        )
        utah_crashes.to_sql("utah_crashes", connection, if_exists="replace", index=False)
        utah_county_analytics.to_sql(
            "utah_county_crash_analytics", connection, if_exists="replace", index=False
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_fars_state_year "
            "ON fars_crashes(state, year)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_cbp_county "
            "ON county_business_patterns(county_geoid)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_utah_crashes_year_county "
            "ON utah_crashes(year, county_name)"
        )

    export_analysis_files(
        crashes,
        businesses,
        population,
        county_analytics,
        utah_crashes,
        utah_county_analytics,
    )
    print(f"Created {DATABASE_PATH}")
    print(f"FARS crashes: {len(crashes):,}")
    print(f"Business-market records: {len(businesses):,}")
    print(f"County analytical records: {len(county_analytics):,}")
    print(f"Utah all-crash records: {len(utah_crashes):,}")
    print(f"Utah county-year analytical records: {len(utah_county_analytics):,}")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fars-years",
        nargs="+",
        type=int,
        default=list(range(2019, 2024)),
        help="FARS years to load. Defaults to 2019 through 2023.",
    )
    parser.add_argument(
        "--cbp-year",
        type=int,
        default=2023,
        help="Census County Business Patterns year. Defaults to 2023.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    write_database(arguments.fars_years, arguments.cbp_year)
