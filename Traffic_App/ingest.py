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
VIRGINIA_CRASH_SERVICE = (
    "https://services.arcgis.com/p5v98VHDX9Atv3l7/arcgis/rest/services/"
    "Full_Crash/FeatureServer"
)
UTAH_CRASH_LAYERS = {
    2019: 7,
    2020: 6,
    2021: 5,
    2022: 4,
    2023: 3,
    2024: 2,
}
ALL_CRASH_YEARS = list(range(2019, 2025))

TARGET_STATE_TIERS = {
    "Tier 1": [
        "Oklahoma",
        "Pennsylvania",
        "Kentucky",
        "Louisiana",
        "Nebraska",
        "New Jersey",
        "Tennessee",
        "Virginia",
    ],
    "Tier 2": ["Texas", "Georgia", "Illinois", "New Mexico"],
    "Tier 3": ["Arkansas", "Florida", "Indiana", "Missouri"],
}

ALL_CRASH_SOURCE_STATUS = [
    {
        "state": "Utah",
        "tier": "Existing pilot",
        "status": "Automated",
        "source_name": "UDOT Utah Crash Locations",
        "source_url": UTAH_CRASH_SERVICE,
        "notes": "Official anonymized all-severity crash FeatureServer, loaded by year.",
    },
    {
        "state": "Virginia",
        "tier": "Tier 1",
        "status": "Automated",
        "source_name": "Virginia Roads Full_Crash",
        "source_url": VIRGINIA_CRASH_SERVICE,
        "notes": "Official Virginia Roads/VDOT crash FeatureServer sourced from DMV TREDS.",
    },
    {
        "state": "Florida",
        "tier": "Tier 3",
        "status": "Portal / credential review",
        "source_name": "Signal Four Analytics / Florida crash systems",
        "source_url": "https://s4.geoplan.ufl.edu/",
        "notes": "Strong crash system, but public bulk API access needs user/account verification.",
    },
    {
        "state": "Texas",
        "tier": "Tier 2",
        "status": "Portal / request",
        "source_name": "TxDOT CRIS",
        "source_url": "https://cris.dot.state.tx.us/",
        "notes": "Authoritative source; statewide bulk access is governed by CRIS export/request rules.",
    },
    {
        "state": "Pennsylvania",
        "tier": "Tier 1",
        "status": "Needs source negotiation",
        "source_name": "PennDOT crash systems",
        "source_url": "https://www.penndot.pa.gov/",
        "notes": "Official data exists, but a statewide public bulk API was not confirmed.",
    },
    {
        "state": "Kentucky",
        "tier": "Tier 1",
        "status": "Needs source negotiation",
        "source_name": "Kentucky crash systems",
        "source_url": "https://transportation.ky.gov/",
        "notes": "Mature state crash ecosystem; bulk public API/export still needs confirmation.",
    },
    {
        "state": "Indiana",
        "tier": "Tier 3",
        "status": "Needs source negotiation",
        "source_name": "Indiana ARIES / traffic safety systems",
        "source_url": "https://www.in.gov/",
        "notes": "Crash data exists; automated public statewide endpoint was not confirmed.",
    },
    {
        "state": "Louisiana",
        "tier": "Tier 1",
        "status": "Needs source negotiation",
        "source_name": "Louisiana DOTD / LSU CARTS crash systems",
        "source_url": "https://www.crashdata.lsu.edu/",
        "notes": "Crash data exists; likely portal or request-mediated for bulk records.",
    },
    {
        "state": "Nebraska",
        "tier": "Tier 1",
        "status": "Needs source negotiation",
        "source_name": "Nebraska DOT crash data",
        "source_url": "https://dot.nebraska.gov/",
        "notes": "Public summaries exist; raw crash-level automation not confirmed.",
    },
    {
        "state": "New Jersey",
        "tier": "Tier 1",
        "status": "Needs source negotiation",
        "source_name": "NJDOT / NJ crash records",
        "source_url": "https://www.nj.gov/transportation/",
        "notes": "Crash records exist; statewide bulk access may require request or portal approval.",
    },
    {
        "state": "Tennessee",
        "tier": "Tier 1",
        "status": "Needs source negotiation",
        "source_name": "Tennessee TITAN crash system",
        "source_url": "https://www.tn.gov/safety.html",
        "notes": "Authoritative data is in TITAN; bulk public API access was not confirmed.",
    },
    {
        "state": "Georgia",
        "tier": "Tier 2",
        "status": "Needs source negotiation",
        "source_name": "Georgia crash systems / GEARS",
        "source_url": "https://www.dot.ga.gov/",
        "notes": "Crash records exist; statewide automated bulk pull likely requires permission.",
    },
    {
        "state": "Illinois",
        "tier": "Tier 2",
        "status": "Needs source negotiation",
        "source_name": "Illinois DOT crash data",
        "source_url": "https://idot.illinois.gov/",
        "notes": "Statewide data exists, but a public crash-level API was not confirmed.",
    },
    {
        "state": "New Mexico",
        "tier": "Tier 2",
        "status": "Needs source negotiation",
        "source_name": "NMDOT / UNM traffic safety data",
        "source_url": "https://gps.unm.edu/",
        "notes": "Strong traffic safety reporting; raw crash-level automation needs confirmation.",
    },
    {
        "state": "Arkansas",
        "tier": "Tier 3",
        "status": "Needs source negotiation",
        "source_name": "Arkansas crash records",
        "source_url": "https://www.ardot.gov/",
        "notes": "Crash data exists; public bulk access was not confirmed.",
    },
    {
        "state": "Missouri",
        "tier": "Tier 3",
        "status": "Needs source negotiation",
        "source_name": "Missouri MSHP / MoDOT crash systems",
        "source_url": "https://www.mshp.dps.missouri.gov/",
        "notes": "Crash systems exist; public statewide bulk API needs confirmation.",
    },
]

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
    request = urllib.request.Request(url, headers={"User-Agent": "TrafficAccidentAnalytics/1.0"})
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
    request = urllib.request.Request(url, headers={"User-Agent": "TrafficAccidentAnalytics/1.0"})
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


