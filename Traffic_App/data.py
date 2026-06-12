"""Data access utilities for the traffic accident analytics app."""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
from typing import BinaryIO

import pandas as pd
import streamlit as st


DATA_DIRECTORY = Path(__file__).parent / "data"
DEFAULT_DATA_FILE = DATA_DIRECTORY / "accidents.csv"
DATABASE_PATH = DATA_DIRECTORY / "traffic_data.sqlite"
DEPLOY_DIRECTORY = DATA_DIRECTORY / "deploy"


def load_table(table: str) -> pd.DataFrame:
    """Load a table from local SQLite or its compact deployment fallback."""
    force_deploy = os.getenv("ELYSIUM_FORCE_DEPLOY_DATA") == "1"
    if DATABASE_PATH.exists() and not force_deploy:
        with sqlite3.connect(DATABASE_PATH) as connection:
            table_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if table_exists:
                return pd.read_sql_query(f'SELECT * FROM "{table}"', connection)

    deployment_file = DEPLOY_DIRECTORY / f"{table}.csv.gz"
    if deployment_file.exists():
        dtype = {"state_fips": str, "county_geoid": str}
        return pd.read_csv(deployment_file, low_memory=False, dtype=dtype)
    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_accident_data(uploaded_file: BinaryIO | None = None) -> pd.DataFrame:
    """Load uploaded accident data or the default local dataset when available."""
    if uploaded_file is not None:
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        if file_name.endswith(".xlsx"):
            return pd.read_excel(uploaded_file)
        raise ValueError("Unsupported file format. Upload a CSV or XLSX file.")

    if DEFAULT_DATA_FILE.exists():
        return pd.read_csv(DEFAULT_DATA_FILE)

    return pd.DataFrame()


@st.cache_data(show_spinner=False)
def load_fars_crashes() -> pd.DataFrame:
    """Load normalized nationwide fatal-crash records."""
    return load_table("fars_crashes")


@st.cache_data(show_spinner=False)
def load_business_patterns() -> pd.DataFrame:
    """Load target-industry county business counts."""
    return load_table("county_business_patterns")


@st.cache_data(show_spinner=False)
def load_data_sources() -> pd.DataFrame:
    """Load data provenance and refresh metadata."""
    return load_table("data_sources")


@st.cache_data(show_spinner=False)
def load_county_analytics() -> pd.DataFrame:
    """Load the joined county-year crash, population, and market table."""
    return load_table("county_marketing_analytics")


@st.cache_data(show_spinner=False)
def load_utah_crashes() -> pd.DataFrame:
    """Load UDOT's anonymized all-severity Utah crash records."""
    return load_table("utah_crashes")


@st.cache_data(show_spinner=False)
def load_utah_county_analytics() -> pd.DataFrame:
    """Load complete Utah county-year all-severity crash analytics."""
    return load_table("utah_county_crash_analytics")
