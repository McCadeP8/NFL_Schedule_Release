from __future__ import annotations

import base64
from pathlib import Path

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
LOGO_PATH = APP_DIR / "assets" / "crestline_logo.png"

BRAND_GOLD = "#ffb810"
BRAND_DARK = "#202830"
BRAND_INK = "#18202a"
BRAND_MUTED = "#667085"
BRAND_SURFACE = "#ffffff"
BRAND_BACKGROUND = "#f5f3ee"


def image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def inject_css() -> None:
    st.html(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
  --brand-gold: {BRAND_GOLD};
  --brand-dark: {BRAND_DARK};
  --brand-ink: {BRAND_INK};
  --brand-muted: {BRAND_MUTED};
  --brand-surface: {BRAND_SURFACE};
  --brand-background: {BRAND_BACKGROUND};
}}

html, body, [class*="css"] {{
  font-family: 'Inter', sans-serif;
  color: var(--brand-ink);
}}

.stApp {{
  background:
    radial-gradient(circle at top left, rgba(255, 184, 16, 0.20), transparent 34rem),
    linear-gradient(180deg, #fbfaf7 0%, var(--brand-background) 100%);
}}

footer {{ visibility: hidden; }}

.block-container {{
  max-width: 1240px !important;
  padding-top: 1.5rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
}}

.crestline-masthead {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 28px;
  align-items: center;
  padding: 26px 0 22px;
  border-bottom: 1px solid rgba(32, 40, 48, 0.14);
}}

.brand-lockup {{
  display: flex;
  align-items: center;
  gap: 24px;
}}

.brand-logo {{
  width: 248px;
  max-width: 42vw;
  height: auto;
  object-fit: contain;
}}

.mast-kicker {{
  color: var(--brand-gold);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 3px;
  text-transform: uppercase;
}}

.mast-title {{
  color: var(--brand-dark);
  font-size: 46px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.02;
  margin-top: 5px;
}}

.mast-subtitle {{
  color: var(--brand-muted);
  font-size: 16px;
  font-weight: 500;
  line-height: 1.55;
  max-width: 670px;
  margin-top: 10px;
}}

.status-pill {{
  justify-self: end;
  color: var(--brand-dark);
  background: rgba(255, 184, 16, 0.18);
  border: 1px solid rgba(255, 184, 16, 0.44);
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 1.2px;
  padding: 10px 15px;
  text-transform: uppercase;
  white-space: nowrap;
}}

.panel {{
  background: rgba(255, 255, 255, 0.90);
  border: 1px solid rgba(32, 40, 48, 0.12);
  border-radius: 8px;
  box-shadow: 0 20px 50px rgba(32, 40, 48, 0.08);
  padding: 22px;
}}

.panel-title {{
  color: var(--brand-dark);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 1.3px;
  text-transform: uppercase;
  margin-bottom: 5px;
}}

.panel-copy {{
  color: var(--brand-muted);
  font-size: 14px;
  line-height: 1.55;
  margin-bottom: 16px;
}}

.prediction-card {{
  background:
    linear-gradient(135deg, rgba(32, 40, 48, 0.98), rgba(24, 32, 42, 0.94)),
    var(--brand-dark);
  border-radius: 8px;
  color: white;
  padding: 30px;
  min-height: 302px;
  position: relative;
  overflow: hidden;
}}

.prediction-card::after {{
  content: "";
  position: absolute;
  width: 260px;
  height: 260px;
  right: -110px;
  top: -120px;
  border-radius: 999px;
  background: rgba(255, 184, 16, 0.28);
}}

.prediction-label {{
  color: rgba(255, 255, 255, 0.74);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
}}

.prediction-value {{
  color: white;
  font-size: 74px;
  font-weight: 800;
  letter-spacing: -0.05em;
  line-height: 0.95;
  margin: 18px 0 6px;
}}

.prediction-unit {{
  color: var(--brand-gold);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1px;
  text-transform: uppercase;
}}

