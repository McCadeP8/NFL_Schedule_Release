"""Elysium Wealth Management traffic accident analytics application."""

from __future__ import annotations

import html
import math

import pandas as pd
import pydeck as pdk
import streamlit as st

from data import (
    load_business_patterns,
    load_county_analytics,
    load_data_sources,
    load_fars_crashes,
    load_utah_crashes,
    load_utah_county_analytics,
)


NAVY = "#213f57"
AQUA = "#31D5D0"
INK = "#172c3d"
MUTED = "#718697"

st.set_page_config(
    page_title="Traffic Accident Insights | Elysium Wealth Management",
    page_icon=":material/car_crash:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def esc(value: object) -> str:
    """Escape user-facing values for safe HTML rendering."""
    return html.escape(str(value))


def number(value: object, decimals: int = 0) -> str:
    """Format a numeric value for display."""
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{decimals}f}"


def inject_css() -> None:
    """Apply the editorial visual system used throughout the app."""
    st.html(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600;700&family=Rajdhani:wght@600;700&display=swap');

:root { --aqua:#31D5D0; --navy:#213f57; --ink:#172c3d; --muted:#718697; --line:#dce6eb; --mist:#f4f8f9; }
html, body, [class*="css"] { font-family:'Barlow',sans-serif; color:var(--ink); }
.stApp {
  background: radial-gradient(circle at 93% 3%,rgba(49,213,208,.13),transparent 25rem),#f4f8f9;
}
.block-container { max-width:1580px!important; padding:1.2rem 2.2rem 4rem!important; }
footer { visibility:hidden; }
header[data-testid="stHeader"] { background:transparent; }
[data-testid="stToolbar"] {
  background:rgba(255,255,255,.92)!important;
  border:1px solid var(--line)!important;
  border-radius:7px!important;
  box-shadow:0 2px 10px rgba(23,44,61,.08)!important;
  padding:2px 5px!important;
}
[data-testid="stToolbar"] button,
[data-testid="stToolbar"] button *,
[data-testid="stToolbar"] a,
[data-testid="stToolbar"] svg,
[data-testid="stAppDeployButton"],
[data-testid="stAppDeployButton"] *,
[data-testid="stMainMenu"],
[data-testid="stMainMenu"] * {
  color:var(--navy)!important;
  fill:var(--navy)!important;
  opacity:1!important;
  visibility:visible!important;
}
[data-testid="stToolbar"] button:hover,
[data-testid="stAppDeployButton"] button:hover,
[data-testid="stMainMenu"] button:hover {
  background:#e8f7f7!important;
}

[data-testid="stSidebar"] { background:linear-gradient(180deg,#19364c 0%,#234b64 100%); border-right:1px solid rgba(49,213,208,.28); }
[data-testid="stSidebar"] * { color:#fff; }
[data-testid="stSidebarContent"] { padding:0 1rem; }
[data-testid="stSidebar"] .stRadio label { padding:.5rem .45rem; }
[data-testid="stSidebar"] div[data-testid="stWidgetLabel"] p {
  font-family:'Barlow Condensed',sans-serif; font-size:13px; font-weight:800; letter-spacing:2px; text-transform:uppercase;
}
[data-testid="stToolbar"],[data-testid="stToolbar"]>div,[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,[data-testid="stExpandSidebarButton"] { opacity:1!important; visibility:visible!important; }
[data-testid="stSidebarCollapseButton"] button,[data-testid="stExpandSidebarButton"] {
  background:var(--aqua)!important; border:2px solid #fff!important; border-radius:999px!important;
  box-shadow:0 5px 16px rgba(23,44,61,.25)!important; color:var(--navy)!important;
  height:2.4rem!important; width:2.4rem!important;
}
[data-testid="stSidebarCollapseButton"] { right:.8rem; top:.8rem; }
[data-testid="stExpandSidebarButton"] { left:1rem!important; top:.9rem!important; }

.masthead { display:flex; justify-content:space-between; align-items:flex-end; gap:24px; padding:30px 0 22px; border-bottom:2px solid var(--line); margin-bottom:20px; }
.mast-kicker { font-family:'Barlow Condensed',sans-serif; color:#168f8c; font-weight:800; font-size:13px; letter-spacing:4px; text-transform:uppercase; }
.mast-title { font-family:'Bebas Neue',sans-serif; color:var(--navy); font-size:clamp(58px,7vw,92px); letter-spacing:3px; line-height:.9; margin-top:8px; }
.mast-copy { color:#617888; font-size:15px; font-weight:500; line-height:1.6; max-width:560px; padding-bottom:4px; }
.period-chip { display:inline-flex; background:#fff; border:1px solid var(--line); border-radius:5px; color:var(--navy); font-family:'Rajdhani',sans-serif; font-size:14px; font-weight:800; letter-spacing:1px; padding:6px 10px; margin-top:10px; }

.metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:13px; margin:16px 0 12px; }
.metric-card { position:relative; overflow:hidden; background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 2px 10px rgba(23,44,61,.06); padding:17px 18px 16px; }
.metric-card:before { position:absolute; content:""; left:0; top:0; width:5px; height:100%; background:var(--accent,var(--aqua)); }
.metric-label { font-family:'Barlow Condensed',sans-serif; color:#8496a3; font-size:12px; font-weight:800; letter-spacing:2px; text-transform:uppercase; }
.metric-value { font-family:'Rajdhani',sans-serif; color:var(--navy); font-size:34px; font-weight:800; line-height:1; margin:7px 0 4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.metric-note { color:#8496a3; font-size:12px; font-weight:600; }

.section-title { display:flex; align-items:center; gap:14px; margin:30px 0 12px; }
.section-title span { font-family:'Bebas Neue',sans-serif; color:var(--navy); font-size:34px; letter-spacing:2px; line-height:1; white-space:nowrap; }
.section-title div { height:1px; background:var(--line); flex:1; }
.section-sub { color:#7a8e9c; font-size:13px; font-weight:600; margin:-5px 0 13px; }

.panel { background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 2px 10px rgba(23,44,61,.06); padding:20px; height:100%; }
.panel-kicker { color:#168f8c; font-family:'Barlow Condensed',sans-serif; font-size:12px; font-weight:800; letter-spacing:2.5px; text-transform:uppercase; }
.panel-title { color:var(--navy); font-family:'Bebas Neue',sans-serif; font-size:31px; letter-spacing:1.5px; line-height:1; margin:5px 0 18px; }

.trend-chart { display:grid; grid-template-columns:repeat(var(--count),1fr); align-items:end; gap:15px; height:270px; padding:16px 8px 0; border-bottom:2px solid #d7e2e7; background:repeating-linear-gradient(to top,transparent 0,transparent 66px,#edf2f4 67px); }
.trend-year { height:100%; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; gap:7px; }
.trend-bars { height:210px; display:flex; align-items:flex-end; justify-content:center; gap:5px; width:100%; }
.trend-bar { position:relative; width:min(34%,34px); min-height:4px; border-radius:4px 4px 0 0; }
.trend-bar.crashes { background:var(--navy); }
.trend-bar.fatalities { background:var(--aqua); }
.trend-value { position:absolute; top:-20px; left:50%; transform:translateX(-50%); font-family:'Rajdhani',sans-serif; font-size:12px; font-weight:800; color:var(--ink); }
.trend-label { font-family:'Rajdhani',sans-serif; font-size:14px; font-weight:800; color:#6d8290; }
.chart-legend { display:flex; gap:18px; margin-top:16px; color:#718697; font-size:12px; font-weight:700; }
.legend-dot { display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:6px; }

.workforce-row { margin:0 0 17px; }
.workforce-top { display:flex; justify-content:space-between; align-items:flex-end; gap:10px; margin-bottom:6px; }
.workforce-name { color:var(--ink); font-size:13px; font-weight:700; }
.workforce-value { color:var(--navy); font-family:'Rajdhani',sans-serif; font-size:18px; font-weight:800; white-space:nowrap; }
.workforce-track { height:8px; border-radius:999px; background:#eaf0f2; overflow:hidden; }
.workforce-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,var(--navy),var(--aqua)); }
.workforce-meta { color:#91a0aa; font-size:11px; font-weight:600; margin-top:4px; }

.table-wrap { overflow:auto; background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 2px 10px rgba(23,44,61,.06); }
.data-table { border-collapse:collapse; width:100%; min-width:850px; }
.data-table th { background:#f6f9fa; border-bottom:2px solid var(--line); color:#708491; font-family:'Barlow Condensed',sans-serif; font-size:12px; font-weight:800; letter-spacing:1.4px; padding:10px 13px; text-align:right; text-transform:uppercase; white-space:nowrap; }
.data-table th:first-child,.data-table th:nth-child(2) { text-align:left; }
.data-table td { border-bottom:1px solid #eaf0f2; color:#465e6d; font-family:'Rajdhani',sans-serif; font-size:14px; font-weight:700; padding:10px 13px; text-align:right; white-space:nowrap; }
.data-table td:first-child,.data-table td:nth-child(2) { text-align:left; }
.data-table tr:nth-child(even) td { background:#fbfcfd; }
.data-table tr:hover td { background:#f1f8f8; }
.rank { color:#9aabb4; font-size:12px; }
.county-name { color:var(--navy); font-family:'Barlow',sans-serif; font-weight:700; }
.rate-pill { display:inline-flex; min-width:54px; justify-content:center; border-radius:4px; background:#e8f9f8; color:#117f7c; font-size:12px; font-weight:800; padding:3px 7px; }
.commercial-pill { display:inline-flex; min-width:34px; justify-content:center; border-radius:4px; background:#eaf0f4; color:var(--navy); padding:3px 7px; }

.matrix-wrap { overflow-x:auto; background:#fff; border:1px solid var(--line); border-radius:8px; box-shadow:0 2px 10px rgba(23,44,61,.06); padding:14px; }
.condition-matrix { border-collapse:separate; border-spacing:5px; width:100%; min-width:1040px; }
.condition-matrix th { color:#718697; font-family:'Barlow Condensed',sans-serif; font-size:11px; font-weight:800; letter-spacing:1px; line-height:1.1; padding:5px 6px; text-align:center; text-transform:uppercase; }
.condition-matrix th:first-child { text-align:left; min-width:135px; }
.condition-matrix td { border-radius:5px; height:67px; min-width:95px; padding:7px; text-align:center; vertical-align:middle; }
.condition-matrix td.weather-label { background:#f5f8f9; color:var(--navy); font-family:'Barlow',sans-serif; font-size:12px; font-weight:700; text-align:left; }
.condition-matrix td.matrix-cell { background:rgba(49,213,208,var(--heat)); border:1px solid rgba(33,63,87,.07); color:var(--ink); }
.condition-matrix td.matrix-cell.hot { background:rgba(33,63,87,var(--heat)); color:#fff; }
.matrix-count { font-family:'Rajdhani',sans-serif; font-size:17px; font-weight:800; line-height:1; }
.matrix-share { font-family:'Barlow Condensed',sans-serif; font-size:10px; font-weight:700; letter-spacing:.5px; margin-top:4px; opacity:.72; text-transform:uppercase; }
.matrix-total { background:#edf3f5; color:var(--navy); font-family:'Rajdhani',sans-serif; font-size:16px; font-weight:800; }
.condition-rank-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; margin-top:14px; }
.condition-rank { background:#fff; border:1px solid var(--line); border-top:4px solid var(--aqua); border-radius:6px; padding:13px; box-shadow:0 1px 6px rgba(23,44,61,.05); }
.condition-rank-num { color:#9aabb4; font-family:'Rajdhani',sans-serif; font-size:12px; font-weight:800; }
.condition-rank-title { color:var(--navy); font-size:12px; font-weight:700; line-height:1.3; margin:5px 0 8px; }
.condition-rank-value { color:var(--ink); font-family:'Rajdhani',sans-serif; font-size:22px; font-weight:800; line-height:1; }
.condition-rank-share { color:#8b9ba6; font-size:10px; font-weight:700; margin-top:3px; text-transform:uppercase; }

.insight-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:12px 0 4px; }
.insight-card { background:linear-gradient(135deg,#213f57,#2a566f); border-radius:8px; color:#fff; padding:18px 19px; box-shadow:0 8px 20px rgba(23,44,61,.14); }
.insight-card.aqua { background:linear-gradient(135deg,#188f8c,#31bdb8); }
.insight-card.light { background:#fff; border:1px solid var(--line); color:var(--navy); box-shadow:0 2px 10px rgba(23,44,61,.06); }
.insight-value { font-family:'Rajdhani',sans-serif; font-size:30px; font-weight:800; line-height:1; }
.insight-label { font-family:'Barlow Condensed',sans-serif; font-size:12px; font-weight:800; letter-spacing:1.7px; margin-top:7px; opacity:.78; text-transform:uppercase; }
.note-box { background:#edf8f8; border-left:5px solid var(--aqua); border-radius:5px; color:#587180; font-size:12px; font-weight:600; line-height:1.6; margin:14px 0 5px; padding:11px 14px; }

@media(max-width:900px) {
  .metric-grid,.insight-strip { grid-template-columns:1fr 1fr; }
  .masthead { display:block; }
  .mast-copy { margin-top:14px; }
}
</style>
"""
    )


def section_title(title: str, subtitle: str = "") -> None:
    st.html(
        f'<div class="section-title"><span>{esc(title)}</span><div></div></div>'
        + (f'<div class="section-sub">{esc(subtitle)}</div>' if subtitle else "")
    )


def metric_grid(items: list[tuple[str, str, str, str]]) -> None:
    cards = "".join(
        f"""
        <div class="metric-card" style="--accent:{accent}">
          <div class="metric-label">{esc(label)}</div>
          <div class="metric-value">{esc(value)}</div>
          <div class="metric-note">{esc(note)}</div>
        </div>"""
        for label, value, note, accent in items
    )
    st.html(f'<div class="metric-grid">{cards}</div>')


def trend_panel(trend: pd.DataFrame, title: str = "Fatal Crash Trend", series_label: str = "Fatal crashes") -> None:
    max_value = max(float(trend["fatal_crashes"].max()), float(trend["fatalities"].max()), 1)
    years = []
    for row in trend.itertuples():
        crash_height = max(float(row.fatal_crashes) / max_value * 190, 4)
        fatal_height = max(float(row.fatalities) / max_value * 190, 4)
        years.append(
            f"""
            <div class="trend-year">
              <div class="trend-bars">
                <div class="trend-bar crashes" style="height:{crash_height:.1f}px"><span class="trend-value">{int(row.fatal_crashes):,}</span></div>
                <div class="trend-bar fatalities" style="height:{fatal_height:.1f}px"><span class="trend-value">{int(row.fatalities):,}</span></div>
              </div>
              <div class="trend-label">{int(row.year)}</div>
            </div>"""
        )
    st.html(
        f"""
        <div class="panel">
          <div class="panel-kicker">Annual movement</div>
          <div class="panel-title">{esc(title)}</div>
          <div class="trend-chart" style="--count:{len(years)}">{''.join(years)}</div>
          <div class="chart-legend">
            <span><i class="legend-dot" style="background:{NAVY}"></i>{esc(series_label)}</span>
            <span><i class="legend-dot" style="background:{AQUA}"></i>Fatalities</span>
          </div>
        </div>"""
    )


def workforce_panel(industry_summary: pd.DataFrame) -> None:
    max_employees = max(float(industry_summary["employees"].max()), 1)
    rows = []
    for row in industry_summary.itertuples():
        width = float(row.employees) / max_employees * 100
        rows.append(
            f"""
            <div class="workforce-row">
              <div class="workforce-top"><span class="workforce-name">{esc(row.industry)}</span><span class="workforce-value">{int(row.employees):,}</span></div>
              <div class="workforce-track"><div class="workforce-fill" style="width:{width:.1f}%"></div></div>
              <div class="workforce-meta">{int(row.establishments):,} establishments</div>
            </div>"""
        )
    st.html(
        f"""
        <div class="panel">
          <div class="panel-kicker">Addressable market</div>
          <div class="panel-title">Target-Industry Workforce</div>
          {''.join(rows)}
        </div>"""
    )


def county_table(frame: pd.DataFrame, limit: int = 15, crash_header: str = "Fatal Crashes") -> None:
    rows = []
    for rank, row in enumerate(frame.head(limit).itertuples(), start=1):
        rows.append(
            f"""
            <tr>
              <td class="rank">{rank:02d}</td>
              <td class="county-name">{esc(row.county_name)}</td>
              <td>{number(row.fatal_crashes)}</td>
              <td>{number(row.fatalities)}</td>
              <td><span class="rate-pill">{number(row.fatal_crashes_per_100k, 1)}</span></td>
              <td><span class="commercial-pill">{number(row.commercial_involved_crashes)}</span></td>
              <td>{number(row.target_establishments)}</td>
              <td>{number(row.target_industry_employees)}</td>
            </tr>"""
        )
    st.html(
        f"""
        <div class="table-wrap"><table class="data-table">
          <thead><tr><th>#</th><th>County</th><th>{esc(crash_header)}</th><th>Fatalities</th><th>Per 100K</th><th>Commercial</th><th>Target Businesses</th><th>Target Employees</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table></div>"""
    )


def simple_table(headers: list[str], rows: list[list[object]]) -> None:
    head = "".join(f"<th>{esc(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    st.html(f'<div class="table-wrap"><table class="data-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def condition_matrix(frame: pd.DataFrame, total_crashes: int) -> None:
    """Render a custom weather-by-light crash matrix with marginal totals."""
    weather_order = (
        frame.groupby("weather")["size"].sum().sort_values(ascending=False).index.tolist()
    )
    light_order = (
        frame.groupby("light_condition")["size"].sum().sort_values(ascending=False).index.tolist()
    )
    pivot = frame.pivot_table(
        index="weather",
        columns="light_condition",
        values="size",
        fill_value=0,
        aggfunc="sum",
    ).reindex(index=weather_order, columns=light_order, fill_value=0)
    max_value = max(float(pivot.to_numpy().max()), 1)
    headers = "".join(f"<th>{esc(light)}</th>" for light in light_order)
    rows = []
    for weather in weather_order:
        cells = []
        for light in light_order:
            value = int(pivot.loc[weather, light])
            intensity = math.log1p(value) / math.log1p(max_value)
            opacity = 0.08 + intensity * 0.78
            hot = intensity > 0.68
            share = value / total_crashes * 100 if total_crashes else 0
            cells.append(
                f'<td class="matrix-cell{" hot" if hot else ""}" style="--heat:{opacity:.3f}" '
                f'title="{esc(weather)} · {esc(light)}: {value:,} crashes ({share:.2f}%)">'
                f'<div class="matrix-count">{value:,}</div><div class="matrix-share">{share:.1f}%</div></td>'
            )
        weather_total = int(pivot.loc[weather].sum())
        rows.append(
            f'<tr><td class="weather-label">{esc(weather)}</td>{"".join(cells)}'
            f'<td class="matrix-total">{weather_total:,}</td></tr>'
        )
    light_totals = "".join(
        f'<td class="matrix-total">{int(pivot[light].sum()):,}</td>' for light in light_order
    )
    st.html(
        f"""
        <div class="matrix-wrap"><table class="condition-matrix">
          <thead><tr><th>Weather ↓ / Light →</th>{headers}<th>Total</th></tr></thead>
          <tbody>{''.join(rows)}<tr><td class="weather-label">Total</td>{light_totals}<td class="matrix-total">{total_crashes:,}</td></tr></tbody>
        </table></div>"""
    )

    top = frame.sort_values("size", ascending=False).head(5)
    cards = "".join(
        f"""
        <div class="condition-rank">
          <div class="condition-rank-num">#{rank:02d}</div>
          <div class="condition-rank-title">{esc(row.weather)} · {esc(row.light_condition)}</div>
          <div class="condition-rank-value">{int(row.size):,}</div>
          <div class="condition-rank-share">{row.size / total_crashes * 100:.1f}% of crashes</div>
        </div>"""
        for rank, row in enumerate(top.itertuples(), start=1)
    )
    st.html(f'<div class="condition-rank-grid">{cards}</div>')


inject_css()
fars = load_fars_crashes()
businesses = load_business_patterns()
sources = load_data_sources()
county_analytics = load_county_analytics()
utah_crashes = load_utah_crashes()
utah_county_analytics = load_utah_county_analytics()

with st.sidebar:
    st.image("https://elysiumwealthmanagement.com/wp-content/uploads/2025/02/elysium-800x166.png", width="stretch")
    st.caption("TRAFFIC ACCIDENT INTELLIGENCE")
    st.divider()
    page = st.radio(
        "Navigation",
        ("Executive Overview", "Accident Trends", "Risk Factors", "Geographic Analysis"),
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("OFFICIAL DATA FILTERS")
    states = sorted(fars["state"].dropna().unique()) if not fars.empty else ["Utah"]
    selected_state = st.selectbox("State", states, index=states.index("Utah") if "Utah" in states else 0)
    utah_all_crash_available = (
        not utah_crashes.empty and "year" in utah_crashes.columns
    )
    crash_scope = "Fatal Crashes Only"
    if selected_state == "Utah" and utah_all_crash_available:
        crash_scope = st.radio(
            "Crash scope",
            ("All Reported Crashes", "Fatal Crashes Only"),
        )
    elif selected_state == "Utah":
        st.caption("All-crash UDOT data is not installed in this deployment.")
    use_utah_all_crashes = (
        selected_state == "Utah"
        and crash_scope == "All Reported Crashes"
        and utah_all_crash_available
    )
    year_source = utah_crashes if use_utah_all_crashes else fars
    available_years = (
        sorted(year_source["year"].dropna().astype(int).unique(), reverse=True)
        if "year" in year_source.columns
        else []
    )
    selected_years = st.multiselect("Crash years", available_years, default=available_years)
    st.divider()
    st.caption("NHTSA FARS · CENSUS CBP · CENSUS POPULATION ESTIMATES")

if fars.empty or not selected_years:
    st.info("Select at least one year or run `python ingest.py` to load official data.")
    st.stop()

if use_utah_all_crashes:
    raw_utah = utah_crashes[utah_crashes["year"].isin(selected_years)].copy()
    state_crashes = pd.DataFrame(
        {
            "case_id": raw_utah["crash_id"],
            "year": raw_utah["year"],
            "county": raw_utah["county_name"],
            "fatalities": pd.to_numeric(raw_utah["number_fatalities"], errors="coerce").fillna(0),
            "commercial_vehicle_involved": raw_utah["motor_carrier_involved_yn"].eq("Y").astype(int),
            "large_truck_bus_involved": raw_utah["commercial_motor_veh_involved"].eq("Y").astype(int),
            "work_zone": raw_utah["work_zone_related_ynu"],
            "weather": raw_utah["weather_condition_desc"],
            "light_condition": raw_utah["light_condition_desc"],
            "latitude": raw_utah["latitude"],
            "longitude": raw_utah["longitude"],
            "injury_crash": raw_utah["crash_severity_desc"].fillna("").ne("No Injury/PDO").astype(int),
            "suspected_serious_injuries": pd.to_numeric(raw_utah["number_four_injuries"], errors="coerce").fillna(0),
            "speed_related": raw_utah["speed_related"].eq("Y").astype(int),
            "distracted_driving": raw_utah["distracted_driving"].eq("Y").astype(int),
            "dui": raw_utah["dui"].eq("Y").astype(int),
            "crash_datetime": raw_utah["crash_datetime"],
            "crash_severity_desc": raw_utah["crash_severity_desc"],
            "main_road_name": raw_utah["main_road_name"],
            "route_id": raw_utah["route_id"],
            "location_desc": raw_utah["location_desc"],
            "manner_collision_desc": raw_utah["manner_collision_desc"],
            "number_vehicles_involved": raw_utah["number_vehicles_involved"],
        }
    )
else:
    state_crashes = fars[(fars["state"] == selected_state) & (fars["year"].isin(selected_years))].copy()
    state_crashes["injury_crash"] = 0
    state_crashes["suspected_serious_injuries"] = 0
    state_crashes["speed_related"] = 0
    state_crashes["distracted_driving"] = 0
    state_crashes["dui"] = 0

state_code = "49" if use_utah_all_crashes else str(int(state_crashes["state_code"].iloc[0])).zfill(2)
state_businesses = businesses[businesses["state_fips"] == state_code].copy()
latest_year = max(selected_years)
latest_rates_base = county_analytics[
    (county_analytics["state"] == selected_state) & (county_analytics["year"] == latest_year)
].copy()
if use_utah_all_crashes and not utah_county_analytics.empty:
    latest_rates = utah_county_analytics[utah_county_analytics["year"] == latest_year].copy()
    latest_rates["fatal_crashes"] = latest_rates["all_crashes"]
    latest_rates["fatal_crashes_per_100k"] = latest_rates["all_crashes_per_100k"]
    latest_rates["commercial_involved_crashes"] = latest_rates["motor_carrier_crashes"]
else:
    latest_rates = latest_rates_base
latest_rates["population"] = pd.to_numeric(latest_rates["population"], errors="coerce")
latest_rates = latest_rates.sort_values("fatal_crashes_per_100k", ascending=False)
stable_rates = latest_rates[latest_rates["population"] >= 10_000]
priority_counties = latest_rates.sort_values("fatal_crashes", ascending=False)

commercial_crashes = int(state_crashes["commercial_vehicle_involved"].sum())
target_establishments = int(state_businesses["establishments"].sum())
target_employees = int(state_businesses["employees"].sum())
highest_rate_county = stable_rates["county_name"].iloc[0] if not stable_rates.empty else "-"
period = f"{min(selected_years)}–{max(selected_years)}" if len(selected_years) > 1 else str(selected_years[0])
crash_label = "Reported Crashes" if use_utah_all_crashes else "Fatal Crashes"
crash_label_short = "crashes" if use_utah_all_crashes else "fatal crashes"

st.html(
    f"""
    <div class="masthead">
      <div><div class="mast-kicker">Elysium Wealth Management</div><div class="mast-title">Traffic Accident Insights</div></div>
      <div class="mast-copy">A decision-ready view of fatal crash exposure and the commercial markets Elysium can serve.<br><span class="period-chip">{esc(selected_state)} · {period}</span></div>
    </div>"""
)

metric_grid(
    [
        (crash_label, f"{len(state_crashes):,}", f"{selected_state} · {period}", AQUA),
        ("Commercial-Involved", f"{commercial_crashes:,}", "Recorded motor-carrier identifier", "#6fa4bd"),
        ("Target Businesses", f"{target_establishments:,}", "Four priority industries", "#168f8c"),
        ("Highest Crash Rate", highest_rate_county, f"{latest_year} · population 10K+", "#e6a94d"),
    ]
)

if page == "Executive Overview":
    trend = (
        state_crashes.groupby("year", as_index=False)
        .agg(fatal_crashes=("case_id", "count"), fatalities=("fatalities", "sum"))
        .sort_values("year")
    )
    industry_summary = (
        state_businesses.groupby("industry", as_index=False)
        .agg(establishments=("establishments", "sum"), employees=("employees", "sum"))
        .sort_values("employees", ascending=False)
    )
    section_title("Market Snapshot", f"{crash_label} and addressable workforce shown side by side.")
    left, right = st.columns((1.25, 1), gap="medium")
    with left:
        trend_panel(trend, f"{crash_label} Trend", crash_label)
    with right:
        workforce_panel(industry_summary)

    total_fatalities = int(state_crashes["fatalities"].sum())
    injury_crashes = int(state_crashes["injury_crash"].sum())
    commercial_share = commercial_crashes / len(state_crashes) * 100 if len(state_crashes) else 0
    top_burden = priority_counties.iloc[0] if not priority_counties.empty else None
    st.html(
        f"""
        <div class="insight-strip">
          <div class="insight-card"><div class="insight-value">{injury_crashes:,}</div><div class="insight-label">Injury crashes in selected period</div></div>
          <div class="insight-card aqua"><div class="insight-value">{commercial_share:.1f}%</div><div class="insight-label">Crashes with carrier indicator</div></div>
          <div class="insight-card light"><div class="insight-value">{esc(top_burden.county_name if top_burden is not None else "-")}</div><div class="insight-label">Highest {latest_year} crash count</div></div>
        </div>"""
    )
    section_title("Priority Counties", f"Latest-year market context for {latest_year}; ordered by {crash_label_short} count.")
    county_table(priority_counties, crash_header=crash_label)

elif page == "Accident Trends":
    trend = (
        state_crashes.groupby("year", as_index=False)
        .agg(
            fatal_crashes=("case_id", "count"),
            fatalities=("fatalities", "sum"),
            commercial_involved=("commercial_vehicle_involved", "sum"),
        )
        .sort_values("year")
    )
    section_title("Annual Movement", f"{crash_label} and fatalities across the selected period.")
    trend_panel(trend.rename(columns={"commercial_involved": "unused"}), f"{crash_label} Trend", crash_label)
    section_title("Year Detail")
    simple_table(
        ["Year", crash_label, "Fatalities", "Commercial-Involved", "Commercial Share"],
        [
            [
                int(row.year),
                f"{int(row.fatal_crashes):,}",
                f"{int(row.fatalities):,}",
                f"{int(row.commercial_involved):,}",
                f"{row.commercial_involved / row.fatal_crashes * 100:.1f}%",
            ]
            for row in trend.itertuples()
        ],
    )
    section_title("County Detail", f"Latest available county context for {latest_year}.")
    county_table(priority_counties, limit=30, crash_header=crash_label)

elif page == "Risk Factors":
    carrier = int(state_crashes["commercial_vehicle_involved"].sum())
    large_vehicle = int(state_crashes["large_truck_bus_involved"].sum())
    work_zone = int((state_crashes["work_zone"].fillna("").str.lower() != "none").sum())
    risk_third_value = int(state_crashes["distracted_driving"].sum()) if use_utah_all_crashes else work_zone
    risk_third_label = "Distracted-driving crashes" if use_utah_all_crashes else "Work-zone coded crashes"
    st.html(
        f"""
        <div class="insight-strip">
          <div class="insight-card"><div class="insight-value">{carrier:,}</div><div class="insight-label">Confirmed carrier indicator</div></div>
          <div class="insight-card aqua"><div class="insight-value">{large_vehicle:,}</div><div class="insight-label">Large truck or bus involved</div></div>
          <div class="insight-card light"><div class="insight-value">{risk_third_value:,}</div><div class="insight-label">{risk_third_label}</div></div>
        </div>"""
    )
    section_title(
        "Weather × Light Conditions",
        f"Cell intensity shows the relative concentration of {crash_label_short}; hover a cell for exact detail.",
    )
    conditions = (
        state_crashes.groupby(["weather", "light_condition"], as_index=False)
        .size()
    )
    condition_matrix(conditions, len(state_crashes))
    st.html('<div class="note-box">Commercial-involved means FARS recorded a motor-carrier identifier. It does not prove every person involved was working at the time.</div>')

else:
    map_title = "Reported Crash Locations" if use_utah_all_crashes else "Fatal Crash Locations"
    map_source = "UDOT" if use_utah_all_crashes else "FARS"
    section_title(map_title, f"Reported {map_source} coordinates for {selected_state} during {period}.")
    map_data = state_crashes.dropna(subset=["latitude", "longitude"]).copy()
    if use_utah_all_crashes:
        severity_order = [
            "Fatal",
            "Suspected Serious Injury",
            "Suspected Minor Injury",
            "Possible Injury",
            "No Injury/PDO",
        ]
        selected_severities = st.multiselect(
            "Injury level",
            severity_order,
            default=severity_order,
            help="Filter the crash points displayed on the map by reported injury severity.",
        )
        map_data = map_data[
            map_data["crash_severity_desc"].isin(selected_severities)
        ].copy()
        if map_data.empty:
            st.info("Select at least one injury level to display crash locations.")
            st.stop()
        if len(map_data) > 25_000:
            map_data = map_data.sample(25_000, random_state=42)
        map_data["street"] = map_data["main_road_name"].fillna("").where(
            map_data["main_road_name"].fillna("").ne(""),
            map_data["route_id"].fillna("Unknown roadway"),
        )
        map_data["location"] = map_data["location_desc"].fillna("Location not reported")
        map_data["severity"] = map_data["crash_severity_desc"].fillna("Unknown")
        map_data["collision"] = map_data["manner_collision_desc"].fillna("Unknown")
        map_data["vehicles"] = pd.to_numeric(
            map_data["number_vehicles_involved"], errors="coerce"
        ).fillna(0).astype(int)
        map_data["color"] = map_data["severity"].map(
            {
                "Fatal": [180, 35, 45, 190],
                "Suspected Serious Injury": [230, 135, 35, 180],
                "Suspected Minor Injury": [49, 213, 208, 165],
                "Possible Injury": [91, 177, 173, 150],
                "No Injury/PDO": [33, 63, 87, 95],
            }
        ).apply(lambda value: value if isinstance(value, list) else [33, 63, 87, 110])
        center_lat = float(map_data["latitude"].median())
        center_lon = float(map_data["longitude"].median())
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius=55,
            radius_min_pixels=2,
            radius_max_pixels=9,
            pickable=True,
            auto_highlight=True,
        )
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=pdk.ViewState(
                latitude=center_lat, longitude=center_lon, zoom=6.2, pitch=0
            ),
            map_style="light",
            tooltip={
                "html": (
                    "<b>{severity}</b><br/>"
                    "<b>{street}</b><br/>{location}<br/>"
                    "Collision: {collision}<br/>Vehicles: {vehicles}"
                ),
                "style": {
                    "backgroundColor": "#213f57",
                    "color": "white",
                    "fontFamily": "Barlow, sans-serif",
                },
            },
        )
        st.pydeck_chart(deck, width="stretch", height=680)
        st.html(
            """
            <div class="chart-legend">
              <span><i class="legend-dot" style="background:#b4232d"></i>Fatal</span>
              <span><i class="legend-dot" style="background:#e68723"></i>Suspected serious injury</span>
              <span><i class="legend-dot" style="background:#31d5d0"></i>Suspected minor injury</span>
              <span><i class="legend-dot" style="background:#5bb1ad"></i>Possible injury</span>
              <span><i class="legend-dot" style="background:#213f57"></i>No injury / PDO</span>
            </div>
            <div class="note-box">Hover over a crash point for street, severity, date, collision type, and vehicle count.
            The map displays a reproducible sample of up to 25,000 selected points for performance.</div>
            """
        )
    else:
        if len(map_data) > 25_000:
            map_data = map_data.sample(25_000, random_state=42)
        st.map(map_data, latitude="latitude", longitude="longitude", color=AQUA)
    section_title("County Context", f"Latest-year crash rates and addressable market for {latest_year}.")
    county_table(priority_counties, limit=30, crash_header=crash_label)

with st.expander("Data sources and refresh status"):
    source_rows = [
        [row.dataset, row.description, row.years, f"{int(row.records):,}", row.refreshed_at[:10]]
        for row in sources.itertuples()
    ]
    simple_table(["Dataset", "Purpose", "Years", "Records", "Refreshed"], source_rows)
