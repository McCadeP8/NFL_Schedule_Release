from __future__ import annotations

from pathlib import Path
import html

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

TEAM_NAMES = {
    "ANA": "Anaheim", "BOS": "Boston", "BUF": "Buffalo", "CAR": "Carolina", "CBJ": "Columbus",
    "CGY": "Calgary", "CHI": "Chicago", "COL": "Colorado", "DAL": "Dallas", "DET": "Detroit",
    "EDM": "Edmonton", "FLA": "Florida", "LAK": "Los Angeles", "MIN": "Minnesota", "MTL": "Montreal",
    "NJD": "New Jersey", "NSH": "Nashville", "NYI": "New York I", "NYR": "New York R", "OTT": "Ottawa",
    "PHI": "Philadelphia", "PIT": "Pittsburgh", "SEA": "Seattle", "SJS": "San Jose", "STL": "St. Louis",
    "TBL": "Tampa Bay", "TOR": "Toronto", "UTA": "Utah", "VAN": "Vancouver", "VGK": "Vegas",
    "WPG": "Winnipeg", "WSH": "Washington",
}

st.set_page_config(page_title="NHL State Lab", page_icon="🏒", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #07111f; color: #f5f7fb; }
    [data-testid="stSidebar"] { background: #0b1727; }
    .hero { padding: 1.2rem 1.4rem; border: 1px solid #20344c; border-radius: 16px;
            background: linear-gradient(120deg,#0c1c31 0%,#102941 60%,#123d50 100%); }
    .hero h1 { margin: 0; letter-spacing: -0.04em; }
    .eyebrow { color:#62d7d3; font-weight:700; letter-spacing:.12em; font-size:.78rem; }
    div[data-testid="stMetric"] { background:#0d1b2c; border:1px solid #20344c;
                                  padding:12px; border-radius:12px; }
    .balance-groups { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin:18px 0 12px; }
    .context-metric-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:17px 0 24px; }
    .context-metric-card { position:relative; overflow:hidden; min-height:112px; padding:16px 18px;
                           border:1px solid #304860; border-radius:14px; background:linear-gradient(145deg,#12243a,#182d44);
                           box-shadow:0 9px 22px rgba(0,0,0,.17); }
    .context-metric-label { color:#8ea5ba; font-size:11px; font-weight:900; letter-spacing:.11em; text-transform:uppercase; }
    .context-metric-value { margin-top:12px; color:#fff; font-size:35px; font-weight:950; letter-spacing:-.035em; line-height:1; }
    .context-metric-detail { margin-top:8px; color:#7890a8; font-size:11px; font-weight:700; }
    .context-rank-pill { position:absolute; right:15px; bottom:14px; padding:6px 10px; border-radius:9px;
                         color:#e4edf6; background:#21374d; border:1px solid #46647f; font-size:15px; font-weight:950; }
    .balance-group { min-width:0; }
    .balance-group-title { margin:0 0 10px; padding:0 3px 10px; border-bottom:2px solid #2a425c;
                           font-size:27px; font-weight:950; letter-spacing:-.025em; color:#fff; }
    .balance-group-title span { display:block; margin-top:3px; color:#7890a8; font-size:11px;
                                font-weight:850; letter-spacing:.13em; text-transform:uppercase; }
    .balance-group-cards { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
    .balance-group-cards .balance-metric-card:nth-child(3) { grid-column:1 / span 2; }
    .balance-metric-card { position:relative; overflow:hidden; min-height:154px; padding:18px 19px 16px;
                           border-radius:16px; color:#fff; box-shadow:0 12px 28px rgba(0,0,0,.24); }
    .balance-metric-card::after { content:""; position:absolute; width:150px; height:150px; right:-70px;
                                  top:-70px; border-radius:50%; border:1px solid rgba(255,255,255,.18);
                                  box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 55px rgba(255,255,255,.025); }
    .rank-elite { background:linear-gradient(135deg,#045c43,#07845f 60%,#0aaa78); border:1px solid #28d39f; }
    .rank-soft-good { background:linear-gradient(135deg,#416b58,#547f69 60%,#68947b); border:1px solid #8bc3a5; }
    .rank-soft-low { background:linear-gradient(135deg,#765058,#8b5d66 60%,#a46b75); border:1px solid #cf929d; }
    .rank-low { background:linear-gradient(135deg,#711823,#9d2130 60%,#c52e40); border:1px solid #ef6272; }
    .rank-neutral { background:linear-gradient(135deg,#243b53,#304e69 60%,#3d607e); border:1px solid #6688a5; }
    .metric-topline { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; position:relative; z-index:1; }
    .metric-label { max-width:76%; font-size:12px; line-height:1.25; font-weight:850; letter-spacing:.085em;
                    text-transform:uppercase; color:rgba(255,255,255,.82); }
    .metric-rank-pill { position:absolute; right:15px; bottom:14px; z-index:2; padding:6px 10px; border-radius:9px;
                        background:rgba(0,0,0,.24); border:1px solid rgba(255,255,255,.34); font-size:15px; font-weight:950; }
    .metric-value { position:relative; z-index:1; margin-top:18px; font-size:43px; font-weight:900;
                    letter-spacing:-.045em; line-height:.92; }
    .metric-comparison { position:relative; z-index:1; max-width:68%; margin-top:11px; font-size:12px; font-weight:750;
                         color:rgba(255,255,255,.78); }
    .nhl-table-shell { margin:10px 0 25px; overflow:hidden; border:1px solid #263b53; border-radius:14px;
                       background:#0c1828; box-shadow:0 12px 28px rgba(0,0,0,.18); }
    .nhl-table-scroll { overflow:auto; scrollbar-color:#38506b #0c1828; }
    .nhl-table { width:100%; min-width:760px; border-collapse:separate; border-spacing:0; font-size:13px; }
    .nhl-table thead th { position:sticky; top:0; z-index:3; padding:12px 14px; background:#14263a;
                          border-bottom:2px solid #2d4863; color:#a9bbcd; text-align:left; font-size:11px;
                          font-weight:900; letter-spacing:.1em; text-transform:uppercase; white-space:nowrap; }
    .nhl-table tbody tr { background:#0c1828; transition:background .14s ease; }
    .nhl-table tbody tr:nth-child(even) { background:#101f31; }
    .nhl-table tbody tr:hover { background:#173149; }
    .nhl-table td { padding:11px 14px; border-bottom:1px solid #1f3449; color:#dce7f3; white-space:nowrap; }
    .nhl-table td.numeric,.nhl-table th.numeric { text-align:right; font-variant-numeric:tabular-nums; }
    .nhl-table td.primary { color:#fff; font-weight:850; }
    .table-pill { display:inline-flex; min-width:48px; justify-content:center; padding:4px 8px; border-radius:999px;
                  font-size:10px; font-weight:900; letter-spacing:.08em; }
    .pill-for { color:#8ff0ce; background:rgba(16,163,127,.17); border:1px solid rgba(38,201,154,.38); }
    .pill-allowed { color:#ff9eaa; background:rgba(201,54,73,.18); border:1px solid rgba(235,102,117,.38); }
    .pill-neutral { color:#b9cadb; background:#1a2c40; border:1px solid #304a64; }
    .nhl-table .group-row th { position:sticky; top:0; z-index:4; padding:9px 12px; color:#fff;
                               text-align:center; font-size:12px; letter-spacing:.12em; }
    .nhl-table .group-row th[rowspan] { text-align:left; vertical-align:bottom; background:#14263a; }
    .nhl-table .group-neutral { background:#33465a; }
    .nhl-table .group-actual { background:#205f50; }
    .nhl-table .group-expected { background:#285778; }
    .nhl-table .group-difference { background:#674a18; }
    .nhl-table .subhead-row th { top:36px; text-align:right; }
    .game-state-table { min-width:1280px; font-size:16px; }
    .game-state-table td { padding:15px 17px; font-size:16px; line-height:1.25; }
    .game-state-table td.primary { font-size:18px; }
    .game-state-table thead th { padding:14px 16px; font-size:13px; }
    .game-state-table .group-row th { font-size:15px; padding:12px 15px; }
    .game-state-table .subhead-row th { top:43px; font-size:13px; }
    .league-balance-table { min-width:1780px; font-size:14px; }
    .league-balance-table td { padding:13px 14px; font-size:14px; line-height:1.2; }
    .league-balance-table td.primary { font-size:16px; }
    .league-balance-table thead th { padding:13px 13px; font-size:12px; }
    .league-balance-table .group-row th { font-size:14px; padding:11px 13px; }
    .league-balance-table .subhead-row th { top:40px; font-size:12px; }
    .league-balance-table td.cell-elite { background:rgba(7,132,95,.38); color:#f5fffb; font-weight:900; }
    .league-balance-table td.cell-soft-good { background:rgba(104,148,123,.32); color:#f7fffa; font-weight:850; }
    .league-balance-table td.cell-soft-low { background:rgba(164,107,117,.32); color:#fff7f8; font-weight:850; }
    .league-balance-table td.cell-low { background:rgba(197,46,64,.40); color:#fff8f9; font-weight:900; }
    .league-balance-table .league-row td { background:#182b40; color:#ffffff; font-weight:900; border-top:2px solid #496983; }
    .league-balance-table .rank-cell { font-size:15px; font-weight:950; }
    .goals-split { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; align-items:start; }
    .goal-panel { min-width:0; }
    .goal-panel-title { display:flex; align-items:center; justify-content:space-between; margin:0 0 8px;
                        padding:13px 16px; border-radius:12px 12px 0 0; font-size:22px; font-weight:950; color:#fff; }
    .goal-panel-title small { font-size:11px; color:rgba(255,255,255,.75); text-transform:uppercase; letter-spacing:.1em; }
    .goal-panel.for .goal-panel-title { background:linear-gradient(120deg,#075d48,#0c8b69); }
    .goal-panel.allowed .goal-panel-title { background:linear-gradient(120deg,#761d2a,#b42d40); }
    .goal-panel .nhl-table-shell { margin-top:0; border-radius:0 0 14px 14px; }
    .goal-panel .nhl-table { min-width:710px; }
    .flow-hero { margin:8px 0 16px; padding:18px 20px; border:1px solid #2a425c; border-radius:14px;
                 background:linear-gradient(135deg,#10243a,#172f48); }
    .flow-hero h2 { margin:0 0 7px; font-size:31px; letter-spacing:-.03em; }
    .flow-hero p { margin:0; color:#aebfd0; font-size:15px; line-height:1.45; }
    .flow-summary-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin:14px 0 20px; }
    .flow-summary-card { min-height:104px; padding:15px 16px; border:1px solid #304860; border-radius:12px;
                         background:#102034; box-shadow:0 9px 22px rgba(0,0,0,.16); }
    .flow-summary-label { color:#8ea5ba; font-size:11px; font-weight:900; letter-spacing:.11em; text-transform:uppercase; }
    .flow-summary-value { margin-top:10px; color:#fff; font-size:32px; font-weight:950; letter-spacing:-.035em; line-height:1; }
    .flow-summary-detail { margin-top:8px; color:#7890a8; font-size:11px; font-weight:750; }
    .flow-panels { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; align-items:start; }
    .flow-panel { min-width:0; }
    .flow-panel-title { display:flex; align-items:flex-end; justify-content:space-between; gap:12px;
                        margin:0; padding:14px 16px; color:#fff; border-radius:12px 12px 0 0; }
    .flow-panel-title strong { display:block; font-size:20px; line-height:1.05; }
    .flow-panel-title span { color:rgba(255,255,255,.76); font-size:11px; font-weight:850; letter-spacing:.1em; text-transform:uppercase; }
    .flow-panel.for .flow-panel-title { background:linear-gradient(120deg,#075d48,#0c8b69); }
    .flow-panel.final .flow-panel-title { background:linear-gradient(120deg,#31495f,#486984); }
    .flow-panel.against .flow-panel-title { background:linear-gradient(120deg,#761d2a,#b42d40); }
    .flow-panel .nhl-table-shell { margin-top:0; border-radius:0 0 14px 14px; }
    .flow-panel .nhl-table-scroll { overflow-x:hidden; }
    .flow-table { width:100%; min-width:0; table-layout:fixed; font-size:11px; }
    .flow-table thead th { padding:8px 6px; font-size:9px; white-space:normal; line-height:1.1; }
    .flow-table td { padding:8px 6px; white-space:normal; line-height:1.15; vertical-align:top; }
    .flow-table td.primary { font-size:11px; }
    @media (max-width:1100px) {
      .flow-panels { grid-template-columns:1fr; }
      .flow-summary-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
    }
    @media (max-width:900px) {
      .balance-groups { grid-template-columns:1fr; }
      .context-metric-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
      .goals-split { grid-template-columns:1fr; }
    }
    </style>
    <div class="hero">
      <div class="eyebrow">GAME-STATE ANALYTICS</div>
      <h1>NHL State Lab</h1>
      <p>Manpower efficiency, post-transition scoring, and score-flow analysis.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def read_kind(kind: str, season: int) -> pd.DataFrame:
    path = DATA / f"{kind}_{season}.parquet"
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


season_files = sorted(DATA.glob("games_*.parquet"))
seasons = [int(path.stem.split("_")[-1]) for path in season_files]
if not seasons:
    st.warning("No processed seasons found. Run the ingestion command in README.md first.")
    st.stop()

with st.sidebar:
    st.subheader("Analysis Controls")
    season = st.selectbox("Season", seasons, index=len(seasons) - 1, format_func=lambda value: str(value)[-4:])
    games = read_kind("games", season)
    all_teams = sorted(
        set(games["home_team"].dropna()) | set(games["away_team"].dropna()),
        key=lambda abbreviation: TEAM_NAMES.get(abbreviation, abbreviation),
    )
    team = st.selectbox(
        "Team",
        ["All", *all_teams],
        format_func=lambda abbreviation: "All" if abbreviation == "All" else TEAM_NAMES.get(abbreviation, abbreviation),
    )
    game_type = st.radio(
        "Competition",
        [2, 3, "all"],
        format_func=lambda value: {
            2: "Regular Season",
            3: "Playoffs",
            "all": "Regular Season + Playoffs",
        }[value],
    )
    game_types = [2, 3] if game_type == "all" else [game_type]
    min_date = pd.to_datetime(games["game_date"]).min().date()
    max_date = pd.to_datetime(games["game_date"]).max().date()
    dates = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    carryover = st.slider("Carryover window", 0, 15, 5, 1, help="Credit goals scored shortly after a manpower-state change to the prior state.")
    periods = st.multiselect("Periods", [1, 2, 3, 4], default=[1, 2, 3, 4], format_func=lambda x: "OT" if x == 4 else f"Period {x}")
    minute_range = st.slider("Game minute", 0, 65, (0, 65))
    st.divider()
    st.caption("LINEUP BALANCE")
    lineup_order = ["6v3", "6v4", "6v5", "5v3", "5v4", "5v5", "5v6", "4v3", "4v4", "4v5", "4v6", "3v3", "3v4", "3v5", "3v6"]
    lineup_types = st.multiselect("Lineup types", lineup_order, default=["5v5"])
    score_options = ["Down 3+", "Down 2", "Down 1", "Tied", "Up 1", "Up 2", "Up 3+"]
    goal_differences = st.multiselect("Goal difference", score_options, default=score_options)
    team_goalie_filter = st.selectbox("Team goalie on ice", ["All", "Yes", "No"])
    opponent_goalie_filter = st.selectbox("Opponent goalie on ice", ["All", "Yes", "No"])

if isinstance(dates, tuple) and len(dates) == 2:
    start_date, end_date = map(pd.Timestamp, dates)
else:
    start_date, end_date = pd.Timestamp(min_date), pd.Timestamp(max_date)

playoff_rank_games = games[games["game_type"].eq(3)] if "game_type" in games else pd.DataFrame()
playoff_rank_teams = sorted(
    set(playoff_rank_games.get("home_team", pd.Series(dtype=object)).dropna())
    | set(playoff_rank_games.get("away_team", pd.Series(dtype=object)).dropna()),
    key=lambda abbreviation: TEAM_NAMES.get(abbreviation, abbreviation),
)
rank_teams = playoff_rank_teams if game_type == 3 else all_teams
rank_team_total = 16 if game_type == 3 else len(all_teams)


def filtered(frame: pd.DataFrame, team_only: bool = True) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    out["game_date"] = pd.to_datetime(out["game_date"])
    if team_only and team != "All" and "team" in out:
        out = out[out["team"].eq(team)]
    if "game_type" in out:
        out = out[out["game_type"].isin(game_types)]
    if "period" in out:
        out = out[out["period"].isin(periods)]
    if "game_minute" in out:
        out = out[out["game_minute"].between(*minute_range)]
    return out[out["game_date"].between(start_date, end_date)]


plays = read_kind("plays", season)
manpower_all = filtered(read_kind("manpower", season), team_only=False)
manpower = manpower_all if team == "All" else manpower_all[manpower_all["team"].eq(team)].copy() if not manpower_all.empty else manpower_all
score_states = filtered(read_kind("score_states", season))
transitions = filtered(read_kind("score_transitions", season))
moneypuck_all = read_kind("moneypuck_shots", season)
if not moneypuck_all.empty:
    game_dates = games[["game_id", "game_date"]].drop_duplicates("game_id")
    moneypuck_all = moneypuck_all.merge(game_dates, on="game_id", how="left")
    moneypuck_all["game_date"] = pd.to_datetime(moneypuck_all["game_date"])
    moneypuck_all = moneypuck_all[
        moneypuck_all["game_date"].between(start_date, end_date)
        & moneypuck_all["game_type"].isin(game_types)
        & moneypuck_all["period"].isin(periods)
        & (moneypuck_all["elapsed_seconds"] / 60).between(*minute_range)
    ].copy()
    moneypuck = moneypuck_all.copy() if team == "All" else moneypuck_all[
        moneypuck_all["home_team"].eq(team) | moneypuck_all["away_team"].eq(team)
    ].copy()
else:
    moneypuck = moneypuck_all
if not plays.empty:
    plays["game_date"] = pd.to_datetime(plays["game_date"])
    team_plays = plays[
        plays["game_date"].between(start_date, end_date)
        & plays["game_type"].isin(game_types)
        & ((plays["home_team"].eq(team) | plays["away_team"].eq(team)) if team != "All" else True)
        & plays["period"].isin(periods)
        & (plays["elapsed_seconds"] / 60).between(*minute_range)
    ].copy()
else:
    team_plays = plays

tab1, tab2, tab3, tab4 = st.tabs(
    ["Lineup Balance", "League Lineup Balance", "Score Flow", "Data Quality"]
)

def diff_bucket(values: pd.Series) -> pd.Series:
    return pd.cut(
        values,
        bins=[-np.inf, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, np.inf],
        labels=["Down 3+", "Down 2", "Down 1", "Tied", "Up 1", "Up 2", "Up 3+"],
    ).astype(str)


def invert_state(value: object) -> str:
    parts = str(value).split("v")
    return f"{parts[1]}v{parts[0]}" if len(parts) == 2 else "Unknown"


def apply_goalie_filter(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame
    if team_goalie_filter != "All":
        out = out[out["team_goalie"].eq(team_goalie_filter == "Yes")]
    if opponent_goalie_filter != "All":
        out = out[out["opponent_goalie"].eq(opponent_goalie_filter == "Yes")]
    return out


def seconds_clock(value: float) -> str:
    total = int(round(value))
    sign = "-" if total < 0 else ""
    total = abs(total)
    if total >= 3600:
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{sign}{hours}:{minutes:02d}:{seconds:02d}"
    return f"{sign}{total // 60}:{total % 60:02d}"


def signed_seconds_clock(value: float) -> str:
    total = int(round(value))
    if total == 0:
        return "0:00"
    return ("+" if total > 0 else "-") + seconds_clock(abs(total))


def game_label(team_code: str, home_team: str, away_team: str) -> str:
    opponent = away_team if home_team == team_code else home_team
    name = TEAM_NAMES.get(opponent, opponent)
    return name if home_team == team_code else f"at {name}"


def countdown_clock(period: int, elapsed_clock: str, game_type_value: int) -> str:
    minute_part, second_part = str(elapsed_clock).split(":", 1)
    elapsed = int(minute_part) * 60 + int(second_part)
    period_length = 300 if int(period) > 3 and int(game_type_value) == 2 else 1200
    return seconds_clock(max(0, period_length - elapsed))


def elapsed_start_clock(elapsed_seconds: float, game_type_value: int) -> str:
    elapsed = max(0, int(round(elapsed_seconds)))
    if elapsed < 3600:
        period = elapsed // 1200 + 1
        elapsed_in_period = elapsed % 1200
        period_length = 1200
        period_label = f"{period}P"
    else:
        overtime_length = 300 if int(game_type_value) == 2 else 1200
        overtime_elapsed = elapsed - 3600
        overtime_index = overtime_elapsed // overtime_length
        elapsed_in_period = overtime_elapsed % overtime_length
        period_length = overtime_length
        period_label = "OT" if overtime_index == 0 else f"{int(overtime_index + 1)}OT"
    return f"{seconds_clock(max(0, period_length - elapsed_in_period))} {period_label}"


def metric_card_html(card: dict[str, object]) -> str:
    rank = card.get("rank")
    rank_number = int(rank) if rank is not None and pd.notna(rank) else None
    if rank_number is None:
        rank_class = "rank-neutral"
    elif rank_number <= rank_team_total / 4:
        rank_class = "rank-elite"
    elif rank_number and rank_number <= rank_team_total / 2:
        rank_class = "rank-soft-good"
    elif rank_number and rank_number <= rank_team_total * 3 / 4:
        rank_class = "rank-soft-low"
    else:
        rank_class = "rank-low"
    rank_text = f"#{rank_number} / {rank_team_total}" if rank_number else "League"
    return (
        f'<div class="balance-metric-card {rank_class}">'
        f'<div class="metric-topline"><span class="metric-label">{html.escape(str(card["label"]))}</span></div>'
        f'<div class="metric-value">{html.escape(str(card["value"]))}</div>'
        f'<div class="metric-comparison">League average&nbsp; {html.escape(str(card["league"]))}</div>'
        f'<span class="metric-rank-pill">{rank_text}</span>'
        f'</div>'
    )


def render_metric_cards(
    actual_cards: list[dict[str, object]],
    expected_cards: list[dict[str, object]],
    difference_cards: list[dict[str, object]],
) -> None:
    groups = []
    for title, subtitle, cards in (
        ("Actual", "What reached the scoreboard", actual_cards),
        ("Expected", "Chance quality from MoneyPuck xG", expected_cards),
        ("Difference", "Actual minus expected", difference_cards),
    ):
        groups.append(
            f'<section class="balance-group"><h3 class="balance-group-title">{title}'
            f'<span>{subtitle}</span></h3><div class="balance-group-cards">'
            f'{"".join(metric_card_html(card) for card in cards)}</div></section>'
        )
    st.html(f'<div class="balance-groups">{"".join(groups)}</div>')


def render_context_cards(cards: list[dict[str, str]]) -> None:
    content = "".join(
        f'<div class="context-metric-card"><span class="context-rank-pill">{html.escape(card["rank"])}</span>'
        f'<div class="context-metric-label">{html.escape(card["label"])}</div>'
        f'<div class="context-metric-value">{html.escape(card["value"])}</div>'
        f'<div class="context-metric-detail">{html.escape(card["detail"])}</div></div>'
        for card in cards
    )
    st.html(f'<div class="context-metric-grid">{content}</div>')


def render_table(
    frame: pd.DataFrame,
    *,
    height: int = 480,
    formats: dict[str, object] | None = None,
    primary: str | None = None,
    pill: str | None = None,
) -> None:
    if frame.empty:
        st.info("No rows match the current filters.")
        return
    formats = formats or {}
    headers = []
    for column in frame.columns:
        numeric = pd.api.types.is_numeric_dtype(frame[column]) and not pd.api.types.is_bool_dtype(frame[column])
        headers.append(f'<th class="{"numeric" if numeric else ""}">{html.escape(str(column))}</th>')
    rows = []
    for _, record in frame.iterrows():
        cells = []
        for column in frame.columns:
            value = record[column]
            formatter = formats.get(column)
            if pd.isna(value):
                shown = "—"
            elif callable(formatter):
                shown = str(formatter(value))
            elif isinstance(formatter, str):
                shown = format(value, formatter)
            elif isinstance(value, (pd.Timestamp,)):
                shown = value.strftime("%b %d, %Y") if hasattr(value, "strftime") else str(value)
            elif isinstance(value, (bool, np.bool_)):
                shown = "✓" if value else ""
            elif isinstance(value, float):
                shown = f"{value:,.2f}"
            else:
                shown = str(value)
            classes = []
            if pd.api.types.is_numeric_dtype(frame[column]) and not pd.api.types.is_bool_dtype(frame[column]):
                classes.append("numeric")
            if column == primary:
                classes.append("primary")
            content = html.escape(shown)
            if column == pill:
                pill_class = "pill-for" if shown == "FOR" else "pill-allowed" if shown == "ALLOWED" else "pill-neutral"
                content = f'<span class="table-pill {pill_class}">{content}</span>'
            cells.append(f'<td class="{" ".join(classes)}">{content}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    st.html(
        f'<div class="nhl-table-shell"><div class="nhl-table-scroll" style="max-height:{height}px">'
        f'<table class="nhl-table"><thead><tr>{"".join(headers)}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        f'</div></div>'
    )


def render_game_state_table(frame: pd.DataFrame) -> None:
    rows = []
    for _, row in frame.iterrows():
        cells = [
            html.escape(str(row["Date"])), html.escape(str(row["Game"])), html.escape(str(row["Result"])),
            html.escape(str(row["Time in State"])),
            f"{row['Actual GF']:.0f}", f"{row['Actual GA']:.0f}", f"{row['Actual GD']:+.0f}",
            f"{row['Expected GF']:.2f}", f"{row['Expected GA']:.2f}", f"{row['Expected GD']:+.2f}",
            f"{row['Difference GF']:+.2f}", f"{row['Difference GA']:+.2f}", f"{row['Difference GD']:+.2f}",
        ]
        row_html = "".join(
            f'<td class="{"primary" if idx == 1 else "numeric" if idx >= 4 else ""}">{value}</td>'
            for idx, value in enumerate(cells)
        )
        rows.append(f"<tr>{row_html}</tr>")
    st.html(
        '<div class="nhl-table-shell"><div class="nhl-table-scroll" style="max-height:620px">'
        '<table class="nhl-table game-state-table"><thead>'
        '<tr class="group-row"><th rowspan="2">Date</th><th rowspan="2">Game</th><th rowspan="2">Result</th>'
        '<th rowspan="2">Time in State</th><th colspan="3" class="group-actual">Actual</th>'
        '<th colspan="3" class="group-expected">Expected</th><th colspan="3" class="group-difference">Difference</th></tr>'
        '<tr class="subhead-row"><th>GF</th><th>GA</th><th>GD</th><th>GF</th><th>GA</th><th>GD</th>'
        '<th>GF</th><th>GA</th><th>GD</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></div>'
    )


def render_league_balance_table(frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("No teams match the current lineup filters.")
        return
    columns = [
        "Rank", "Team", "Record", "Points Percentage", "Time Played", "Goals Scored", "Goals Allowed", "Goals Difference",
        "Actual Goal Scored", "Actual Goal Allowed", "Actual GD/60",
        "Expected Goal Scored", "Expected Goal Allowed", "Expected GD/60",
        "Difference Goal Scored", "Difference Goal Allowed", "Difference GD/60",
    ]
    rows = []
    for _, row in frame[columns].iterrows():
        is_league = str(row["Team"]) == "League Average"
        row_classes = ["league-row"] if is_league else []
        row_class = f' class="{" ".join(row_classes)}"' if row_classes else ""
        cell_html = []
        for column in columns:
            value = row[column]
            classes = []
            if column == "Team":
                classes.append("primary")
            if column == "Rank":
                classes.append("rank-cell")
            if column not in {"Team", "Record"}:
                classes.append("numeric")
            cell_class = frame.at[row.name, f"__class_{column}"] if f"__class_{column}" in frame else ""
            if cell_class:
                classes.append(cell_class)
            cell_html.append(f'<td class="{" ".join(classes)}">{html.escape(str(value))}</td>')
        rows.append(f'<tr{row_class}>{"".join(cell_html)}</tr>')
    st.html(
        '<div class="nhl-table-shell"><div class="nhl-table-scroll" style="max-height:760px">'
        '<table class="nhl-table league-balance-table"><thead>'
        '<tr class="group-row"><th rowspan="2">Rank</th><th rowspan="2">Team</th>'
        '<th colspan="6" class="group-neutral">Context</th>'
        '<th colspan="3" class="group-actual">Actual</th>'
        '<th colspan="3" class="group-expected">Expected</th>'
        '<th colspan="3" class="group-difference">Difference</th></tr>'
        '<tr class="subhead-row"><th>Record</th><th>Pts %</th><th>Time</th><th>GF</th><th>GA</th><th>GD</th>'
        '<th>Time to Next GF</th><th>Time to Next GA</th><th>GD/60</th>'
        '<th>Time to Next GF</th><th>Time to Next GA</th><th>GD/60</th>'
        '<th>GF Time</th><th>GA Time</th><th>GD/60</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></div>'
    )


def goal_table_html(frame: pd.DataFrame) -> str:
    headers = ["Date", "Game", "Scorer", "Period", "Time Left", "Score Before", "Type", "Carryover"]
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in headers:
            value = row[column]
            classes = "primary" if column == "Scorer" else "numeric" if column == "Period" else ""
            cells.append(f'<td class="{classes}">{html.escape(str(value))}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    head = "".join(f"<th>{html.escape(column)}</th>" for column in headers)
    return (
        '<div class="nhl-table-shell"><div class="nhl-table-scroll">'
        f'<table class="nhl-table"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        '</div></div>'
    )


def render_goals_split(goals_for: pd.DataFrame, goals_allowed: pd.DataFrame) -> None:
    for_html = goal_table_html(goals_for) if not goals_for.empty else '<div class="nhl-table-shell" style="padding:24px">No goals scored.</div>'
    allowed_html = goal_table_html(goals_allowed) if not goals_allowed.empty else '<div class="nhl-table-shell" style="padding:24px">No goals allowed.</div>'
    st.html(
        '<div class="goals-split">'
        f'<section class="goal-panel for"><div class="goal-panel-title">For <small>{len(goals_for)} goals</small></div>{for_html}</section>'
        f'<section class="goal-panel allowed"><div class="goal-panel-title">Allowed <small>{len(goals_allowed)} goals</small></div>{allowed_html}</section>'
        '</div>'
    )


def render_flow_summary(cards: list[dict[str, str]]) -> None:
    content = "".join(
        f'<div class="flow-summary-card"><div class="flow-summary-label">{html.escape(card["label"])}</div>'
        f'<div class="flow-summary-value">{html.escape(card["value"])}</div>'
        f'<div class="flow-summary-detail">{html.escape(card["detail"])}</div></div>'
        for card in cards
    )
    st.html(f'<div class="flow-summary-grid">{content}</div>')


def flow_panel_html(
    title: str,
    subtitle: str,
    frame: pd.DataFrame,
    kind: str,
    *,
    total_count: int | None = None,
    display_limit: int | None = None,
) -> str:
    count = len(frame) if total_count is None else total_count
    count_label = f"{count} results" if kind == "final" else f"{count} goals"
    display_frame = frame if display_limit is None else frame.head(display_limit)
    if frame.empty:
        body = '<div class="nhl-table-shell" style="padding:24px">No matching state exits.</div>'
    else:
        body = table_html(
            display_frame,
            primary="Game",
            height=None,
            formats={},
            table_class="nhl-table flow-table",
        )
    return (
        f'<section class="flow-panel {kind}"><div class="flow-panel-title">'
        f'<div><strong>{html.escape(title)}</strong><span>{html.escape(subtitle)}</span></div>'
        f'<span>{html.escape(count_label)}</span></div>{body}</section>'
    )


def render_flow_panels(
    for_frame: pd.DataFrame,
    final_frame: pd.DataFrame,
    against_frame: pd.DataFrame,
    *,
    selected_team: str,
) -> None:
    display_limit = 100 if selected_team == "All" else None
    st.html(
        '<div class="flow-panels">'
        + flow_panel_html("Goal For", "Diff improves by one", for_frame, "for", display_limit=display_limit)
        + flow_panel_html("No More Goals", "State runs to final", final_frame, "final", display_limit=display_limit)
        + flow_panel_html("Goal Against", "Diff worsens by one", against_frame, "against", display_limit=display_limit)
        + '</div>'
    )


def table_html(
    frame: pd.DataFrame,
    *,
    height: int | None = 480,
    formats: dict[str, object] | None = None,
    primary: str | None = None,
    pill: str | None = None,
    table_class: str = "nhl-table",
) -> str:
    if frame.empty:
        return '<div class="nhl-table-shell" style="padding:24px">No rows match the current filters.</div>'
    formats = formats or {}
    headers = []
    for column in frame.columns:
        numeric = pd.api.types.is_numeric_dtype(frame[column]) and not pd.api.types.is_bool_dtype(frame[column])
        headers.append(f'<th class="{"numeric" if numeric else ""}">{html.escape(str(column))}</th>')
    rows = []
    for _, record in frame.iterrows():
        cells = []
        for column in frame.columns:
            value = record[column]
            formatter = formats.get(column)
            if pd.isna(value):
                shown = "—"
            elif callable(formatter):
                shown = str(formatter(value))
            elif isinstance(formatter, str):
                shown = format(value, formatter)
            elif isinstance(value, float):
                shown = f"{value:,.2f}"
            else:
                shown = str(value)
            classes = []
            if pd.api.types.is_numeric_dtype(frame[column]) and not pd.api.types.is_bool_dtype(frame[column]):
                classes.append("numeric")
            if column == primary:
                classes.append("primary")
            content = html.escape(shown)
            if column == pill:
                pill_class = "pill-for" if shown == "FOR" else "pill-allowed" if shown == "AGAINST" else "pill-neutral"
                content = f'<span class="table-pill {pill_class}">{content}</span>'
            cells.append(f'<td class="{" ".join(classes)}">{content}</td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')
    scroll_style = "" if height is None else f' style="max-height:{height}px"'
    return (
        f'<div class="nhl-table-shell"><div class="nhl-table-scroll"{scroll_style}>'
        f'<table class="{table_class}"><thead><tr>{"".join(headers)}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        f'</div></div>'
    )


def data_footnote(include_moneypuck: bool = False) -> None:
    st.divider()
    sources = (
        "Official schedules, scores, play-by-play, and shift charts: "
        "[NHL Web and Stats APIs](https://api-web.nhle.com/)."
    )
    if include_moneypuck:
        sources += (
            " Expected-goal estimates: [MoneyPuck](https://www.moneypuck.com/data.htm); "
            "used from its published season download and credited per its data terms."
        )
    st.caption(f"Data sources — {sources}")


def perspective_shots(shots: pd.DataFrame) -> pd.DataFrame:
    if shots.empty:
        return pd.DataFrame()
    shooting = pd.DataFrame(
        {
            "game_id": shots["game_id"], "game_date": shots["game_date"],
            "team": shots["event_team"],
            "opponent": np.where(shots["event_team"].eq(shots["home_team"]), shots["away_team"], shots["home_team"]),
            "state": shots["state"], "score_diff": shots["event_team_diff_before"],
            "team_goalie": shots["for_goalie"], "opponent_goalie": shots["against_goalie"],
            "xgf": shots["xg"], "xga": 0.0, "agf": shots["is_goal"], "aga": 0,
            "attempts_for": 1, "attempts_against": 0,
        }
    )
    defending = pd.DataFrame(
        {
            "game_id": shots["game_id"], "game_date": shots["game_date"],
            "team": shooting["opponent"], "opponent": shots["event_team"],
            "state": shots["state"].map(invert_state), "score_diff": -shots["event_team_diff_before"],
            "team_goalie": shots["against_goalie"], "opponent_goalie": shots["for_goalie"],
            "xgf": 0.0, "xga": shots["xg"], "agf": 0, "aga": shots["is_goal"],
            "attempts_for": 0, "attempts_against": 1,
        }
    )
    out = pd.concat([shooting, defending], ignore_index=True)
    out["score_bucket"] = diff_bucket(out["score_diff"])
    return out


def flow_state_label(value: int) -> str:
    if value <= -3:
        return "Down 3+"
    if value < 0:
        return f"Down {abs(value)}"
    if value == 0:
        return "Tied"
    if value >= 3:
        return "Up 3+"
    return f"Up {value}"


def build_score_flow_entries(
    games_frame: pd.DataFrame,
    plays_frame: pd.DataFrame,
    selected_team: str,
) -> pd.DataFrame:
    if games_frame.empty or plays_frame.empty:
        return pd.DataFrame()
    rows = []
    games_by_id = games_frame.drop_duplicates("game_id").set_index("game_id")
    goal_plays = plays_frame[plays_frame["event_type"].eq("goal")].copy()
    if "period_type" in goal_plays:
        goal_plays = goal_plays[~goal_plays["period_type"].eq("SO")].copy()
    goal_groups = {
        game_id: group.sort_values(["elapsed_seconds", "sort_order"])
        for game_id, group in goal_plays.groupby("game_id", sort=False)
    }
    shootout_games = set(plays_frame.loc[plays_frame["event_type"].eq("shootout-complete"), "game_id"])
    game_end = (
        plays_frame[plays_frame["event_type"].eq("game-end")]
        .groupby("game_id", as_index=True)["elapsed_seconds"]
        .max()
    )
    max_elapsed = plays_frame.groupby("game_id", as_index=True)["elapsed_seconds"].max()
    for game_id, game in games_by_id.iterrows():
        if selected_team != "All" and selected_team not in {game["home_team"], game["away_team"]}:
            continue
        perspective_teams = [game["home_team"], game["away_team"]] if selected_team == "All" else [selected_team]
        game_goals = goal_groups.get(game_id, goal_plays.iloc[0:0])
        end_second = int(game_end.get(game_id, max(3600, max_elapsed.get(game_id, 3600))))
        end_second = max(3600, end_second)
        for perspective_team in perspective_teams:
            is_home = perspective_team == game["home_team"]
            opponent = game["away_team"] if is_home else game["home_team"]
            score_for = 0
            score_against = 0
            state_start = 0
            state_diff = 0
            state_score = "0-0"
            for goal in game_goals.itertuples(index=False):
                goal_second = int(goal.elapsed_seconds)
                scored_for = goal.scoring_team == perspective_team
                duration = max(0, goal_second - state_start)
                rows.append({
                    "team": perspective_team,
                    "opponent": opponent,
                    "game_id": game_id,
                    "game_date": game["game_date"],
                    "game_type": game["game_type"],
                    "home_team": game["home_team"],
                    "away_team": game["away_team"],
                    "home_score": game["home_score"],
                    "away_score": game["away_score"],
                    "period": goal.period,
                    "event_second": goal_second,
                    "event_clock": goal.time_in_period,
                    "scorer": goal.actor_name or "Unknown",
                    "entry_second": state_start,
                    "entry_goals_for": score_for,
                    "entry_goals_against": score_against,
                    "entry_score": state_score,
                    "entry_diff": state_diff,
                    "state": flow_state_label(state_diff),
                    "duration_seconds": duration,
                    "outcome": "FOR" if scored_for else "AGAINST",
                    "score_for_after": score_for + (1 if scored_for else 0),
                    "score_against_after": score_against + (0 if scored_for else 1),
                })
                if scored_for:
                    score_for += 1
                else:
                    score_against += 1
                state_diff = score_for - score_against
                state_score = f"{score_for}-{score_against}"
                state_start = goal_second
            duration = max(0, end_second - state_start)
            official_score_for = game["home_score"] if is_home else game["away_score"]
            official_score_against = game["away_score"] if is_home else game["home_score"]
            shootout_result = ""
            if game_id in shootout_games:
                shootout_result = "Won shootout" if official_score_for > official_score_against else "Lost shootout"
            rows.append({
                "team": perspective_team,
                "opponent": opponent,
                "game_id": game_id,
                "game_date": game["game_date"],
                "game_type": game["game_type"],
                "home_team": game["home_team"],
                "away_team": game["away_team"],
                "home_score": game["home_score"],
                "away_score": game["away_score"],
                "period": np.nan,
                "event_second": end_second,
                "event_clock": "Final",
                "scorer": "Final",
                "entry_second": state_start,
                "entry_goals_for": score_for,
                "entry_goals_against": score_against,
                "entry_score": state_score,
                "entry_diff": state_diff,
                "state": flow_state_label(state_diff),
                "duration_seconds": duration,
                "outcome": "FINAL",
                "shootout_result": shootout_result,
                "score_for_after": score_for,
                "score_against_after": score_against,
            })
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    team_home = frame["team"].eq(frame["home_team"])
    team_score = np.where(team_home, frame["home_score"], frame["away_score"])
    opponent_score = np.where(team_home, frame["away_score"], frame["home_score"])
    max_period_by_game = (
        plays_frame.groupby("game_id", as_index=False)["period"].max().rename(columns={"period": "max_period"})
    )
    frame = frame.merge(max_period_by_game, on="game_id", how="left")
    frame["win"] = team_score > opponent_score
    frame["otl"] = (team_score < opponent_score) & frame["game_type"].eq(2) & frame["max_period"].gt(3)
    frame["loss"] = (team_score < opponent_score) & ~frame["otl"]
    return frame


@st.cache_data(show_spinner=False)
def cached_score_flow_entries(
    season_value: int,
    game_type_values: tuple[int, ...],
    start_value: str,
    end_value: str,
    selected_team: str,
) -> pd.DataFrame:
    all_games = read_kind("games", season_value)
    all_plays = read_kind("plays", season_value)
    if all_games.empty or all_plays.empty:
        return pd.DataFrame()
    all_games = all_games.copy()
    all_games["game_date"] = pd.to_datetime(all_games["game_date"])
    scoped_games = all_games[
        all_games["game_date"].between(pd.Timestamp(start_value), pd.Timestamp(end_value))
        & all_games["game_type"].isin(list(game_type_values))
        & all_games["game_state"].isin(["OFF", "FINAL"])
    ].copy()
    scoped_plays = all_plays[all_plays["game_id"].isin(scoped_games["game_id"])].copy()
    return build_score_flow_entries(scoped_games, scoped_plays, selected_team)


def flow_record_text(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "0-0-0"
    games_once = frame.drop_duplicates(["team", "game_id"])
    wins = int(games_once["win"].sum())
    losses = int(games_once["loss"].sum())
    otl = int(games_once["otl"].sum())
    return f"{wins}-{losses}-{otl}"


def points_pct_from_flow(frame: pd.DataFrame) -> float:
    if frame.empty:
        return np.nan
    games_once = frame.drop_duplicates(["team", "game_id"])
    games_count = len(games_once)
    if games_count == 0:
        return np.nan
    return (2 * games_once["win"].sum() + games_once["otl"].sum()) / (2 * games_count)


def score_flow_league_context(league_frame: pd.DataFrame, selected_team: str) -> dict[str, object]:
    if league_frame.empty:
        return {
            "avg_entries": np.nan,
            "avg_time": np.nan,
            "avg_points_pct": np.nan,
            "entry_rank": np.nan,
            "time_rank": np.nan,
            "points_rank": np.nan,
        }
    team_summary = league_frame.groupby("team", as_index=False).agg(
        entries=("game_id", "size"),
        avg_time=("duration_seconds", "mean"),
    )
    game_summary = (
        league_frame.drop_duplicates(["team", "game_id"])
        .groupby("team", as_index=False)
        .agg(games=("game_id", "size"), wins=("win", "sum"), overtime_losses=("otl", "sum"))
    )
    team_summary = team_summary.merge(game_summary, on="team", how="left")
    team_summary["points"] = 2 * team_summary["wins"] + team_summary["overtime_losses"]
    team_summary["points_pct"] = np.where(
        team_summary["games"].gt(0),
        team_summary["points"] / (2 * team_summary["games"]),
        np.nan,
    )
    team_summary["entry_rank"] = team_summary["entries"].rank(method="min", ascending=False)
    team_summary["time_rank"] = team_summary["avg_time"].rank(method="min", ascending=False)
    team_summary["points_rank"] = team_summary["points"].rank(method="min", ascending=False)
    selected = team_summary[team_summary["team"].eq(selected_team)]
    selected_row = selected.iloc[0] if selected_team != "All" and not selected.empty else pd.Series(dtype=object)
    return {
        "avg_entries": team_summary["entries"].mean(),
        "avg_time": team_summary["avg_time"].mean(),
        "avg_points": team_summary["points"].mean(),
        "avg_points_pct": team_summary["points_pct"].mean(),
        "entry_rank": selected_row.get("entry_rank", np.nan),
        "time_rank": selected_row.get("time_rank", np.nan),
        "points_rank": selected_row.get("points_rank", np.nan),
    }


def rank_or_league(value: object) -> str:
    return "League" if pd.isna(value) else f"#{int(value)} / {rank_team_total}"


def flow_display_table(frame: pd.DataFrame, selected_team: str, outcome: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    out = frame.copy().sort_values(["game_date", "event_second"], ascending=[False, True])
    out["Date"] = pd.to_datetime(out["game_date"]).dt.strftime("%b %d")
    out["Team"] = out["team"].map(lambda value: TEAM_NAMES.get(value, value))
    out["Game"] = [
        game_label(team_code, home, away)
        for team_code, home, away in zip(out["team"], out["home_team"], out["away_team"])
    ]
    out["Score"] = out["entry_score"]
    out["Start"] = [
        elapsed_start_clock(entry_second, game_type)
        for entry_second, game_type in zip(out["entry_second"], out["game_type"])
    ]
    out["Time at Diff"] = out["duration_seconds"].map(seconds_clock)
    out["Period"] = out["period"].map(lambda value: "Final" if pd.isna(value) else "OT" if int(value) > 3 else str(int(value)))
    out["Time Left"] = [
        "Final" if outcome == "FINAL" else countdown_clock(int(period), clock, int(game_type))
        for period, clock, game_type in zip(out["period"].fillna(3), out["event_clock"], out["game_type"])
    ]
    if outcome == "FINAL":
        out["Note"] = out["shootout_result"].fillna("").replace("", "Final")
        columns = ["Date", "Game", "Score", "Start", "Time at Diff", "Note"]
    else:
        columns = ["Date", "Game", "Score", "Start", "Time at Diff", "Scorer", "Period", "Time Left"]
        out["Scorer"] = out["scorer"].fillna("Unknown")
    if selected_team == "All":
        columns = ["Team", *columns]
    return out[columns]


with tab1:
    st.subheader("Lineup Balance")
    st.caption("One view of how quickly the selected lineup creates and concedes goals, benchmarked against the same league-wide context.")
    if not lineup_types:
        st.info("Select at least one lineup type in the sidebar.")
    elif manpower_all.empty or moneypuck_all.empty:
        st.info("Lineup exposure or expected-goal data is unavailable for this selection.")
    else:
        exposure_all = manpower_all[
            manpower_all["state"].isin(lineup_types)
            & manpower_all["score_bucket"].isin(goal_differences)
        ].copy()
        exposure_all = exposure_all.rename(columns={"for_goalie": "team_goalie", "against_goalie": "opponent_goalie"})
        exposure_all = apply_goalie_filter(exposure_all)

        shot_view = perspective_shots(moneypuck_all)
        shot_view = shot_view[
            shot_view["state"].isin(lineup_types)
            & shot_view["score_bucket"].isin(goal_differences)
        ]
        shot_view = apply_goalie_filter(shot_view)

        league_goals = plays[
            plays["game_date"].between(start_date, end_date)
            & plays["game_type"].isin(game_types)
            & plays["period"].isin(periods)
            & (plays["elapsed_seconds"] / 60).between(*minute_range)
            & plays["event_type"].eq("goal")
        ].copy()
        scoring_home = league_goals["scoring_team"].eq(league_goals["home_team"])
        scoring_team = league_goals["scoring_team"]
        allowed_team = np.where(scoring_home, league_goals["away_team"], league_goals["home_team"])
        scoring_goalie = np.where(scoring_home, league_goals["home_goalie"], league_goals["away_goalie"]).astype(bool)
        allowed_goalie = np.where(scoring_home, league_goals["away_goalie"], league_goals["home_goalie"]).astype(bool)
        league_goals["credited_state"] = league_goals["official_state"]
        league_carry = (
            league_goals["seconds_since_state_change"].le(carryover)
            & league_goals["prior_state"].notna()
            & league_goals["prior_state"].ne(league_goals["official_state"])
        )
        league_goals.loc[league_carry, "credited_state"] = league_goals.loc[league_carry, "prior_state"]
        goals_for_view = pd.DataFrame({
            "team": scoring_team,
            "credited_state": league_goals["credited_state"],
            "score_bucket": diff_bucket(league_goals["event_team_diff_before"]),
            "team_goalie": scoring_goalie,
            "opponent_goalie": allowed_goalie,
            "raw_goals": 1,
            "raw_goals_allowed": 0,
        })
        goals_allowed_view = pd.DataFrame({
            "team": allowed_team,
            "credited_state": league_goals["credited_state"].map(invert_state),
            "score_bucket": diff_bucket(-league_goals["event_team_diff_before"]),
            "team_goalie": allowed_goalie,
            "opponent_goalie": scoring_goalie,
            "raw_goals": 0,
            "raw_goals_allowed": 1,
        })
        goal_view = pd.concat([goals_for_view, goals_allowed_view], ignore_index=True)
        goal_view = goal_view[
            goal_view["credited_state"].isin(lineup_types)
            & goal_view["score_bucket"].isin(goal_differences)
        ]
        goal_view = apply_goalie_filter(goal_view)
        raw_goals_by_team = goal_view.groupby("team", as_index=False)[["raw_goals", "raw_goals_allowed"]].sum()

        minutes_by_team = exposure_all.groupby("team", as_index=False)["seconds"].sum()
        outcomes_by_team = shot_view.groupby("team", as_index=False)[["xgf", "xga", "agf", "aga"]].sum()
        league = minutes_by_team.merge(outcomes_by_team, on="team", how="left").fillna(0)
        league["minutes"] = league["seconds"] / 60
        league["xgf_minutes"] = np.where(league["xgf"].gt(0), league["minutes"] / league["xgf"], np.inf)
        league["agf_minutes"] = np.where(league["agf"].gt(0), league["minutes"] / league["agf"], np.inf)
        league["xga_minutes"] = np.where(league["xga"].gt(0), league["minutes"] / league["xga"], np.inf)
        league["aga_minutes"] = np.where(league["aga"].gt(0), league["minutes"] / league["aga"], np.inf)
        league["xgd60"] = (league["xgf"] - league["xga"]) * 60 / league["minutes"]
        league["agd60"] = (league["agf"] - league["aga"]) * 60 / league["minutes"]
        league["gf_minutes_diff"] = league["agf_minutes"] - league["xgf_minutes"]
        league["ga_minutes_diff"] = league["aga_minutes"] - league["xga_minutes"]
        league["gd60_diff"] = league["agd60"] - league["xgd60"]
        league["rank_xgf"] = league["xgf_minutes"].rank(method="min", ascending=True)
        league["rank_agf"] = league["agf_minutes"].rank(method="min", ascending=True)
        league["rank_xga"] = league["xga_minutes"].rank(method="min", ascending=False)
        league["rank_aga"] = league["aga_minutes"].rank(method="min", ascending=False)
        league["rank_xgd"] = league["xgd60"].rank(method="min", ascending=False)
        league["rank_agd"] = league["agd60"].rank(method="min", ascending=False)
        league["rank_gf_diff"] = league["gf_minutes_diff"].rank(method="min", ascending=True)
        league["rank_ga_diff"] = league["ga_minutes_diff"].rank(method="min", ascending=False)
        league["rank_gd_diff"] = league["gd60_diff"].rank(method="min", ascending=False)

        max_period_by_game = plays.groupby("game_id", as_index=False)["period"].max().rename(columns={"period": "max_period"})
        context_games = exposure_all.groupby(["team", "game_id"], as_index=False)["seconds"].sum()
        context_games = context_games.merge(
            games[["game_id", "game_type", "home_team", "away_team", "home_score", "away_score"]],
            on="game_id", how="left",
        ).merge(max_period_by_game, on="game_id", how="left")
        context_home = context_games["team"].eq(context_games["home_team"])
        context_games["score_for"] = np.where(context_home, context_games["home_score"], context_games["away_score"])
        context_games["score_against"] = np.where(context_home, context_games["away_score"], context_games["home_score"])
        context_games["win"] = context_games["score_for"].gt(context_games["score_against"]).astype(int)
        context_games["otl"] = (
            context_games["score_for"].lt(context_games["score_against"])
            & context_games["game_type"].eq(2)
            & context_games["max_period"].gt(3)
        ).astype(int)
        context_games["loss"] = (
            context_games["score_for"].lt(context_games["score_against"]).astype(int) - context_games["otl"]
        )
        context_league = context_games.groupby("team", as_index=False).agg(
            games_played=("game_id", "nunique"), wins=("win", "sum"), losses=("loss", "sum"),
            overtime_losses=("otl", "sum"), seconds=("seconds", "sum"),
        )
        context_league = context_league.merge(raw_goals_by_team, on="team", how="left")
        context_league["raw_goals"] = context_league["raw_goals"].fillna(0).astype(int)
        context_league["points_pct"] = (
            (2 * context_league["wins"] + context_league["overtime_losses"])
            / (2 * context_league["games_played"])
        )
        context_league["minutes"] = context_league["seconds"] / 60
        context_league["minutes_per_game"] = context_league["minutes"] / context_league["games_played"]
        context_league["rank_points"] = context_league["points_pct"].rank(method="min", ascending=False)
        context_league["rank_games_played"] = context_league["games_played"].rank(method="min", ascending=False)
        context_league["rank_minutes"] = context_league["minutes"].rank(method="min", ascending=False)
        context_league["rank_raw_goals"] = context_league["raw_goals"].rank(method="min", ascending=False)

        total_minutes = league["minutes"].sum()
        league_values = {
            "xgf_minutes": total_minutes / league["xgf"].sum() if league["xgf"].sum() else np.inf,
            "agf_minutes": total_minutes / league["agf"].sum() if league["agf"].sum() else np.inf,
            "xga_minutes": total_minutes / league["xga"].sum() if league["xga"].sum() else np.inf,
            "aga_minutes": total_minutes / league["aga"].sum() if league["aga"].sum() else np.inf,
            "xgd60": (league["xgf"].sum() - league["xga"].sum()) * 60 / total_minutes if total_minutes else np.nan,
            "agd60": (league["agf"].sum() - league["aga"].sum()) * 60 / total_minutes if total_minutes else np.nan,
        }
        league_values["gf_minutes_diff"] = league_values["agf_minutes"] - league_values["xgf_minutes"]
        league_values["ga_minutes_diff"] = league_values["aga_minutes"] - league_values["xga_minutes"]
        league_values["gd60_diff"] = league_values["agd60"] - league_values["xgd60"]

        selected = league if team == "All" else league[league["team"].eq(team)]
        if selected.empty or total_minutes == 0 or (team != "All" and selected["minutes"].iloc[0] == 0):
            st.warning("No tracked minutes match these filters.")
        else:
            if team == "All":
                row = pd.Series({
                    **league_values,
                    "minutes": total_minutes,
                    **{column: np.nan for column in league.columns if column.startswith("rank_")},
                })
                selected_exposure = exposure_all
                context_row = pd.Series({
                    "games_played": context_league["games_played"].sum(),
                    "wins": context_league["wins"].sum(),
                    "losses": context_league["losses"].sum(),
                    "overtime_losses": context_league["overtime_losses"].sum(),
                    "points_pct": (
                        (2 * context_league["wins"].sum() + context_league["overtime_losses"].sum())
                        / (2 * context_league["games_played"].sum())
                    ),
                    "minutes": context_league["minutes"].sum(),
                    "raw_goals": context_league["raw_goals"].sum(),
                })
            else:
                row = selected.iloc[0]
                selected_exposure = exposure_all[exposure_all["team"].eq(team)]
                context_row = context_league[context_league["team"].eq(team)].iloc[0]
            games_played = int(context_row["games_played"])
            wins = int(context_row["wins"])
            losses = int(context_row["losses"])
            overtime_losses = int(context_row["overtime_losses"])
            points_pct = context_row["points_pct"]
            selected_minutes = context_row["minutes"]
            raw_goals = int(context_row["raw_goals"])
            context_ranks = (
                {
                    "games": "League", "points": "League",
                    "minutes": "League", "goals": "League",
                }
                if team == "All"
                else {
                    "games": f"#{int(context_row['rank_games_played'])} / {rank_team_total}",
                    "points": f"#{int(context_row['rank_points'])} / {rank_team_total}",
                    "minutes": f"#{int(context_row['rank_minutes'])} / {rank_team_total}",
                    "goals": f"#{int(context_row['rank_raw_goals'])} / {rank_team_total}",
                }
            )
            render_context_cards(
                [
                    {"label": "Record in Selected Games", "value": f"{games_played} GP; {wins}–{losses}–{overtime_losses}", "detail": "League total of team-games in this state" if team == "All" else "Ranked by games containing this state", "rank": context_ranks["games"]},
                    {"label": "Points Percentage", "value": "—" if not np.isfinite(points_pct) else f"{points_pct:.2%}", "detail": "(2 × W + OTL) ÷ (2 × GP)", "rank": context_ranks["points"]},
                    {"label": "Time Played", "value": seconds_clock(selected_minutes * 60), "detail": "Total time in the selected state", "rank": context_ranks["minutes"]},
                    {"label": "Goals Scored", "value": str(raw_goals), "detail": "League total in this state" if team == "All" else "Matches the For goal table below", "rank": context_ranks["goals"]},
                ]
            )
            actual_specs = [
                ("Time to Next Goal Scored", "agf_minutes", "rank_agf", "clock"),
                ("Time to Next Goal Allowed", "aga_minutes", "rank_aga", "clock"),
                ("Goal Difference per 60", "agd60", "rank_agd", "+.2f"),
            ]
            expected_specs = [
                ("Time to Next Goal Scored", "xgf_minutes", "rank_xgf", "clock"),
                ("Time to Next Goal Allowed", "xga_minutes", "rank_xga", "clock"),
                ("Goal Difference per 60", "xgd60", "rank_xgd", "+.2f"),
            ]
            difference_specs = [
                ("Time to Next Goal Scored", "gf_minutes_diff", "rank_gf_diff", "signed_clock"),
                ("Time to Next Goal Allowed", "ga_minutes_diff", "rank_ga_diff", "signed_clock"),
                ("Goal Difference per 60", "gd60_diff", "rank_gd_diff", "+.2f"),
            ]

            def cards_from_specs(specs: list[tuple[str, str, str, str]]) -> list[dict[str, object]]:
                cards = []
                for label, key, rank_key, fmt in specs:
                    value = row[key]
                    league_value = league_values[key]
                    if fmt == "clock":
                        shown = "—" if not np.isfinite(value) else seconds_clock(value * 60)
                        league_shown = "—" if not np.isfinite(league_value) else seconds_clock(league_value * 60)
                    elif fmt == "signed_clock":
                        shown = "—" if not np.isfinite(value) else signed_seconds_clock(value * 60)
                        league_shown = "—" if not np.isfinite(league_value) else signed_seconds_clock(league_value * 60)
                    else:
                        shown = "—" if not np.isfinite(value) else format(value, fmt)
                        league_shown = "—" if not np.isfinite(league_value) else format(league_value, fmt)
                    cards.append(
                        {
                            "label": label,
                            "value": shown,
                            "league": league_shown,
                            "rank": row[rank_key],
                        }
                    )
                return cards

            actual_cards = cards_from_specs(actual_specs)
            expected_cards = cards_from_specs(expected_specs)
            difference_cards = cards_from_specs(difference_specs)
            render_metric_cards(actual_cards, expected_cards, difference_cards)

            st.caption(f"{seconds_clock(row['minutes'] * 60)} tracked time · Lineups: {', '.join(lineup_types)} · Carryover affects the goal log below; xG tiles use the strict on-ice state.")

            if team == "All":
                st.info("Select a team to see the game-by-game schedule and individual goal logs. League-wide summary metrics remain shown above.")
            st.markdown("### Game-by-Game Time in State")
            detail_exposure = selected_exposure if team != "All" else selected_exposure.iloc[0:0]
            schedule = detail_exposure.groupby(["game_id", "game_date", "opponent"], as_index=False)["seconds"].sum()
            selected_shots = shot_view[shot_view["team"].eq(team)]
            game_outcomes = selected_shots.groupby("game_id", as_index=False)[["xgf", "xga", "agf", "aga"]].sum()
            schedule = schedule.merge(game_outcomes, on="game_id", how="left").fillna({"xgf": 0, "xga": 0, "agf": 0, "aga": 0})
            game_meta = games[["game_id", "game_type", "home_team", "away_team", "home_score", "away_score"]]
            schedule = schedule.merge(game_meta, on="game_id", how="left").merge(max_period_by_game, on="game_id", how="left")
            schedule["Date"] = pd.to_datetime(schedule["game_date"]).dt.strftime("%b %d")
            schedule["Game"] = [game_label(team, home, away) for home, away in zip(schedule["home_team"], schedule["away_team"])]
            team_home_schedule = schedule["home_team"].eq(team)
            team_score = np.where(team_home_schedule, schedule["home_score"], schedule["away_score"])
            opponent_score = np.where(team_home_schedule, schedule["away_score"], schedule["home_score"])
            high_score = np.maximum(team_score, opponent_score).astype(int)
            low_score = np.minimum(team_score, opponent_score).astype(int)
            overtime_loss = (team_score < opponent_score) & schedule["game_type"].eq(2) & schedule["max_period"].gt(3)
            result_letter = np.where(team_score > opponent_score, "W", np.where(overtime_loss, "OTL", "L"))
            schedule["Result"] = [f"{letter}, {high}–{low}" for letter, high, low in zip(result_letter, high_score, low_score)]
            schedule["Time in State"] = schedule["seconds"].map(seconds_clock)
            schedule["Actual GF"] = schedule["agf"]
            schedule["Actual GA"] = schedule["aga"]
            schedule["Actual GD"] = schedule["agf"] - schedule["aga"]
            schedule["Expected GF"] = schedule["xgf"]
            schedule["Expected GA"] = schedule["xga"]
            schedule["Expected GD"] = schedule["xgf"] - schedule["xga"]
            schedule["Difference GF"] = schedule["agf"] - schedule["xgf"]
            schedule["Difference GA"] = schedule["aga"] - schedule["xga"]
            schedule["Difference GD"] = schedule["Actual GD"] - schedule["Expected GD"]
            schedule = schedule.sort_values("game_date", ascending=False)
            render_game_state_table(
                schedule[["Date", "Game", "Result", "Time in State", "Actual GF", "Actual GA", "Actual GD", "Expected GF", "Expected GA", "Expected GD", "Difference GF", "Difference GA", "Difference GD"]]
            )

            st.markdown("### Goals in the Selected State")
            detail_plays = team_plays if team != "All" else team_plays.iloc[0:0]
            goals = detail_plays[detail_plays["event_type"].eq("goal")].copy()
            if goals.empty:
                st.info("Select a team to see individual goals." if team == "All" else "No goals match this selection.")
            else:
                team_home = goals["home_team"].eq(team)
                goals["state"] = [f"{int(a)}v{int(b)}" for a, b in zip(np.where(team_home, goals["home_skaters"], goals["away_skaters"]), np.where(team_home, goals["away_skaters"], goals["home_skaters"]))]
                goals["team_goalie"] = np.where(team_home, goals["home_goalie"], goals["away_goalie"]).astype(bool)
                goals["opponent_goalie"] = np.where(team_home, goals["away_goalie"], goals["home_goalie"]).astype(bool)
                goals["score_diff"] = np.where(team_home, goals["home_diff_before"], -goals["home_diff_before"])
                goals["score_bucket"] = diff_bucket(goals["score_diff"])
                goals["Outcome"] = np.where(goals["scoring_team"].eq(team), "FOR", "ALLOWED")
                goals["prior_team_state"] = np.where(goals["scoring_team"].eq(team), goals["prior_state"], goals["prior_state"].map(invert_state))
                carry_mask = goals["seconds_since_state_change"].le(carryover) & goals["prior_team_state"].notna() & goals["prior_team_state"].ne(goals["state"])
                goals["credited_state"] = goals["state"]
                goals.loc[carry_mask, "credited_state"] = goals.loc[carry_mask, "prior_team_state"]
                goals["carryover_seconds"] = np.where(carry_mask, goals["seconds_since_state_change"], np.nan)
                goals = goals[goals["credited_state"].isin(lineup_types) & goals["score_bucket"].isin(goal_differences)]
                goals = apply_goalie_filter(goals)
                team_home = goals["home_team"].eq(team)
                goals["Date"] = pd.to_datetime(goals["game_date"]).dt.strftime("%b %d")
                goals["Game"] = [game_label(team, home, away) for home, away in zip(goals["home_team"], goals["away_team"])]
                goals["Time Left"] = [
                    countdown_clock(period, clock, game_type_value)
                    for period, clock, game_type_value in zip(goals["period"], goals["time_in_period"], goals["game_type"])
                ]
                team_score_before = np.where(team_home, goals["home_score_before"], goals["away_score_before"]).astype(int)
                opponent_score_before = np.where(team_home, goals["away_score_before"], goals["home_score_before"]).astype(int)
                score_status = np.where(team_score_before > opponent_score_before, "Leading", np.where(team_score_before < opponent_score_before, "Trailing", "Tied"))
                high_before = np.maximum(team_score_before, opponent_score_before)
                low_before = np.minimum(team_score_before, opponent_score_before)
                goals["Score Before"] = [f"{status}, {high}–{low}" for status, high, low in zip(score_status, high_before, low_before)]
                goals["Carryover"] = ["—" if pd.isna(value) else f"{int(value)} sec" for value in goals["carryover_seconds"]]
                goals = goals.rename(columns={"period": "Period", "actor_name": "Scorer", "credited_state": "Type"}).sort_values(["game_date", "elapsed_seconds"], ascending=[False, True])
                goals["Scorer"] = goals["Scorer"].fillna("Unknown")
                goal_columns = ["Date", "Game", "Scorer", "Period", "Time Left", "Score Before", "Type", "Carryover"]
                goals_for = goals[goals["Outcome"].eq("FOR")][goal_columns]
                goals_allowed = goals[goals["Outcome"].eq("ALLOWED")][goal_columns]
                render_goals_split(goals_for, goals_allowed)
    data_footnote(include_moneypuck=True)

with tab2:
    st.subheader("League Lineup Balance")
    st.caption("All teams under the current state filters. Rank is by Actual GD/60.")
    if not lineup_types:
        st.info("Select at least one lineup type in the sidebar.")
    elif manpower_all.empty or moneypuck_all.empty:
        st.info("Lineup exposure or expected-goal data is unavailable for this selection.")
    else:
        exposure_all = manpower_all[
            manpower_all["state"].isin(lineup_types)
            & manpower_all["score_bucket"].isin(goal_differences)
        ].copy()
        exposure_all = exposure_all.rename(columns={"for_goalie": "team_goalie", "against_goalie": "opponent_goalie"})
        exposure_all = apply_goalie_filter(exposure_all)

        shot_view = perspective_shots(moneypuck_all)
        shot_view = shot_view[
            shot_view["state"].isin(lineup_types)
            & shot_view["score_bucket"].isin(goal_differences)
        ]
        shot_view = apply_goalie_filter(shot_view)

        league_goals = plays[
            plays["game_date"].between(start_date, end_date)
            & plays["game_type"].isin(game_types)
            & plays["period"].isin(periods)
            & (plays["elapsed_seconds"] / 60).between(*minute_range)
            & plays["event_type"].eq("goal")
        ].copy()
        scoring_home = league_goals["scoring_team"].eq(league_goals["home_team"])
        scoring_team = league_goals["scoring_team"]
        allowed_team = np.where(scoring_home, league_goals["away_team"], league_goals["home_team"])
        scoring_goalie = np.where(scoring_home, league_goals["home_goalie"], league_goals["away_goalie"]).astype(bool)
        allowed_goalie = np.where(scoring_home, league_goals["away_goalie"], league_goals["home_goalie"]).astype(bool)
        league_goals["credited_state"] = league_goals["official_state"]
        league_carry = (
            league_goals["seconds_since_state_change"].le(carryover)
            & league_goals["prior_state"].notna()
            & league_goals["prior_state"].ne(league_goals["official_state"])
        )
        league_goals.loc[league_carry, "credited_state"] = league_goals.loc[league_carry, "prior_state"]
        goals_for_view = pd.DataFrame({
            "team": scoring_team,
            "credited_state": league_goals["credited_state"],
            "score_bucket": diff_bucket(league_goals["event_team_diff_before"]),
            "team_goalie": scoring_goalie,
            "opponent_goalie": allowed_goalie,
            "raw_goals": 1,
            "raw_goals_allowed": 0,
        })
        goals_allowed_view = pd.DataFrame({
            "team": allowed_team,
            "credited_state": league_goals["credited_state"].map(invert_state),
            "score_bucket": diff_bucket(-league_goals["event_team_diff_before"]),
            "team_goalie": allowed_goalie,
            "opponent_goalie": scoring_goalie,
            "raw_goals": 0,
            "raw_goals_allowed": 1,
        })
        goal_view = pd.concat([goals_for_view, goals_allowed_view], ignore_index=True)
        goal_view = goal_view[
            goal_view["credited_state"].isin(lineup_types)
            & goal_view["score_bucket"].isin(goal_differences)
        ]
        goal_view = apply_goalie_filter(goal_view)
        raw_goals_by_team = goal_view.groupby("team", as_index=False)[["raw_goals", "raw_goals_allowed"]].sum()

        teams = pd.DataFrame({"team": rank_teams})
        minutes_by_team = exposure_all.groupby("team", as_index=False)["seconds"].sum()
        outcomes_by_team = shot_view.groupby("team", as_index=False)[["xgf", "xga", "agf", "aga"]].sum()
        league = (
            teams.merge(minutes_by_team, on="team", how="left")
            .merge(outcomes_by_team, on="team", how="left")
            .fillna({"seconds": 0, "xgf": 0, "xga": 0, "agf": 0, "aga": 0})
        )
        league["minutes"] = league["seconds"] / 60
        league["xgf_minutes"] = np.where(league["xgf"].gt(0), league["minutes"] / league["xgf"], np.inf)
        league["agf_minutes"] = np.where(league["agf"].gt(0), league["minutes"] / league["agf"], np.inf)
        league["xga_minutes"] = np.where(league["xga"].gt(0), league["minutes"] / league["xga"], np.inf)
        league["aga_minutes"] = np.where(league["aga"].gt(0), league["minutes"] / league["aga"], np.inf)
        league["xgd60"] = np.where(league["minutes"].gt(0), (league["xgf"] - league["xga"]) * 60 / league["minutes"], np.nan)
        league["agd60"] = np.where(league["minutes"].gt(0), (league["agf"] - league["aga"]) * 60 / league["minutes"], np.nan)
        league["gf_minutes_diff"] = league["agf_minutes"] - league["xgf_minutes"]
        league["ga_minutes_diff"] = league["aga_minutes"] - league["xga_minutes"]
        league["gd60_diff"] = league["agd60"] - league["xgd60"]
        league["rank_agd"] = league["agd60"].rank(method="min", ascending=False)

        max_period_by_game = plays.groupby("game_id", as_index=False)["period"].max().rename(columns={"period": "max_period"})
        context_games = exposure_all.groupby(["team", "game_id"], as_index=False)["seconds"].sum()
        context_games = context_games.merge(
            games[["game_id", "game_type", "home_team", "away_team", "home_score", "away_score"]],
            on="game_id", how="left",
        ).merge(max_period_by_game, on="game_id", how="left")
        if context_games.empty:
            context_league = teams.assign(
                games_played=0, wins=0, losses=0, overtime_losses=0, context_seconds=0,
                raw_goals=0, raw_goals_allowed=0,
            )
        else:
            context_home = context_games["team"].eq(context_games["home_team"])
            context_games["score_for"] = np.where(context_home, context_games["home_score"], context_games["away_score"])
            context_games["score_against"] = np.where(context_home, context_games["away_score"], context_games["home_score"])
            context_games["win"] = context_games["score_for"].gt(context_games["score_against"]).astype(int)
            context_games["otl"] = (
                context_games["score_for"].lt(context_games["score_against"])
                & context_games["game_type"].eq(2)
                & context_games["max_period"].gt(3)
            ).astype(int)
            context_games["loss"] = (
                context_games["score_for"].lt(context_games["score_against"]).astype(int) - context_games["otl"]
            )
            context_league = context_games.groupby("team", as_index=False).agg(
                games_played=("game_id", "nunique"), wins=("win", "sum"), losses=("loss", "sum"),
                overtime_losses=("otl", "sum"), context_seconds=("seconds", "sum"),
            )
            context_league = teams.merge(context_league, on="team", how="left").fillna(0)
        context_league = context_league.drop(
            columns=[column for column in ["raw_goals", "raw_goals_allowed"] if column in context_league]
        )
        context_league = context_league.merge(raw_goals_by_team, on="team", how="left")
        for column in ["raw_goals", "raw_goals_allowed"]:
            if column not in context_league:
                context_league[column] = 0
        context_league["raw_goals"] = context_league["raw_goals"].fillna(0)
        context_league["raw_goals_allowed"] = context_league["raw_goals_allowed"].fillna(0)
        for column in ["games_played", "wins", "losses", "overtime_losses", "context_seconds", "raw_goals", "raw_goals_allowed"]:
            context_league[column] = context_league[column].fillna(0)
        context_league["points_pct"] = np.where(
            context_league["games_played"].gt(0),
            (2 * context_league["wins"] + context_league["overtime_losses"]) / (2 * context_league["games_played"]),
            np.nan,
        )

        table = league.merge(
            context_league[["team", "games_played", "wins", "losses", "overtime_losses", "points_pct", "raw_goals", "raw_goals_allowed"]],
            on="team", how="left",
        )
        table["raw_goal_difference"] = table["raw_goals"] - table["raw_goals_allowed"]
        table = table.sort_values(["rank_agd", "team"], na_position="last")

        total_minutes = table["minutes"].sum()
        league_values = {
            "team": "League Average",
            "rank_agd": np.nan,
            "games_played": table["games_played"].mean(),
            "wins": table["wins"].mean(),
            "losses": table["losses"].mean(),
            "overtime_losses": table["overtime_losses"].mean(),
            "points_pct": table["points_pct"].mean(),
            "minutes": table["minutes"].mean(),
            "raw_goals": table["raw_goals"].mean(),
            "raw_goals_allowed": table["raw_goals_allowed"].mean(),
            "raw_goal_difference": table["raw_goal_difference"].mean(),
            "agf_minutes": total_minutes / table["agf"].sum() if table["agf"].sum() else np.inf,
            "aga_minutes": total_minutes / table["aga"].sum() if table["aga"].sum() else np.inf,
            "agd60": (table["agf"].sum() - table["aga"].sum()) * 60 / total_minutes if total_minutes else np.nan,
            "xgf_minutes": total_minutes / table["xgf"].sum() if table["xgf"].sum() else np.inf,
            "xga_minutes": total_minutes / table["xga"].sum() if table["xga"].sum() else np.inf,
            "xgd60": (table["xgf"].sum() - table["xga"].sum()) * 60 / total_minutes if total_minutes else np.nan,
        }
        league_values["gf_minutes_diff"] = league_values["agf_minutes"] - league_values["xgf_minutes"]
        league_values["ga_minutes_diff"] = league_values["aga_minutes"] - league_values["xga_minutes"]
        league_values["gd60_diff"] = league_values["agd60"] - league_values["xgd60"]
        table = pd.concat([table, pd.DataFrame([league_values])], ignore_index=True)

        def clock_minutes(value: float) -> str:
            return "—" if not np.isfinite(value) else seconds_clock(value * 60)

        def signed_clock_minutes(value: float) -> str:
            return "—" if not np.isfinite(value) else signed_seconds_clock(value * 60)

        def goal_count(value: float) -> str:
            return "—" if pd.isna(value) else f"{value:.1f}" if value % 1 else f"{int(value)}"

        display = pd.DataFrame({
            "Rank": table["rank_agd"].map(lambda value: "League" if pd.isna(value) else f"#{int(value)} / {rank_team_total}"),
            "Team": table["team"].map(lambda value: "League Average" if value == "League Average" else TEAM_NAMES.get(value, value)),
            "Record": [
                f"{games_played:.1f} GP; {wins:.1f}-{losses:.1f}-{ot_losses:.1f}" if team_name == "League Average" else f"{int(games_played)} GP; {int(wins)}-{int(losses)}-{int(ot_losses)}"
                for team_name, games_played, wins, losses, ot_losses in zip(table["team"], table["games_played"], table["wins"], table["losses"], table["overtime_losses"])
            ],
            "Points Percentage": table["points_pct"].map(lambda value: "—" if pd.isna(value) else f"{value:.2%}"),
            "Time Played": table["minutes"].map(lambda value: seconds_clock(value * 60)),
            "Goals Scored": table["raw_goals"].map(goal_count),
            "Goals Allowed": table["raw_goals_allowed"].map(goal_count),
            "Goals Difference": table["raw_goal_difference"].map(lambda value: "—" if pd.isna(value) else f"{value:+.1f}" if value % 1 else f"{int(value):+d}"),
            "Actual Goal Scored": table["agf_minutes"].map(clock_minutes),
            "Actual Goal Allowed": table["aga_minutes"].map(clock_minutes),
            "Actual GD/60": table["agd60"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}"),
            "Expected Goal Scored": table["xgf_minutes"].map(clock_minutes),
            "Expected Goal Allowed": table["xga_minutes"].map(clock_minutes),
            "Expected GD/60": table["xgd60"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}"),
            "Difference Goal Scored": table["gf_minutes_diff"].map(signed_clock_minutes),
            "Difference Goal Allowed": table["ga_minutes_diff"].map(signed_clock_minutes),
            "Difference GD/60": table["gd60_diff"].map(lambda value: "—" if pd.isna(value) else f"{value:+.2f}"),
        })

        def rank_class(rank_value: float) -> str:
            if pd.isna(rank_value):
                return ""
            rank_number = int(rank_value)
            if rank_number <= rank_team_total / 4:
                return "cell-elite"
            if rank_number <= rank_team_total / 2:
                return "cell-soft-good"
            if rank_number <= rank_team_total * 3 / 4:
                return "cell-soft-low"
            return "cell-low"

        heatmap_columns = {
            "Points Percentage": ("points_pct", False),
            "Time Played": ("minutes", False),
            "Goals Scored": ("raw_goals", False),
            "Goals Allowed": ("raw_goals_allowed", True),
            "Goals Difference": ("raw_goal_difference", False),
            "Actual Goal Scored": ("agf_minutes", True),
            "Actual Goal Allowed": ("aga_minutes", False),
            "Actual GD/60": ("agd60", False),
            "Expected Goal Scored": ("xgf_minutes", True),
            "Expected Goal Allowed": ("xga_minutes", False),
            "Expected GD/60": ("xgd60", False),
            "Difference Goal Scored": ("gf_minutes_diff", True),
            "Difference Goal Allowed": ("ga_minutes_diff", False),
            "Difference GD/60": ("gd60_diff", False),
        }
        team_rows = table["team"].ne("League Average")
        for display_column, (source_column, ascending) in heatmap_columns.items():
            ranks = table.loc[team_rows, source_column].rank(method="min", ascending=ascending, na_option="bottom")
            display[f"__class_{display_column}"] = ""
            display.loc[team_rows, f"__class_{display_column}"] = ranks.map(rank_class).values
        render_league_balance_table(display)
    data_footnote(include_moneypuck=True)

def sankey_html(flow: pd.DataFrame) -> str:
    """Dependency-free two-stage Sankey SVG for score transitions."""
    width, height, left_x, right_x, node_w, pad = 900, 520, 175, 700, 18, 9
    sources = flow.groupby("source")["transitions"].sum().sort_values(ascending=False)
    targets = flow.groupby("target")["transitions"].sum().sort_values(ascending=False)
    if sources.empty or targets.empty:
        return "<p>No transitions.</p>"
    scale = min((height - pad * len(sources)) / sources.sum(), (height - pad * len(targets)) / targets.sum())
    def positions(series):
        result, y = {}, 5.0
        for label, value in series.items():
            h = max(3.0, float(value) * scale)
            result[label] = [y, h, y]
            y += h + pad
        return result
    src_pos, dst_pos = positions(sources), positions(targets)
    links = []
    for row in flow.sort_values("transitions", ascending=False).itertuples(index=False):
        amount = float(row.transitions)
        thick = max(1.5, amount * scale)
        sy = src_pos[row.source][2] + thick / 2
        ty = dst_pos[row.target][2] + thick / 2
        src_pos[row.source][2] += thick
        dst_pos[row.target][2] += thick
        color = "98,215,211" if bool(row.goal_for) else "239,102,112"
        links.append(f'<path d="M {left_x+node_w} {sy:.1f} C 390 {sy:.1f}, 510 {ty:.1f}, {right_x} {ty:.1f}" fill="none" stroke="rgba({color},.46)" stroke-width="{thick:.1f}"><title>{html.escape(str(row.source))} → {html.escape(str(row.target))}: {int(amount)}</title></path>')
    nodes = []
    for label, (y, h, _) in src_pos.items():
        nodes.append(f'<rect x="{left_x}" y="{y:.1f}" width="{node_w}" height="{h:.1f}" rx="3" fill="#62d7d3"/><text x="{left_x-8}" y="{y+h/2+4:.1f}" text-anchor="end">{html.escape(str(label))}</text>')
    for label, (y, h, _) in dst_pos.items():
        nodes.append(f'<rect x="{right_x}" y="{y:.1f}" width="{node_w}" height="{h:.1f}" rx="3" fill="#ffb454"/><text x="{right_x+node_w+8}" y="{y+h/2+4:.1f}">{html.escape(str(label))}</text>')
    return f'<div style="background:#0d1b2c;border:1px solid #20344c;border-radius:12px;padding:8px"><svg viewBox="0 0 {width} {height}" width="100%" height="520" style="font:12px sans-serif;fill:#dce7f3">{"".join(links)}{"".join(nodes)}</svg></div>'


with tab3:
    st.subheader("Score Flow")
    flow_state_options = ["Down 3+", "Down 2", "Down 1", "Tied", "Up 1", "Up 2", "Up 3+"]
    flow_state = st.selectbox("Goal-difference scenario", flow_state_options, index=flow_state_options.index("Tied"))
    cache_start = str(pd.Timestamp(start_date).date())
    cache_end = str(pd.Timestamp(end_date).date())
    flow_entries = cached_score_flow_entries(season, tuple(game_types), cache_start, cache_end, team)
    league_flow_entries = flow_entries if team == "All" else cached_score_flow_entries(season, tuple(game_types), cache_start, cache_end, "All")
    if flow_entries.empty:
        st.info("No games match the current score-flow filters.")
    else:
        raw_state_entries = flow_entries[flow_entries["state"].eq(flow_state)].copy()
        raw_league_state_entries = league_flow_entries[league_flow_entries["state"].eq(flow_state)].copy()
        goal_count_options = ["All", *sorted(raw_state_entries["entry_goals_for"].dropna().astype(int).unique())]
        selected_flow_goals = st.selectbox(
            "Goals scored in scenario",
            goal_count_options,
            format_func=lambda value: "All" if value == "All" else f"{value} goals scored",
            help="Team goals at the start of the selected score-differential state. Example: Up 1 with 2 goals scored is a 2-1 game state.",
        )
        state_entries = raw_state_entries if selected_flow_goals == "All" else raw_state_entries[
            raw_state_entries["entry_goals_for"].eq(int(selected_flow_goals))
        ].copy()
        league_state_entries = raw_league_state_entries if selected_flow_goals == "All" else raw_league_state_entries[
            raw_league_state_entries["entry_goals_for"].eq(int(selected_flow_goals))
        ].copy()
        if state_entries.empty:
            st.info("No entries match this score-flow scenario.")
        else:
            outcome_counts = state_entries["outcome"].value_counts()
            league_counts = league_state_entries["outcome"].value_counts()
            total_entries = len(state_entries)
            league_total = len(league_state_entries)
            avg_time = state_entries["duration_seconds"].mean()
            league_avg_time = league_state_entries["duration_seconds"].mean()
            flow_context = score_flow_league_context(league_state_entries, team)
            record = flow_record_text(state_entries)
            scenario_games = state_entries.drop_duplicates(["team", "game_id"])
            scenario_points = int(2 * scenario_games["win"].sum() + scenario_games["otl"].sum())
            points_pct = points_pct_from_flow(state_entries)
            team_label = "League" if team == "All" else TEAM_NAMES.get(team, team)
            scenario_copy = {
                "Down 3+": "trailing by three or more goals",
                "Down 2": "trailing by two goals",
                "Down 1": "trailing by one goal",
                "Tied": "playing at an even score",
                "Up 1": "leading by one goal",
                "Up 2": "leading by two goals",
                "Up 3+": "leading by three or more goals",
            }[flow_state]
            st.html(
                '<div class="flow-hero">'
                f'<h2>{html.escape(team_label)} Score Flow: {html.escape(flow_state)}</h2>'
                f'<p>This looks at every time {html.escape(team_label)} was {html.escape(scenario_copy)}. '
                f'{html.escape("The goals-scored filter is set to " + ("all scores" if selected_flow_goals == "All" else str(selected_flow_goals) + " team goals"))}. '
                'Each entry measures how long that score differential lasted, then classifies the exit as a goal for, no more goals before final, or a goal against.</p>'
                '</div>'
            )
            for_entries = state_entries[state_entries["outcome"].eq("FOR")]
            final_entries = state_entries[state_entries["outcome"].eq("FINAL")]
            against_entries = state_entries[state_entries["outcome"].eq("AGAINST")]

            def pct_text(count: int, total: int) -> str:
                return "0.0%" if total == 0 else f"{count / total:.1%}"

            def league_pct(outcome: str) -> str:
                return pct_text(int(league_counts.get(outcome, 0)), league_total)

            def pct_or_dash(value: float) -> str:
                return "—" if pd.isna(value) else f"{value:.2%}"

            def seconds_or_dash(value: float) -> str:
                return "—" if pd.isna(value) else seconds_clock(value)

            def number_or_dash(value: float) -> str:
                return "—" if pd.isna(value) else f"{value:,.1f}"

            entry_rank_text = "" if team == "All" else f" · Rank {rank_or_league(flow_context['entry_rank'])}"
            points_rank_text = "" if team == "All" else f" · Rank {rank_or_league(flow_context['points_rank'])}"
            time_rank_text = "" if team == "All" else f" · Rank {rank_or_league(flow_context['time_rank'])}"

            render_flow_summary([
                {
                    "label": "Scenario Entries",
                    "value": f"{total_entries:,}",
                    "detail": f"League total {league_total:,} · Avg/team {number_or_dash(flow_context['avg_entries'])}{entry_rank_text}",
                },
                {
                    "label": "Scenario Points",
                    "value": f"{scenario_points:,} pts",
                    "detail": f"Record {record} · Pts% {pct_or_dash(points_pct)} · League avg/team {number_or_dash(flow_context['avg_points'])} pts / {pct_or_dash(flow_context['avg_points_pct'])}{points_rank_text}",
                },
                {
                    "label": "Average Time in State",
                    "value": seconds_or_dash(avg_time),
                    "detail": f"League avg/entry {seconds_or_dash(league_avg_time)} · Avg/team {seconds_or_dash(flow_context['avg_time'])}{time_rank_text}",
                },
                {
                    "label": "Outcome Split",
                    "value": f"{pct_text(len(for_entries), total_entries)} / {pct_text(len(final_entries), total_entries)} / {pct_text(len(against_entries), total_entries)}",
                    "detail": f"GF / Final / GA · League {league_pct('FOR')} / {league_pct('FINAL')} / {league_pct('AGAINST')}",
                },
            ])

            for_table = flow_display_table(for_entries, team, "FOR")
            final_table = flow_display_table(final_entries, team, "FINAL")
            against_table = flow_display_table(against_entries, team, "AGAINST")
            render_flow_panels(for_table, final_table, against_table, selected_team=team)
            st.caption("Score Flow uses full-game goal sequence within the selected season, competition, and date range. Period and game-minute filters remain for the lineup tabs.")
    data_footnote()

with tab4:
    st.subheader("Coverage and Auditability")
    completed = games[games["game_state"].isin(["OFF", "FINAL"])]
    processed_ids = set(plays["game_id"].unique()) if not plays.empty else set()
    expected_ids = set(completed[completed["game_type"].isin(game_types)]["game_id"])
    missing = sorted(expected_ids - processed_ids)
    c1, c2, c3 = st.columns(3)
    c1.metric("Completed games", f"{len(expected_ids):,}")
    c2.metric("Games with play-by-play", f"{len(expected_ids & processed_ids):,}")
    c3.metric("Missing", f"{len(missing):,}")
    if missing:
        render_table(pd.DataFrame({"Missing game ID": missing}), height=360, primary="Missing game ID")
    else:
        st.success("All completed games in this selection have play-by-play data.")
    st.markdown(
        "Official event strength and reconstructed shift strength are kept separately. "
        "Use the raw JSON cache to audit any game-level discrepancy."
    )
    data_footnote(include_moneypuck=True)