.prediction-note {{
  color: rgba(255, 255, 255, 0.72);
  font-size: 14px;
  line-height: 1.55;
  margin-top: 24px;
  max-width: 470px;
}}

.metric-strip {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}}

.mini-metric {{
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(32, 40, 48, 0.10);
  border-radius: 8px;
  padding: 16px;
}}

.mini-value {{
  color: var(--brand-dark);
  font-size: 26px;
  font-weight: 800;
  letter-spacing: -0.03em;
}}

.mini-label {{
  color: var(--brand-muted);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  margin-top: 4px;
}}

.topic-grid {{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 14px 0 20px;
}}

.topic-card {{
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(32, 40, 48, 0.11);
  border-left: 5px solid var(--brand-gold);
  border-radius: 8px;
  padding: 17px;
  box-shadow: 0 12px 28px rgba(32, 40, 48, 0.06);
}}

.topic-name {{
  color: var(--brand-muted);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}}

.topic-value {{
  color: var(--brand-dark);
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.04em;
  margin-top: 6px;
}}

.topic-detail {{
  color: var(--brand-muted);
  font-size: 13px;
  font-weight: 600;
  margin-top: 4px;
}}

.tab-note {{
  color: var(--brand-muted);
  font-size: 14px;
  line-height: 1.55;
  margin: 0 0 12px;
}}

.stTabs [data-baseweb="tab-list"] {{
  gap: 8px;
  border-bottom: 1px solid rgba(32, 40, 48, 0.12);
}}

.stTabs [data-baseweb="tab"] {{
  color: var(--brand-dark);
  font-weight: 800;
}}

.stTabs [aria-selected="true"] {{
  color: var(--brand-dark) !important;
  background: rgba(255, 184, 16, 0.18);
  border-radius: 7px 7px 0 0;
}}

.stSlider [data-baseweb="slider"] > div {{
  color: var(--brand-gold);
}}

div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] *,
div[data-testid="stNumberInput"] label,
div[data-testid="stNumberInput"] label *,
.stNumberInput label,
.stNumberInput label * {{
  color: var(--brand-dark) !important;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}}

.stNumberInput input,
div[data-testid="stNumberInput"] input {{
  color: var(--brand-dark) !important;
  background: #ffffff !important;
  border-radius: 7px;
}}

button[kind="secondary"], button[kind="primary"] {{
  border-radius: 7px !important;
  font-weight: 800 !important;
}}

@media (max-width: 760px) {{
  .crestline-masthead {{
    grid-template-columns: 1fr;
  }}
  .brand-lockup {{
    align-items: flex-start;
    flex-direction: column;
  }}
  .brand-logo {{
    max-width: 78vw;
  }}
  .mast-title {{
    font-size: 36px;
  }}
  .status-pill {{
    justify-self: start;
  }}
  .metric-strip {{
    grid-template-columns: 1fr;
  }}
  .topic-grid {{
    grid-template-columns: 1fr;
  }}
}}
</style>
"""
    )


def inflation_factor(inflation_rate: float) -> float:
    return 1 + (inflation_rate / 100)


def dummy_prediction(square_feet: float, window_square_feet: float, concrete_yards: float) -> float:
    """Replace these starter weights with a trained model when real project data is ready."""
    base = 18_500
    conditioned_area = square_feet * 74.50
    glazing_factor = window_square_feet * 33.25
    concrete_factor = concrete_yards * 168.00
    scale_credit = min(square_feet, 8_000) * 1.35
    return max(0, base + conditioned_area + glazing_factor + concrete_factor - scale_credit)


def format_money(value: float) -> str:
    return f"${value:,.0f}"


def format_qty(value: float, unit: str) -> str:
    if unit == "units":
        return f"{value:,.1f} units"
    return f"{value:,.0f} {unit}"


def render_masthead() -> None:
    logo_src = image_data_uri(LOGO_PATH)
    st.html(
        f"""