def fetch_arcgis_layer_metadata(service_url: str, layer_id: int) -> dict:
    """Fetch ArcGIS layer metadata, including coded-value domains."""
    url = f"{service_url}/{layer_id}?f=json"
    request = urllib.request.Request(url, headers={"User-Agent": "TrafficAnalytics/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload


def domain_maps(layer_metadata: dict) -> dict[str, dict[str, str]]:
    """Build field-level coded-value lookup maps from ArcGIS metadata."""
    maps: dict[str, dict[str, str]] = {}
    for field in layer_metadata.get("fields", []):
        domain = field.get("domain") or {}
        coded_values = domain.get("codedValues") or []
        if coded_values:
            maps[field["name"]] = {
                str(item.get("code")): str(item.get("name"))
                for item in coded_values
            }
    return maps


def decode_domain_value(value: object, lookup: dict[str, str]) -> object:
    """Decode an ArcGIS coded value while preserving non-coded values."""
    if pd.isna(value):
        return value
    text = str(value)
    if text in lookup:
        return lookup[text]
    try:
        integer_text = str(int(float(text)))
    except (TypeError, ValueError):
        integer_text = text
    return lookup.get(integer_text, value)


def yes_flag(series: pd.Series) -> pd.Series:
    """Normalize common yes/no encodings to 1/0 flags."""
    values = series.fillna("").astype(str).str.strip().str.lower()
    return values.isin({"y", "yes", "1", "true"}).astype(int)


def fetch_arcgis_features(
    service_url: str,
    layer_id: int,
    where: str,
    cache_path: Path,
    order_field: str = "OBJECTID",
    page_size: int = 2000,
) -> pd.DataFrame:
    """Fetch and cache rows from a public ArcGIS FeatureServer layer."""
    if cache_path.exists():
        return pd.read_csv(cache_path, low_memory=False)

    print(f"Downloading ArcGIS records: {cache_path.name}")
    rows: list[dict] = []
    offset = 0
    while True:
        parameters = urllib.parse.urlencode(
            {
                "where": where,
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": offset,
                "resultRecordCount": page_size,
                "orderByFields": order_field,
                "f": "json",
            }
        )
        url = f"{service_url}/{layer_id}/query?{parameters}"
        request = urllib.request.Request(url, headers={"User-Agent": "TrafficAnalytics/1.0"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    payload = json.load(response)
                if "error" in payload:
                    raise RuntimeError(payload["error"])
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 ** attempt)
        features = payload.get("features", [])
        if not features:
            break
        for feature in features:
            row = feature.get("attributes", {}).copy()
            geometry = feature.get("geometry", {})
            row["longitude"] = geometry.get("x")
            row["latitude"] = geometry.get("y")
            rows.append(row)
        offset += len(features)
        print(f"  {offset:,} records")
        if len(features) < page_size:
            break

    frame = pd.DataFrame(rows)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(cache_path, index=False)
    return frame


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


def normalize_severity(value: object) -> str:
    """Map source severity labels into the app's five severity bands."""
    text = "" if pd.isna(value) else str(value).strip().lower()
    if text.startswith("k") or "fatal" in text:
        return "Fatal"
    if text.startswith("a") or "serious" in text or "severe" in text:
        return "Suspected Serious Injury"
    if text.startswith("b") or "minor" in text:
        return "Suspected Minor Injury"
    if text.startswith("c") or "possible" in text:
        return "Possible Injury"
    return "No Injury/PDO"


def normalize_utah_all_crashes(utah_crashes: pd.DataFrame) -> pd.DataFrame:
    """Convert raw UDOT crashes to the shared all-state crash schema."""
    if utah_crashes.empty:
        return pd.DataFrame()
    raw = utah_crashes.copy()
    normalized = pd.DataFrame(
        {
            "case_id": raw["crash_id"],
            "source_dataset": "UDOT Utah Crash Locations",
            "state_code": "49",
            "state": "Utah",
            "year": pd.to_numeric(raw["year"], errors="coerce"),
            "crash_datetime": raw.get("crash_datetime"),
            "county": raw["county_name"],
            "county_code": pd.NA,
            "fatalities": pd.to_numeric(raw["number_fatalities"], errors="coerce").fillna(0),
            "commercial_vehicle_involved": yes_flag(raw["motor_carrier_involved_yn"]),
            "large_truck_bus_involved": yes_flag(raw["commercial_motor_veh_involved"]),
            "work_zone": raw["work_zone_related_ynu"],
            "weather": raw["weather_condition_desc"],
            "light_condition": raw["light_condition_desc"],
            "latitude": pd.to_numeric(raw["latitude"], errors="coerce"),
            "longitude": pd.to_numeric(raw["longitude"], errors="coerce"),
            "crash_severity_desc": raw["crash_severity_desc"],
            "suspected_serious_injuries": pd.to_numeric(
                raw["number_four_injuries"], errors="coerce"
            ).fillna(0),
            "speed_related": yes_flag(raw["speed_related"]),
            "distracted_driving": yes_flag(raw["distracted_driving"]),
            "dui": yes_flag(raw["dui"]),
            "main_road_name": raw["main_road_name"],
            "route_id": raw["route_id"],
            "location_desc": raw["location_desc"],
            "manner_collision_desc": raw["manner_collision_desc"],
            "number_vehicles_involved": pd.to_numeric(
                raw["number_vehicles_involved"], errors="coerce"
            ),
        }
    )
    normalized["crash_date"] = pd.to_datetime(
        normalized["crash_datetime"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    normalized["injury_crash"] = normalized["crash_severity_desc"].ne("No Injury/PDO").astype(int)
    return normalized


def load_virginia_crash_year(year: int) -> pd.DataFrame:
    """Load one year of official all-severity Virginia crash records."""
    cache_path = RAW_DIRECTORY / f"virginia_crashes_{year}.csv"
    where = f"CRASH_YEAR='{year}'"
    raw = fetch_arcgis_features(
        VIRGINIA_CRASH_SERVICE,
        0,
        where,
        cache_path,
        page_size=16000,
    )
    raw["year"] = year
    return raw


def normalize_virginia_all_crashes(virginia_crashes: pd.DataFrame) -> pd.DataFrame:
    """Convert Virginia Roads Full_Crash rows to the shared all-state schema."""
    if virginia_crashes.empty:
        return pd.DataFrame()

    metadata = fetch_arcgis_layer_metadata(VIRGINIA_CRASH_SERVICE, 0)
    lookups = domain_maps(metadata)
    raw = virginia_crashes.copy()
    for column, lookup in lookups.items():
        if column in raw:
            raw[f"{column}_decoded"] = raw[column].map(lambda value: decode_domain_value(value, lookup))

    severity = raw.get("CRASH_SEVERITY_decoded", raw["CRASH_SEVERITY"]).map(normalize_severity)
    crash_datetime = pd.to_datetime(raw["CRASH_DT"], unit="ms", errors="coerce", utc=True)
    county = raw.get("PHYSICAL_JURIS_decoded", raw.get("PHYSICAL_JURIS", pd.Series(index=raw.index)))
    county = county.fillna(raw.get("JURIS_CODE_decoded", raw.get("JURIS_CODE", "")))
    normalized = pd.DataFrame(
        {
            "case_id": raw["DOCUMENT_NBR"],
            "source_dataset": "Virginia Roads Full_Crash",
            "state_code": "51",
            "state": "Virginia",
            "year": pd.to_numeric(raw["CRASH_YEAR"], errors="coerce"),
            "crash_datetime": crash_datetime.dt.strftime("%Y-%m-%d %H:%M:%S"),
            "crash_date": crash_datetime.dt.strftime("%Y-%m-%d"),
            "county": county.astype(str).str.replace(r"^\d+\.\s*", "", regex=True),
            "county_code": raw.get("JURIS_CODE"),
            "fatalities": pd.to_numeric(raw["K_PEOPLE"], errors="coerce").fillna(0),
            "commercial_vehicle_involved": yes_flag(
                raw.get("LGTRUCK_NONLGTRUCK_decoded", raw.get("LGTRUCK_NONLGTRUCK", ""))
            ),
            "large_truck_bus_involved": yes_flag(
                raw.get("LGTRUCK_NONLGTRUCK_decoded", raw.get("LGTRUCK_NONLGTRUCK", ""))
            ),
            "work_zone": raw.get("WORK_ZONE_RELATED_decoded", raw.get("WORK_ZONE_RELATED")),
            "weather": raw.get("WEATHER_CONDITION_decoded", raw.get("WEATHER_CONDITION")),
            "light_condition": raw.get("LIGHT_CONDITION_decoded", raw.get("LIGHT_CONDITION")),
            "latitude": pd.to_numeric(raw.get("LAT", raw.get("latitude")), errors="coerce"),
            "longitude": pd.to_numeric(raw.get("LON", raw.get("longitude")), errors="coerce"),
            "crash_severity_desc": severity,
            "suspected_serious_injuries": pd.to_numeric(raw["A_PEOPLE"], errors="coerce").fillna(0),
            "speed_related": yes_flag(raw.get("SPEED_NOTSPEED_decoded", raw.get("SPEED_NOTSPEED", ""))),
            "distracted_driving": yes_flag(
                raw.get("DISTRACTED_NOTDISTRACTED_decoded", raw.get("DISTRACTED_NOTDISTRACTED", ""))
            ),
            "dui": yes_flag(raw.get("ALCOHOL_NOTALCOHOL_decoded", raw.get("ALCOHOL_NOTALCOHOL", ""))),
            "main_road_name": raw.get("ROUTE_OR_STREET_NM"),
            "route_id": raw.get("RTE_NM"),
            "location_desc": raw.get("INTERSECTION_ANALYSIS_decoded", raw.get("INTERSECTION_ANALYSIS")),
            "manner_collision_desc": raw.get("COLLISION_TYPE_decoded", raw.get("COLLISION_TYPE")),
            "number_vehicles_involved": pd.to_numeric(raw["VEH_COUNT"], errors="coerce"),
        }
    )
    normalized["injury_crash"] = normalized["crash_severity_desc"].ne("No Injury/PDO").astype(int)
    return normalized


def load_all_state_crashes(
    utah_crashes: pd.DataFrame,
    years: list[int],
    include_virginia: bool = True,
) -> pd.DataFrame:
    """Load every all-severity state source that has an automated adapter."""
    frames = [normalize_utah_all_crashes(utah_crashes)]
    if include_virginia:
        virginia = pd.concat(
            [load_virginia_crash_year(year) for year in years],
            ignore_index=True,
        )
        frames.append(normalize_virginia_all_crashes(virginia))
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


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


def county_join_key(series: pd.Series) -> pd.Series:
    """Normalize county/city labels for cross-source joins."""
    cleaned = (
        series.fillna("")
        .astype(str)
        .str.replace(r"^\d+\.\s*", "", regex=True)
        .str.replace(r"^City of (.+)$", r"\1 City", regex=True)
        .str.replace(r"\s+County$", "", regex=True)
        .str.replace(r"\s+Parish$", "", regex=True)
        .str.replace(r"\s+Borough$", "", regex=True)
        .str.upper()
        .str.strip()
    )
    return cleaned


def build_all_state_county_analytics(
    all_state_crashes: pd.DataFrame,
    businesses: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    """Create county-year analytics for every automated all-severity state source."""
    if all_state_crashes.empty:
        return pd.DataFrame()

    pop = population.copy()
    pop["state_fips"] = pop["state_fips"].astype(str).str.zfill(2)
    pop["county_join_key"] = county_join_key(pop["county_name"])
    business_summary = businesses.groupby("county_geoid", as_index=False).agg(
        target_establishments=("establishments", "sum"),
        target_industry_employees=("employees", "sum"),
        target_annual_payroll_thousands=("annual_payroll_thousands", "sum"),
    )

    crashes = all_state_crashes.copy()
    crashes["state_fips"] = crashes["state_code"].astype(str).str.zfill(2)
    crashes["county_join_key"] = county_join_key(crashes["county"])
    crashes["property_damage_only_crash"] = crashes["crash_severity_desc"].eq("No Injury/PDO").astype(int)
    crashes["fatal_crash"] = crashes["crash_severity_desc"].eq("Fatal").astype(int)
    crashes["suspected_serious_injury_crash"] = crashes["crash_severity_desc"].eq(
        "Suspected Serious Injury"
    ).astype(int)

    summary = (
        crashes.groupby(["state", "state_fips", "year", "county_join_key"], as_index=False)
        .agg(
            source_county_name=("county", "first"),
            all_crashes=("case_id", "count"),
            property_damage_only_crashes=("property_damage_only_crash", "sum"),
            injury_crashes=("injury_crash", "sum"),
            suspected_serious_injury_crashes=("suspected_serious_injury_crash", "sum"),
            fatal_crashes=("fatal_crash", "sum"),
            fatalities=("fatalities", "sum"),
            motor_carrier_crashes=("commercial_vehicle_involved", "sum"),
            commercial_vehicle_crashes=("large_truck_bus_involved", "sum"),
            dui_crashes=("dui", "sum"),
            distracted_driving_crashes=("distracted_driving", "sum"),
            speed_related_crashes=("speed_related", "sum"),
        )
    )

    analytics = summary.merge(
        pop,
        on=["state_fips", "county_join_key"],
        how="left",
        validate="many_to_one",
        suffixes=("", "_population"),
    ).merge(business_summary, on="county_geoid", how="left", validate="many_to_one")
    analytics["population"] = analytics.apply(
        lambda row: row.get(f"population_{int(row['year'])}", pd.NA),
        axis=1,
    )
    analytics["county_name"] = analytics["county_name"].fillna(analytics["source_county_name"])
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
    return analytics.drop(columns=["county_join_key", "source_county_name"])


def export_analysis_files(
    crashes: pd.DataFrame,
    businesses: pd.DataFrame,
    population: pd.DataFrame,
    county_analytics: pd.DataFrame,
    utah_crashes: pd.DataFrame,
    utah_county_analytics: pd.DataFrame,
    all_state_crashes: pd.DataFrame,
    all_state_county_analytics: pd.DataFrame,
    all_crash_source_status: pd.DataFrame,
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
    all_state_crashes.to_csv(
        EXPORT_DIRECTORY / "all_state_crashes_2019_2024.csv.gz",
        index=False,
        compression="gzip",
    )
    all_state_county_analytics.to_csv(
        EXPORT_DIRECTORY / "all_state_county_crash_analytics_2019_2024.csv",
        index=False,
    )
    all_crash_source_status.to_csv(
        EXPORT_DIRECTORY / "all_crash_source_status.csv",
        index=False,
    )


def write_database(
    fars_years: list[int],
    cbp_year: int,
    all_crash_years: list[int],
    include_virginia: bool = True,
) -> None:
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
    print("Loading automated all-state all-crash records")
    all_state_crashes = load_all_state_crashes(
        utah_crashes,
        all_crash_years,
        include_virginia=include_virginia,
    )
    all_state_county_analytics = build_all_state_county_analytics(
        all_state_crashes, businesses, population
    )
    all_crash_source_status = pd.DataFrame(ALL_CRASH_SOURCE_STATUS)

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
            {
                "dataset": "Virginia Roads Full_Crash",
                "description": "Official Virginia all-severity crash records sourced from DMV TREDS",
                "years": f"{min(all_crash_years)}-{max(all_crash_years)}",
                "records": len(all_state_crashes[all_state_crashes["state"] == "Virginia"]),
                "refreshed_at": refreshed_at,
                "source_url": VIRGINIA_CRASH_SERVICE,
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
        all_state_crashes.to_sql(
            "all_state_crashes", connection, if_exists="replace", index=False
        )
        all_state_county_analytics.to_sql(
            "all_state_county_crash_analytics", connection, if_exists="replace", index=False
        )
        all_crash_source_status.to_sql(
            "all_crash_source_status", connection, if_exists="replace", index=False
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
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_all_state_crashes_state_year "
            "ON all_state_crashes(state, year)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_all_state_county_state_year "
            "ON all_state_county_crash_analytics(state, year)"
        )

    export_analysis_files(
        crashes,
        businesses,
        population,
        county_analytics,
        utah_crashes,
        utah_county_analytics,
        all_state_crashes,
        all_state_county_analytics,
        all_crash_source_status,
    )
    print(f"Created {DATABASE_PATH}")
    print(f"FARS crashes: {len(crashes):,}")
    print(f"Business-market records: {len(businesses):,}")
    print(f"County analytical records: {len(county_analytics):,}")
    print(f"Utah all-crash records: {len(utah_crashes):,}")
    print(f"Utah county-year analytical records: {len(utah_county_analytics):,}")
    print(f"All-state all-crash records: {len(all_state_crashes):,}")
    print(
        "Automated all-crash states: "
        + ", ".join(sorted(all_state_crashes["state"].dropna().unique()))
    )


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
    parser.add_argument(
        "--all-crash-years",
        nargs="+",
        type=int,
        default=ALL_CRASH_YEARS,
        help="All-severity state crash years to load. Defaults to 2019 through 2024.",
    )
    parser.add_argument(
        "--skip-virginia",
        action="store_true",
        help="Skip the automated Virginia Roads all-crash adapter.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    write_database(
        arguments.fars_years,
        arguments.cbp_year,
        arguments.all_crash_years,
        include_virginia=not arguments.skip_virginia,
    )
