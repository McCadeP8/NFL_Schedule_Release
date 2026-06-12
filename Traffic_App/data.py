"""Data access utilities for the traffic accident analytics app."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import BinaryIO

import pandas as pd
import streamlit as st


DATA_DIRECTORY = Path(__file__).parent / "data"
DEFAULT_DATA_FILE = DATA_DIRECTORY / "accidents.csv"
DATABASE_PATH = DATA_DIRECTORY / "traffic_data.sqlite"


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
    if not DATABASE_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DATABASE_PATH) as connection:
        return pd.read_sql_query("SELECT * FROM fars_crashes", connection)


@st.cache_data(show_spinner=False)
def load_business_patterns() -> pd.DataFrame:
    """Load target-industry county business counts."""
    if not DATABASE_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DATABASE_PATH) as connection:
        return pd.read_sql_query("SELECT * FROM county_business_patterns", connection)


@st.cache_data(show_spinner=False)
def load_data_sources() -> pd.DataFrame:
    """Load data provenance and refresh metadata."""
    if not DATABASE_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DATABASE_PATH) as connection:
        return pd.read_sql_query("SELECT * FROM data_sources", connection)


@st.cache_data(show_spinner=False)
def load_county_analytics() -> pd.DataFrame:
    """Load the joined county-year crash, population, and market table."""
    if not DATABASE_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DATABASE_PATH) as connection:
        return pd.read_sql_query("SELECT * FROM county_marketing_analytics", connection)


@st.cache_data(show_spinner=False)
def load_utah_crashes() -> pd.DataFrame:
    """Load UDOT's anonymized all-severity Utah crash records."""
    if not DATABASE_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DATABASE_PATH) as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='utah_crashes'"
        ).fetchone()
        if not table_exists:
            return pd.DataFrame()
        return pd.read_sql_query("SELECT * FROM utah_crashes", connection)


@st.cache_data(show_spinner=False)
def load_utah_county_analytics() -> pd.DataFrame:
    """Load complete Utah county-year all-severity crash analytics."""
    if not DATABASE_PATH.exists():
        return pd.DataFrame()
    with sqlite3.connect(DATABASE_PATH) as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='utah_county_crash_analytics'"
        ).fetchone()
        if not table_exists:
            return pd.DataFrame()
        return pd.read_sql_query("SELECT * FROM utah_county_crash_analytics", connection)