<div class="crestline-masthead">
  <div class="brand-lockup">
    <img class="brand-logo" src="{logo_src}" alt="Crestline Homes logo">
    <div>
      <div class="mast-kicker">Build Projection</div>
      <div class="mast-title">Project Estimate Model</div>
      <div class="mast-subtitle">
        Enter the core build quantities and generate a fast planning number.
        The current model is seeded with dummy weights so the workflow is ready
        before real historical bids are loaded.
      </div>
    </div>
  </div>
  <div class="status-pill">Prototype Model</div>
</div>
"""
    )


def render_prediction(value: float, inflation_rate: float) -> None:
    st.html(
        f"""
<div class="prediction-card">
  <div class="prediction-label">Inflation-Adjusted Number</div>
  <div class="prediction-value">{format_money(value)}</div>
  <div class="prediction-unit">Planning Estimate · {inflation_rate:.1f}% Inflation</div>
  <div class="prediction-note">
    This is a placeholder projection using dummy coefficients for square footage,
    window area, concrete volume, and a future-cost inflation assumption. Swap in
    trained coefficients or a saved model once your real project dataset is available.
  </div>
</div>
"""
    )


def render_metric_strip(square_feet: float, window_square_feet: float, concrete_yards: float) -> None:
    window_ratio = 0 if square_feet == 0 else window_square_feet / square_feet
    concrete_per_1000 = 0 if square_feet == 0 else concrete_yards / (square_feet / 1_000)
    cards = [
        (f"{square_feet:,.0f}", "Square Feet"),
        (f"{window_ratio:.1%}", "Window Ratio"),
        (f"{concrete_per_1000:.1f}", "Yards / 1k SF"),
    ]
    st.html(
        '<div class="metric-strip">'
        + "".join(
            f"""
<div class="mini-metric">
  <div class="mini-value">{value}</div>
  <div class="mini-label">{label}</div>
