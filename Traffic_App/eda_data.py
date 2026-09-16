"""Convenience loaders for Python exploratory analysis.

These functions mirror the datasets produced by ``ingest.py`` and used by the
Streamlit app, but they intentionally avoid importing Streamlit. By default the
helpers read the full local SQLite database when it exists, then fall back to the
compact deployment CSVs or analysis exports.

Examples
--------
>>> from eda_data import get_data_utah_crashes, get_data_catalog
>>> get_data_catalog()
>>> utah = get_data_utah_crashes(columns=["year", "county_name", "crash_severity_desc"])
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_DIRECTORY = ROOT / "data"
DATABASE_PATH = DATA_DIRECTORY / "traffic_data.sqlite"
DEPLOY_DIRECTORY = DATA_DIRECTORY / "deploy"
EXPORT_DIRECTORY = DATA_DIRECTORY / "exports"

FIPS_DTYPES = {
    "state_fips": "string",
    "county_fips": "string",
    "county_geoid": "string",
    "state_code": "string",
    "county_code": "string",
}

EXPORT_FILES = {
    "all_crash_source_status": "all_crash_source_status.csv",
    "all_state_county_crash_analytics": "all_state_county_crash_analytics_2019_2024.csv",
    "all_state_crashes": "all_state_crashes_2019_2024.csv.gz",
    "county_business_patterns": "county_target_industries_2023.csv",
    "county_marketing_analytics": "county_marketing_analytics.csv",
    "county_population": "county_population_2020_2024.csv",
    "fars_crashes": "fars_crashes_2019_2023.csv",
    "utah_county_crash_analytics": "utah_county_crash_analytics_2019_2024.csv",
    "utah_crashes": "utah_crashes_2019_2024.csv.gz",
}

TABLES = (
    "fars_crashes",
    "county_business_patterns",
    "county_population",
    "county_marketing_analytics",
    "data_sources",
    "utah_crashes",
    "utah_county_crash_analytics",
    "all_state_crashes",
    "all_state_county_crash_analytics",
    "all_crash_source_status",
)


def _clean_columns(columns: Iterable[str] | None) -> list[str] | None:
    if columns is None:
        return None
    cleaned = [column for column in columns if column]
    return cleaned or None


def _read_csv(path: Path, columns: list[str] | None, nrows: int | None) -> pd.DataFrame:
    return pd.read_csv(
        path,
        usecols=columns,
        nrows=nrows,
        low_memory=False,
        dtype=FIPS_DTYPES,
    )


def _read_sql(
    table: str,
    columns: list[str] | None,
    where: str | None,
    params: tuple | dict | None,
    nrows: int | None,
) -> pd.DataFrame:
    selected = "*" if columns is None else ", ".join(f'"{column}"' for column in columns)
    query = f'SELECT {selected} FROM "{table}"'
    if where:
        query += f" WHERE {where}"
    if nrows is not None:
        query += f" LIMIT {int(nrows)}"

    with sqlite3.connect(DATABASE_PATH) as connection:
        table_exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        if not table_exists:
            raise KeyError(f"Table not found in SQLite database: {table}")
        return pd.read_sql_query(query, connection, params=params)


def get_data_table(
    table: str,
    columns: Iterable[str] | None = None,
    where: str | None = None,
    params: tuple | dict | None = None,
    nrows: int | None = None,
    prefer_sqlite: bool = True,
) -> pd.DataFrame:
    """Load any known dataset as a pandas DataFrame.

    Parameters
    ----------
    table:
        One of the names in ``TABLES``.
    columns:
        Optional subset of columns to read.
    where, params:
        Optional SQLite WHERE clause and parameters. These are only applied when
        reading from SQLite.
    nrows:
        Optional row limit, useful for peeking at large crash-level tables.
    prefer_sqlite:
        Read ``data/traffic_data.sqlite`` first when available. Set to ``False``
        to inspect the smaller deployment/export CSV files.
    """
    if table not in TABLES:
        raise ValueError(f"Unknown table {table!r}. Choose from: {', '.join(TABLES)}")

    selected_columns = _clean_columns(columns)
    if prefer_sqlite and DATABASE_PATH.exists():
        return _read_sql(table, selected_columns, where, params, nrows)

    deploy_file = DEPLOY_DIRECTORY / f"{table}.csv.gz"
    if deploy_file.exists():
        return _read_csv(deploy_file, selected_columns, nrows)

    export_name = EXPORT_FILES.get(table)
    export_file = EXPORT_DIRECTORY / export_name if export_name else None
    if export_file and export_file.exists():
        return _read_csv(export_file, selected_columns, nrows)

    if DATABASE_PATH.exists():
        return _read_sql(table, selected_columns, where, params, nrows)

    raise FileNotFoundError(f"No SQLite, deployment CSV, or export CSV found for {table}")


def get_data_fars_crashes(**kwargs) -> pd.DataFrame:
    return get_data_table("fars_crashes", **kwargs)


def get_data_county_business_patterns(**kwargs) -> pd.DataFrame:
    return get_data_table("county_business_patterns", **kwargs)


def get_data_county_population(**kwargs) -> pd.DataFrame:
    return get_data_table("county_population", **kwargs)


def get_data_county_marketing_analytics(**kwargs) -> pd.DataFrame:
    return get_data_table("county_marketing_analytics", **kwargs)


def get_data_data_sources(**kwargs) -> pd.DataFrame:
    return get_data_table("data_sources", **kwargs)


def get_data_utah_crashes(**kwargs) -> pd.DataFrame:
    return get_data_table("utah_crashes", **kwargs)


def get_data_utah_county_crash_analytics(**kwargs) -> pd.DataFrame:
    return get_data_table("utah_county_crash_analytics", **kwargs)


def get_data_all_state_crashes(**kwargs) -> pd.DataFrame:
    return get_data_table("all_state_crashes", **kwargs)


def get_data_all_state_county_crash_analytics(**kwargs) -> pd.DataFrame:
    return get_data_table("all_state_county_crash_analytics", **kwargs)


def get_data_all_crash_source_status(**kwargs) -> pd.DataFrame:
    return get_data_table("all_crash_source_status", **kwargs)


def get_data_catalog() -> pd.DataFrame:
    """Return row and column counts for the available datasets."""
    rows = []
    for table in TABLES:
        frame = get_data_table(table, nrows=0)
        count = None
        if DATABASE_PATH.exists():
            with sqlite3.connect(DATABASE_PATH) as connection:
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                ).fetchone()
                if exists:
                    count = connection.execute(
                        f'SELECT COUNT(*) FROM "{table}"'
                    ).fetchone()[0]
        if count is None:
            count = len(get_data_table(table))
        rows.append(
            {
                "table": table,
                "rows": count,
                "columns": len(frame.columns),
                "example_columns": ", ".join(frame.columns[:8]),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.max_colwidth", 80)
    print(get_data_catalog().to_string(index=False))