</div>
"""
            for value, label in cards
        )
        + "</div>"
    )


def subtopic_rows(category: str, driver_value: float, inflation_rate: float) -> list[dict[str, float | str]]:
    factor = inflation_factor(inflation_rate)
    if category == "square":
        rows = [
            ("Square Tile", driver_value * 0.18, "sf", 11.25),
            ("Square Carpet", driver_value * 0.32, "sf", 6.80),
            ("LVP / Hardwood", driver_value * 0.22, "sf", 9.90),
            ("Drywall Surface", driver_value * 2.85, "sf", 2.15),
            ("Framing Labor", driver_value, "sf", 18.40),
            ("Interior Trim", driver_value * 0.74, "lf", 7.25),
        ]
    elif category == "windows":
        rows = [
            ("Window A", driver_value * 0.55, "sf", 78.00),
            ("Window B", driver_value * 0.30, "sf", 96.00),
            ("Specialty Glass", driver_value * 0.15, "sf", 132.00),
            ("Patio / Slider Units", max(1, driver_value / 115), "units", 1_650.00),
            ("Trim + Flashing", driver_value, "sf", 14.50),
            ("Screens + Hardware", driver_value * 0.82, "sf", 8.75),
        ]
    else:
        rows = [
            ("Real Concrete", driver_value * 0.82, "cy", 190.00),
            ("Fake Concrete", driver_value * 0.18, "cy", 145.00),
            ("Rebar / Mesh", driver_value * 110, "lb", 1.55),
            ("Forms + Prep", driver_value, "cy", 68.00),
            ("Pump / Mobilization", max(1, driver_value / 55), "units", 1_250.00),
            ("Finish Labor", driver_value, "cy", 82.00),
        ]

    return [
        {
            "Subtopic": name,
            "Quantity": quantity,
            "Unit": unit,
            "Current Unit Cost": unit_cost,
            "Future Unit Cost": unit_cost * factor,
            "Future Cost": quantity * unit_cost * factor,
        }
        for name, quantity, unit, unit_cost in rows
    ]


def past_build_data(category: str) -> pd.DataFrame:
    if category == "square":
        records = [
            ("2024-08", "Canyon Ridge", 2410, 435, 760, 410, 188_200),
            ("2025-01", "Juniper", 1985, 360, 620, 335, 158_400),
            ("2025-06", "Summit", 3160, 570, 990, 620, 246_750),
            ("2025-11", "Aspen", 3825, 690, 1225, 780, 302_900),
            ("2026-04", "Wasatch", 2875, 520, 920, 545, 229_300),
        ]
        return pd.DataFrame(
            records,
            columns=["Build Date", "Past Build", "Square Feet", "Square Tile SF", "Square Carpet SF", "LVP / Hardwood SF", "Total Cost"],
        )
    if category == "windows":
        records = [
            ("2024-08", "Canyon Ridge", 285, 157, 86, 42, 48_600),
            ("2025-01", "Juniper", 210, 116, 63, 31, 36_950),
            ("2025-06", "Summit", 365, 201, 110, 54, 62_400),
            ("2025-11", "Aspen", 455, 250, 137, 68, 78_850),
            ("2026-04", "Wasatch", 335, 184, 101, 50, 58_700),
        ]
        return pd.DataFrame(
            records,
            columns=["Build Date", "Past Build", "Window SF", "Window A SF", "Window B SF", "Specialty SF", "Total Cost"],
        )

    records = [
        ("2024-08", "Canyon Ridge", 42, 34.4, 7.6, 4_620, 21_500),
        ("2025-01", "Juniper", 36, 29.5, 6.5, 3_960, 18_900),
        ("2025-06", "Summit", 55, 45.1, 9.9, 6_050, 28_800),
        ("2025-11", "Aspen", 69, 56.6, 12.4, 7_590, 36_950),
        ("2026-04", "Wasatch", 48, 39.4, 8.6, 5_280, 25_900),
    ]
    return pd.DataFrame(
        records,
        columns=["Build Date", "Past Build", "Concrete CY", "Real Concrete CY", "Fake Concrete CY", "Rebar / Mesh LB", "Total Cost"],
    )


def render_subtopic_cards(rows: list[dict[str, float | str]]) -> None:
    cards = []
    for row in rows:
        cards.append(
            f"""
<div class="topic-card">
  <div class="topic-name">{row["Subtopic"]}</div>
  <div class="topic-value">{format_money(float(row["Future Cost"]))}</div>
  <div class="topic-detail">{format_qty(float(row["Quantity"]), str(row["Unit"]))} · {format_money(float(row["Future Unit Cost"]))}/{row["Unit"]}</div>
</div>
"""
        )
    st.html(f'<div class="topic-grid">{"".join(cards)}</div>')


def render_subtopic_tab(category: str, driver_value: float, inflation_rate: float, intro: str) -> None:
    rows = subtopic_rows(category, driver_value, inflation_rate)
    total = sum(float(row["Future Cost"]) for row in rows)
    st.html(
        f"""
<div class="panel">
  <div class="panel-title">{format_money(total)} Forecast</div>
  <div class="panel-copy">{intro}</div>
</div>
"""
    )
    render_subtopic_cards(rows)
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Quantity": st.column_config.NumberColumn("Quantity", format="%.1f"),
            "Current Unit Cost": st.column_config.NumberColumn("Current Unit Cost", format="$%.2f"),
            "Future Unit Cost": st.column_config.NumberColumn("Future Unit Cost", format="$%.2f"),
            "Future Cost": st.column_config.NumberColumn("Future Cost", format="$%d"),
        },
    )
    st.write("")
    st.html(
        """
<div class="panel">
  <div class="panel-title">Past Builds</div>
  <div class="panel-copy">Five dummy historical records from the last two years for calibration layout.</div>
</div>
"""
    )
    st.dataframe(
        past_build_data(category),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Total Cost": st.column_config.NumberColumn("Total Cost", format="$%d"),
        },
    )


def render_dummy_data(inflation_rate: float) -> None:
    factor = inflation_factor(inflation_rate)
    data = pd.DataFrame(
        [
            {"Plan": "Canyon Ridge", "Build Date": "2024-08", "Square Feet": 2410, "Window SF": 285, "Concrete CY": 42, "Result": 207500},
            {"Plan": "Juniper", "Build Date": "2025-01", "Square Feet": 1985, "Window SF": 210, "Concrete CY": 36, "Result": 176900},
            {"Plan": "Summit", "Build Date": "2025-06", "Square Feet": 3160, "Window SF": 365, "Concrete CY": 55, "Result": 262250},
            {"Plan": "Aspen", "Build Date": "2025-11", "Square Feet": 3825, "Window SF": 455, "Concrete CY": 69, "Result": 312800},
            {"Plan": "Wasatch", "Build Date": "2026-04", "Square Feet": 2875, "Window SF": 335, "Concrete CY": 48, "Result": 235600},
        ]
    )
    data["Inflation Adjusted"] = data["Result"] * factor
    st.dataframe(
        data,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Result": st.column_config.NumberColumn("Result", format="$%d"),
            "Inflation Adjusted": st.column_config.NumberColumn("Inflation Adjusted", format="$%d"),
        },
    )


st.set_page_config(
    page_title="Build Projection | Crestline Homes",
    page_icon=str(LOGO_PATH),
    layout="wide",
)

inject_css()
render_masthead()

st.write("")
left, right = st.columns([0.43, 0.57], gap="large")

with left:
    st.html(
        """
<div class="panel">
  <div class="panel-title">Inputs</div>
  <div class="panel-copy">Adjust quantities to generate an immediate projection.</div>
</div>
"""
    )
    square_feet = st.number_input(
        "Square Footage",
        min_value=0.0,
        max_value=20_000.0,
        value=2_750.0,
        step=50.0,
    )
    window_square_feet = st.number_input(
        "Window Square Feet",
        min_value=0.0,
        max_value=4_000.0,
        value=320.0,
        step=10.0,
    )
    concrete_yards = st.number_input(
        "Cubic Yards of Concrete",
        min_value=0.0,
        max_value=1_000.0,
        value=48.0,
        step=1.0,
    )
    inflation_rate = st.slider(
        "Future Inflation %",
        min_value=0.0,
        max_value=15.0,
        value=4.5,
        step=0.25,
    )

    st.write("")
    render_metric_strip(square_feet, window_square_feet, concrete_yards)

with right:
    prediction = dummy_prediction(square_feet, window_square_feet, concrete_yards)
    future_prediction = prediction * inflation_factor(inflation_rate)
    render_prediction(future_prediction, inflation_rate)

st.write("")
square_tab, window_tab, concrete_tab = st.tabs(
    ["Square Footage", "Windows", "Concrete"]
)

with square_tab:
    render_subtopic_tab(
        "square",
        square_feet,
        inflation_rate,
        "Predicted square-foot-driven subtopics including square tile, square carpet, LVP, drywall, framing, and interior trim.",
    )

with window_tab:
    render_subtopic_tab(
        "windows",
        window_square_feet,
        inflation_rate,
        "Predicted window package subtopics including Window A, Window B, specialty glass, patio units, trim, flashing, and screens.",
    )

with concrete_tab:
    render_subtopic_tab(
        "concrete",
        concrete_yards,
        inflation_rate,
        "Predicted concrete package subtopics including real concrete, fake concrete, rebar, forms, pump mobilization, and finish labor.",
    )

st.write("")
st.html(
    """
<div class="panel">
  <div class="panel-title">Starter Data</div>
  <div class="panel-copy">Dummy whole-build records included for layout, model replacement, and future calibration.</div>
</div>
"""
)
render_dummy_data(inflation_rate)
