from __future__ import annotations

import html
from typing import Optional

import pandas as pd
import streamlit as st

from data import LEAGUES, POSITIONS, load_all_rosters as fetch_all_rosters
from data import load_branding_data as fetch_branding_data


LEAGUE_NAME = "NCAA/NFL Crossover"
LEAGUE_LOGO = "https://upload.wikimedia.org/wikipedia/en/c/cf/NCAA_football_icon_logo.svg"
LEAGUE_ROSTER_ORDER = [
    "ACC",
    "B1G",
    "Big 12",
    "SEC",
    "Pac-12",
    "G6",
    "MW",
    "AAC",
    "MAC",
    "C-USA",
    "SBC",
    "F12",
]
ROSTER_STATUS_ORDER = {"Starter": 0, "Bench": 1, "Taxi": 2, "Reserve": 3}
POSITION_LABELS = {
    "QB": "Quarterback",
    "RB": "Running Back",
    "WR": "Wide Receiver",
    "TE": "Tight End",
}
SCHEDULE_STATUS_COLORS = {
    "win": "#166534",
    "loss": "#991b1b",
    "tie": "#4a5a78",
    "pending": "#8a96b0",
}


def clean_text(value: object, fallback: str = "") -> str:
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    if text.lower() in {"", "nan", "none"}:
        return fallback
    return text


def esc(value: object, fallback: str = "") -> str:
    return html.escape(clean_text(value, fallback))


def first_value(frame: pd.DataFrame, column: str, fallback: str = "") -> str:
    if frame.empty or column not in frame.columns:
        return fallback
    values = frame[column].dropna().astype(str).str.strip()
    values = values.loc[~values.str.lower().isin(["", "nan", "none"])]
    return values.iloc[0] if len(values) else fallback


def match_key(value: object) -> str:
    return clean_text(value).casefold()


def inject_css() -> None:
    st.html(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600;700&family=Rajdhani:wght@600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Barlow', sans-serif;
  background-color: #f4f6fa;
  color: #1a2030;
}
.stApp { background: #f4f6fa; }
footer { visibility: hidden; }
.block-container {
  max-width: 1780px !important;
  padding-top: 1.25rem !important;
  padding-left: 2.25rem !important;
  padding-right: 2.25rem !important;
}
.app-masthead {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 24px;
  padding: 36px 0 24px;
  border-bottom: 2px solid #e2e6ef;
  width: 100%;
}
.mast-left {
  display: flex;
  align-items: center;
  gap: 20px;
}
.league-logo {
  width: 112px;
  height: 112px;
  object-fit: contain;
  filter: drop-shadow(0 4px 12px rgba(15,23,42,0.18));
}
.mast-kicker {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 5px;
  text-transform: uppercase;
  color: #c8102e;
}
.mast-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 82px;
  letter-spacing: 4px;
  line-height: 0.95;
  color: #111827;
}
.season-select-wrap {
  min-width: 180px;
}
.season-select-wrap label,
.season-select-wrap div[data-testid="stWidgetLabel"],
.season-select-wrap div[data-testid="stWidgetLabel"] * {
  color: #111827 !important;
  opacity: 1 !important;
}
.mast-chip {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #6b7a99;
  background: #fff;
  border: 1px solid #dde2ed;
  border-radius: 5px;
  padding: 9px 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.stTabs [data-baseweb="tab-list"] {
  background: #f4f6fa;
  border-bottom: 2px solid #e2e6ef;
  gap: 0;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #9aa5be;
  padding: 16px 28px;
}
.stTabs [data-baseweb="tab"]:hover { color: #4a5a78; }
.stTabs [aria-selected="true"] {
  color: #111827 !important;
  border-bottom: 2px solid #c8102e !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding-top: 18px; }
div[data-testid="stWidgetLabel"] p {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #111827 !important;
}
div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] *,
label[data-testid="stWidgetLabel"],
label[data-testid="stWidgetLabel"] * {
  color: #111827 !important;
  opacity: 1 !important;
}
.brand-panel {
  background: #fff;
  border: 1px solid #e2e6ef;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.07);
  padding: 22px 24px;
  margin: 12px 0 18px;
}
.conf-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 22px;
  border-left: 8px solid var(--accent);
}
.conf-title-wrap {
  display: flex;
  align-items: center;
  gap: 18px;
}
.conf-logo {
  width: 84px;
  height: 84px;
  object-fit: contain;
}
.conf-kicker {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 5px;
  text-transform: uppercase;
  color: #9aa5be;
}
.conf-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 58px;
  letter-spacing: 3px;
  line-height: 1;
  color: #111827;
}
.team-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin: 12px 0 22px;
}
.team-tile {
  background: #fff;
  border: 1px solid #e2e6ef;
  border-top: 5px solid var(--team-color);
  border-radius: 8px;
  min-height: 90px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  box-shadow: 0 1px 6px rgba(15,23,42,0.06);
}
.team-tile img {
  max-width: 100%;
  max-height: 54px;
  object-fit: contain;
}
.roster-section {
  margin: 22px 0 30px;
}
.position-label {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}
.position-label span {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 44px;
  letter-spacing: 3px;
  line-height: 1;
  color: #111827;
}
.position-label div {
  flex: 1;
  height: 1px;
  background: #dde2ed;
}
.roster-scroll {
  overflow-x: auto;
  border: 1px solid #e2e6ef;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
}
.roster-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 1180px;
}
.roster-table th {
  min-width: 138px;
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  border-right: 1px solid #e8ecf3;
  padding: 10px 8px;
  vertical-align: bottom;
}
.team-head {
  border-top: 5px solid var(--team-color);
}
.team-head img {
  max-width: 112px;
  max-height: 44px;
  object-fit: contain;
}
.roster-table td {
  border-right: 1px solid #edf0f7;
  border-bottom: 1px solid #edf0f7;
  padding: 7px 10px;
  font-family: 'Barlow', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #1a2030;
  white-space: nowrap;
}
.roster-table tr:nth-child(even) td { background: #fbfcff; }
.team-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  color: #fff;
  background: linear-gradient(135deg, var(--team-color), var(--team-color2));
  border-radius: 10px;
  padding: 26px 30px;
  margin: 12px 0 22px;
  box-shadow: 0 12px 28px rgba(15,23,42,0.16);
}
.team-hero-wordmark {
  max-width: 340px;
  max-height: 96px;
  object-fit: contain;
  filter: drop-shadow(0 5px 12px rgba(0,0,0,0.25));
}
.team-hero-logo {
  width: 118px;
  height: 118px;
  object-fit: contain;
  filter: drop-shadow(0 5px 12px rgba(0,0,0,0.24));
}
.team-hero-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 68px;
  letter-spacing: 3px;
  line-height: 1;
}
.team-hero-sub {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 4px;
  text-transform: uppercase;
  opacity: 0.85;
}
.team-roster-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
.position-card {
  background: #fff;
  border: 1px solid #e2e6ef;
  border-top: 5px solid var(--team-color);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
  overflow: hidden;
}
.position-card-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  letter-spacing: 3px;
  color: #111827;
  padding: 12px 16px 6px;
  border-bottom: 1px solid #edf0f7;
}
.player-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 16px;
  border-bottom: 1px solid #edf0f7;
}
.player-row:nth-child(even) { background: #fbfcff; }
.player-main {
  display: flex;
  align-items: center;
  gap: 10px;
}
.player-name {
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #1a2030;
}
.player-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: #8a96b0;
}
.nfl-chip {
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: #4a5a78;
  background: #eef2f7;
  border-radius: 4px;
  padding: 2px 7px;
}
.injury-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fee2e2;
  color: #991b1b;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 800;
}
.league-matrix {
  min-width: 1120px;
}
.league-matrix .player-col {
  min-width: 230px;
  text-align: left;
}
.league-matrix .taken-col {
  min-width: 66px;
  text-align: center;
}
.taken-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 26px;
  border-radius: 5px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
}
.conf-head img {
  width: 108px;
  height: 68px;
  object-fit: contain;
}
.conf-head-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: #4a5a78;
}
.team-logo-cell {
  text-align: center;
  vertical-align: middle;
}
.team-logo-cell img {
  max-width: 34px;
  max-height: 34px;
  object-fit: contain;
}
.empty-state {
  min-height: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  background: #fff;
  border: 1px solid #e2e6ef;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.07);
  margin-top: 14px;
}
.empty-state img {
  width: 112px;
  height: 112px;
  object-fit: contain;
  margin-bottom: 18px;
}
.empty-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 58px;
  letter-spacing: 3px;
  color: #111827;
}
.empty-sub {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #9aa5be;
}
.schedule-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 10px 0 18px;
}
.schedule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(390px, 1fr));
  gap: 18px;
}
.schedule-card {
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
  overflow: hidden;
}
.schedule-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e6ef;
}
.week-chip {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #4a5a78;
}
.game-badge {
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 1.2px;
  color: #fff;
  background: #1a2030;
  border-radius: 4px;
  padding: 2px 8px;
}
.matchup-row {
  display: grid;
  grid-template-columns: 1fr 76px;
  align-items: center;
  gap: 12px;
  padding: 13px 14px;
  border-bottom: 1px solid #edf0f7;
  border-left: 6px solid var(--team-color);
}
.matchup-row:last-child { border-bottom: none; }
.matchup-row.winner { background: linear-gradient(90deg, rgba(22,101,52,0.08), #fff 45%); }
.matchup-row.loser { opacity: 0.74; }
.matchup-team {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.matchup-team img {
  width: 44px;
  height: 44px;
  object-fit: contain;
  flex-shrink: 0;
}
.matchup-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  color: #1a2030;
  line-height: 1.05;
}
.matchup-conf {
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 700;
  color: #8a96b0;
  margin-top: 2px;
}
.score-box {
  justify-self: end;
  min-width: 58px;
  border-radius: 8px;
  background: #f1f5f9;
  color: #1a2030;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 38px;
  letter-spacing: 1px;
  line-height: 1;
  text-align: center;
  padding: 9px 10px 6px;
}
.score-box.win { background: #dcfce7; color: #166534; }
.score-box.loss { background: #fee2e2; color: #991b1b; }
.score-box.tie { background: #e2e8f0; color: #4a5a78; }
.schedule-notes {
  padding: 10px 14px 12px;
  font-family: 'Barlow', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
  background: #fbfcff;
}
.team-schedule-stack {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}
.schedule-matrix-wrap {
  margin-top: 26px;
}
.schedule-matrix-title {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}
.schedule-matrix-title span {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  letter-spacing: 3px;
  line-height: 1;
  color: #111827;
}
.schedule-matrix-title div {
  flex: 1;
  height: 1px;
  background: #dde2ed;
}
.schedule-matrix-scroll {
  overflow-x: auto;
  border: 1px solid #e2e6ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
}
.schedule-matrix {
  border-collapse: collapse;
  width: 100%;
  min-width: 1180px;
}
.schedule-matrix th {
  background: #f8fafc;
  border-right: 1px solid #e8ecf3;
  border-bottom: 2px solid #e2e6ef;
  padding: 10px 8px;
  text-align: center;
}
.schedule-matrix th:first-child {
  min-width: 92px;
}
.schedule-matrix-team-head img {
  width: 48px;
  height: 48px;
  object-fit: contain;
}
.schedule-week-cell {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: #4a5a78;
  background: #f8fafc;
  border-right: 1px solid #e8ecf3;
  border-bottom: 1px solid #edf0f7;
  padding: 10px 12px;
  white-space: nowrap;
}
.schedule-opponent-cell {
  border-right: 1px solid #edf0f7;
  border-bottom: 1px solid #edf0f7;
  padding: 8px;
  text-align: center;
  min-width: 84px;
  height: 58px;
}
.schedule-opponent-cell.win { background: #dcfce7; }
.schedule-opponent-cell.loss { background: #fee2e2; }
.schedule-opponent-cell.tie { background: #fef9c3; }
.schedule-opponent-cell.pending { background: #ffffff; }
.schedule-opponent-cell img {
  width: 42px;
  height: 42px;
  object-fit: contain;
}
.schedule-bye {
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 800;
  color: #b0baca;
}
</style>
"""
    )


def masthead() -> None:
    left, right = st.columns([1, 0.16], vertical_alignment="center")
    with left:
        st.html(
            f"""
<div class="app-masthead">
  <div class="mast-left">
    <img class="league-logo" src="{LEAGUE_LOGO}" alt="{esc(LEAGUE_NAME)}">
    <div>
      <div class="mast-kicker">Dynasty Command Center</div>
      <div class="mast-title">{esc(LEAGUE_NAME)}</div>
    </div>
  </div>
</div>
"""
        )
    with right:
        st.html('<div class="season-select-wrap">')
        selected_season = st.selectbox(
            "Season",
            [2025],
            index=0,
            key="global_season",
        )
        st.html("</div>")
    return selected_season


def under_construction(label: str) -> None:
    st.html(
        f"""
<div class="empty-state">
  <img src="{LEAGUE_LOGO}" alt="{esc(LEAGUE_NAME)}">
  <div class="empty-sub">{esc(label)}</div>
  <div class="empty-title">Coming Soon</div>
</div>
"""
    )


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Loading team branding...")
def load_branding_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return fetch_branding_data()


@st.cache_data(ttl=60 * 60 * 24, show_spinner="Loading NCAA/NFL Crossover rosters...")
def load_all_rosters() -> pd.DataFrame:
    return fetch_all_rosters()


def team_lookup(schools: pd.DataFrame) -> dict[str, dict[str, str]]:
    lookup = {}
    for _, row in schools.iterrows():
        team = clean_text(row.get("School"))
        if not team:
            continue
        lookup[team] = {
            "logo": clean_text(row.get("Logo")),
            "wordmark": clean_text(row.get("Wordmark")),
            "conference": clean_text(row.get("Conference")),
            "color": clean_text(row.get("Color"), "#1a2030"),
            "color2": clean_text(row.get("Color2"), "#c8102e"),
        }
    return lookup


def score_lookup(scores: pd.DataFrame) -> dict[tuple[str, int], float]:
    lookup = {}
    if scores.empty:
        return lookup
    for _, row in scores.iterrows():
        team = clean_text(row.get("Team"))
        week = row.get("Week")
        points = row.get("Points")
        if not team or pd.isna(week) or pd.isna(points):
            continue
        lookup[(match_key(team), int(week))] = float(points)
    return lookup


def conference_logo(conferences: pd.DataFrame, conference: str) -> str:
    match = conferences.loc[conferences["Conference"].astype(str).eq(str(conference))]
    return first_value(match, "Logo", LEAGUE_LOGO)


def conference_code(conferences: pd.DataFrame, conference: str) -> str:
    match = conferences.loc[conferences["Conference"].astype(str).eq(str(conference))]
    return first_value(match, "Code", conference)


def taken_color(count: int) -> str:
    if count >= 10:
        return "#166534"
    if count >= 7:
        return "#3f8f29"
    if count >= 5:
        return "#d97706"
    if count >= 3:
        return "#dc2626"
    return "#7f1d1d"


def score_class(points: Optional[float], opponent_points: Optional[float]) -> str:
    if points is None or opponent_points is None:
        return "pending"
    if points > opponent_points:
        return "win"
    if points < opponent_points:
        return "loss"
    return "tie"


def render_matchup_team(
    team: str,
    week: int,
    points: Optional[float],
    opponent_points: Optional[float],
    teams: dict[str, dict[str, str]],
) -> str:
    info = teams.get(team, {})
    logo = clean_text(info.get("logo"))
    conference = clean_text(info.get("conference"))
    color = esc(info.get("color"), "#1a2030")
    status = score_class(points, opponent_points)
    score_text = f"{points:.2f}" if points is not None else "-"
    logo_html = f'<img src="{esc(logo)}" alt="{esc(team)}">' if logo else ""

    return f"""
<div class="matchup-row {status if status in ('win', 'loss') else ''}" style="--team-color:{color};">
  <div class="matchup-team">
    {logo_html}
    <div>
      <div class="matchup-name">{esc(team)}</div>
      <div class="matchup-conf">{esc(conference)}</div>
    </div>
  </div>
  <div class="score-box {status if status in ('win', 'loss', 'tie') else ''}">{score_text}</div>
</div>
"""


def render_schedule_cards(
    games: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    empty_label: str = "No games found",
    stacked: bool = False,
) -> None:
    if games.empty:
        st.html(
            f"""
<div class="empty-state">
  <img src="{LEAGUE_LOGO}" alt="{esc(LEAGUE_NAME)}">
  <div class="empty-sub">Schedule</div>
  <div class="empty-title">{esc(empty_label)}</div>
</div>
"""
        )
        return

    teams = team_lookup(schools)
    scores_by_team_week = score_lookup(scores)
    cards = []
    games = games.sort_values(["Week", "TeamA", "TeamB"], na_position="last")

    for _, game in games.iterrows():
        week = int(game["Week"]) if not pd.isna(game.get("Week")) else 0
        team_a = clean_text(game.get("TeamA"))
        team_b = clean_text(game.get("TeamB"))
        notes = clean_text(game.get("Notes"))
        is_conference = bool(game.get("Conference", False))
        score_a = scores_by_team_week.get((match_key(team_a), week))
        score_b = scores_by_team_week.get((match_key(team_b), week))
        badge = "Conference" if is_conference else "Non-Conf"

        cards.append(
            f"""
<div class="schedule-card">
  <div class="schedule-card-top">
    <div class="week-chip">Week {week}</div>
    <div class="game-badge">{badge}</div>
  </div>
  {render_matchup_team(team_a, week, score_a, score_b, teams)}
  {render_matchup_team(team_b, week, score_b, score_a, teams)}
  {f'<div class="schedule-notes">{esc(notes)}</div>' if notes else ''}
</div>
"""
        )

    container_class = "team-schedule-stack" if stacked else "schedule-grid"
    st.html(f'<div class="{container_class}">{"".join(cards)}</div>')


def schedule_weeks(schedule: pd.DataFrame) -> list[int]:
    if schedule.empty or "Week" not in schedule.columns:
        return []
    return sorted(
        int(week)
        for week in schedule["Week"].dropna().unique()
        if int(week) > 0
    )


def week_label(week: int) -> str:
    return f"Week {week}"


def filter_conference_schedule(
    schedule: pd.DataFrame,
    schools: pd.DataFrame,
    conference: str,
) -> pd.DataFrame:
    teams = team_lookup(schools)
    conference_teams = {
        team
        for team, info in teams.items()
        if clean_text(info.get("conference")) == conference
    }
    return schedule.loc[
        schedule["TeamA"].isin(conference_teams)
        | schedule["TeamB"].isin(conference_teams)
    ].copy()


def render_conference_schedule_matrix(
    conference_schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    conference: str,
) -> None:
    teams = team_lookup(schools)
    conference_teams = sorted(
        team
        for team, info in teams.items()
        if clean_text(info.get("conference")) == conference
    )
    weeks = schedule_weeks(conference_schedule)

    if not conference_teams or not weeks:
        return

    scores_by_team_week = score_lookup(scores)
    headers = ['<th class="schedule-week-head">Week</th>']

    for team in conference_teams:
        logo = clean_text(teams.get(team, {}).get("logo"))
        if logo:
            header = f'<img src="{esc(logo)}" alt="{esc(team)}" title="{esc(team)}">'
        else:
            header = f'<span class="conf-head-label">{esc(team)}</span>'
        headers.append(f'<th class="schedule-matrix-team-head">{header}</th>')

    body_rows = []
    for week in weeks:
        week_games = conference_schedule.loc[conference_schedule["Week"].eq(week)]
        cells = [f'<td class="schedule-week-cell">Week {week}</td>']

        for team in conference_teams:
            game = week_games.loc[
                week_games["TeamA"].eq(team) | week_games["TeamB"].eq(team)
            ]

            if game.empty:
                cells.append('<td class="schedule-opponent-cell pending"><span class="schedule-bye">BYE</span></td>')
                continue

            game_row = game.iloc[0]
            team_a = clean_text(game_row.get("TeamA"))
            team_b = clean_text(game_row.get("TeamB"))
            opponent = team_b if team_a == team else team_a
            opponent_logo = clean_text(teams.get(opponent, {}).get("logo"))
            team_score = scores_by_team_week.get((match_key(team), int(week)))
            opponent_score = scores_by_team_week.get((match_key(opponent), int(week)))
            result = score_class(team_score, opponent_score)

            if opponent_logo:
                content = f'<img src="{esc(opponent_logo)}" alt="{esc(opponent)}" title="{esc(opponent)}">'
            else:
                content = f'<span class="conf-head-label">{esc(opponent)}</span>'

            cells.append(f'<td class="schedule-opponent-cell {result}">{content}</td>')

        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    st.html(
        f"""
<div class="schedule-matrix-wrap">
  <div class="schedule-matrix-title"><span>Schedule Grid</span><div></div></div>
  <div class="schedule-matrix-scroll">
    <table class="schedule-matrix">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
    )


def render_roster_matrix(rosters: pd.DataFrame) -> None:
    teams = (
        rosters[
            ["team_name", "team_logo", "team_wordmark", "team_color"]
        ]
        .drop_duplicates("team_name")
        .sort_values("team_name")
        .to_dict("records")
    )

    for position in POSITIONS:
        pos_rosters = rosters.loc[rosters["position"].eq(position)].copy()
        if pos_rosters.empty:
            continue

        team_players: dict[str, list[str]] = {}
        max_players = 0
        for team in teams:
            team_name = clean_text(team.get("team_name"))
            players = (
                pos_rosters.loc[pos_rosters["team_name"].eq(team_name), "player_name"]
                .fillna(pos_rosters.loc[pos_rosters["team_name"].eq(team_name), "player_id"])
                .dropna()
                .astype(str)
                .sort_values()
                .tolist()
            )
            team_players[team_name] = players
            max_players = max(max_players, len(players))

        headers = []
        for team in teams:
            team_name = clean_text(team.get("team_name"))
            logo = clean_text(team.get("team_logo"))
            color = esc(team.get("team_color"), "#1a2030")
            logo_html = f'<img src="{esc(logo)}" alt="{esc(team_name)}">' if logo else ""
            headers.append(
                f"""
<th class="team-head" style="--team-color:{color};">
  {logo_html}
</th>
"""
            )

        body_rows = []
        for idx in range(max_players):
            cells = []
            for team in teams:
                team_name = clean_text(team.get("team_name"))
                player = team_players.get(team_name, [])
                cells.append(f"<td>{esc(player[idx]) if idx < len(player) else ''}</td>")
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        st.html(
            f"""
<div class="roster-section">
  <div class="position-label"><span>{POSITION_LABELS.get(position, position)}</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
        )


def render_league_roster_matrix(rosters: pd.DataFrame, conferences: pd.DataFrame) -> None:
    conference_order = [conference for conference in LEAGUE_ROSTER_ORDER if conference in set(rosters["league_name"])]
    conference_logos = {
        conference: conference_logo(conferences, conference)
        for conference in conference_order
    }

    for position in POSITIONS:
        pos_rosters = rosters.loc[rosters["position"].eq(position)].copy()
        if pos_rosters.empty:
            continue

        rows = []
        for player_id, player_rows in pos_rosters.groupby("player_id"):
            player_name = first_value(player_rows, "player_name", str(player_id))
            row = {
                "player_id": player_id,
                "player_name": player_name,
                "taken_count": player_rows["league_name"].nunique(),
            }
            for conference in conference_order:
                match = player_rows.loc[player_rows["league_name"].eq(conference)]
                row[conference] = first_value(match, "team_logo", "")
                row[f"{conference}_team"] = first_value(match, "team_name", "")
            rows.append(row)

        matrix = pd.DataFrame(rows).sort_values(
            ["taken_count", "player_name"],
            ascending=[False, True],
        )

        headers = ['<th class="player-col">Player</th>']
        for conference in conference_order:
            logo = conference_logos.get(conference, "")
            header_content = (
                f'<img src="{esc(logo)}" alt="{esc(conference)}" title="{esc(conference)}">'
                if logo
                else f'<span class="conf-head-label">{esc(conference)}</span>'
            )
            headers.append(
                f"""
<th class="conf-head">
  {header_content}
</th>
"""
            )
        headers.append('<th class="taken-col">#</th>')

        body_rows = []
        for _, row in matrix.iterrows():
            cells = [f'<td class="player-col">{esc(row["player_name"])}</td>']
            for conference in conference_order:
                logo = clean_text(row.get(conference))
                team = clean_text(row.get(f"{conference}_team"))
                if logo:
                    cells.append(
                        f'<td class="team-logo-cell"><img src="{esc(logo)}" alt="{esc(team)}" title="{esc(team)}"></td>'
                    )
                else:
                    cells.append('<td class="team-logo-cell"></td>')
            taken_count = int(row["taken_count"])
            cells.append(
                f'<td class="taken-col"><span class="taken-pill" style="background:{taken_color(taken_count)};">{taken_count}</span></td>'
            )
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        st.html(
            f"""
<div class="roster-section">
  <div class="position-label"><span>{POSITION_LABELS.get(position, position)}</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table league-matrix">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
        )


def render_team_hero(rosters: pd.DataFrame, team_name: str) -> None:
    team = rosters.loc[rosters["team_name"].eq(team_name)].copy()
    if team.empty:
        st.warning("No roster rows found for this team.")
        return

    color = first_value(team, "team_color", "#1a2030")
    color2 = first_value(team, "team_color2", "#c8102e")
    logo = first_value(team, "team_logo", LEAGUE_LOGO)
    wordmark = first_value(team, "team_wordmark", "")
    conference = first_value(team, "league_name", "")
    hero_image = wordmark or logo

    st.html(
        f"""
<div class="team-hero" style="--team-color:{esc(color)};--team-color2:{esc(color2)};">
  <div>
    <div class="team-hero-sub">{esc(conference)} Roster</div>
    <div class="team-hero-title">{esc(team_name)}</div>
  </div>
  <img class="team-hero-wordmark" src="{esc(hero_image)}" alt="{esc(team_name)}">
  <img class="team-hero-logo" src="{esc(logo)}" alt="{esc(team_name)}">
</div>
"""
    )


def render_team_roster(rosters: pd.DataFrame, team_name: str) -> None:
    team = rosters.loc[rosters["team_name"].eq(team_name)].copy()
    if team.empty:
        st.warning("No roster rows found for this team.")
        return

    color = first_value(team, "team_color", "#1a2030")
    cards = []
    for position in POSITIONS:
        position_team = team.loc[team["position"].eq(position)].copy()
        position_team["status_sort"] = position_team["roster_spot"].map(ROSTER_STATUS_ORDER).fillna(9)
        players = (
            position_team[["player_name", "roster_spot", "nfl_team", "injury_status", "status_sort"]]
            .dropna(subset=["player_name"])
            .sort_values(["status_sort", "player_name"])
            .to_dict("records")
        )
        rows = "".join(
            f"""
<div class="player-row">
  <div class="player-main">
    <div class="player-name">{esc(player["player_name"])}</div>
    {f'<span class="injury-chip">{esc(clean_text(player.get("injury_status"))[:1].upper())}</span>' if clean_text(player.get("injury_status")) else ''}
  </div>
  <div class="player-meta">
    {f'<span class="nfl-chip">{esc(player.get("nfl_team"))}</span>' if clean_text(player.get("nfl_team")) else ''}
    <span>{esc(player["roster_spot"])}</span>
  </div>
</div>
"""
            for player in players
        )
        cards.append(
            f"""
<div class="position-card" style="--team-color:{esc(color)};">
  <div class="position-card-title">{POSITION_LABELS.get(position, position)}</div>
  {rows or '<div class="player-row"><div class="player-name"></div></div>'}
</div>
"""
        )

    st.html(f'<div class="team-roster-grid">{"".join(cards)}</div>')


st.set_page_config(
    page_title=LEAGUE_NAME,
    page_icon=LEAGUE_LOGO,
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
selected_season = masthead()

schools, conferences, schedule, scores = load_branding_data()
all_rosters = load_all_rosters()

league_tab, conference_tab, team_tab = st.tabs(
    ["🏆 League", "🏟️ Conference", "🎓 Team"]
)

with league_tab:
    (
        league_standings_tab,
        league_schedule_tab,
        league_scores_tab,
        league_rankings_tab,
        league_rosters_tab,
        league_rules_tab,
    ) = st.tabs(
        [
            "📊 Standings",
            "📅 Schedule",
            "🏈 Scores",
            "⭐ Rankings",
            "👥 Rosters",
            "📘 Rules",
        ]
    )
    with league_standings_tab:
        under_construction("League Standings")
    with league_schedule_tab:
        weeks = schedule_weeks(schedule)
        if weeks:
            selected_week = st.selectbox(
                "Week",
                weeks,
                key="league_schedule_week",
                format_func=week_label,
            )
            week_games = schedule.loc[schedule["Week"].eq(selected_week)].copy()
            render_schedule_cards(
                week_games,
                scores,
                schools,
                empty_label=f"No Week {selected_week} games",
            )
        else:
            render_schedule_cards(
                schedule,
                scores,
                schools,
                empty_label="No schedule loaded",
            )
    with league_scores_tab:
        under_construction("League Scores")
    with league_rankings_tab:
        under_construction("League Rankings")
    with league_rosters_tab:
        render_league_roster_matrix(all_rosters, conferences)
    with league_rules_tab:
        under_construction("League Rules")

with conference_tab:
    conference_options = [name for name in LEAGUES.keys() if name in set(conferences["Conference"].astype(str))]
    if not conference_options:
        conference_options = list(LEAGUES.keys())

    selected_conference = st.selectbox("Conference", conference_options)
    conference_rosters = all_rosters.loc[
        all_rosters["league_name"].eq(selected_conference)
    ].copy()
    conf_logo = conference_logo(conferences, selected_conference)
    conf_code = conference_code(conferences, selected_conference)

    st.html(
        f"""
<div class="brand-panel conf-hero" style="--accent:#c8102e;">
  <div class="conf-title-wrap">
    <img class="conf-logo" src="{esc(conf_logo)}" alt="{esc(selected_conference)}">
    <div>
      <div class="conf-kicker">{esc(conf_code)} Conference</div>
      <div class="conf-title">{esc(selected_conference)}</div>
    </div>
  </div>
  <img class="league-logo" src="{LEAGUE_LOGO}" alt="{esc(LEAGUE_NAME)}">
</div>
"""
    )
    (
        conf_standings_tab,
        conf_schedule_tab,
        conf_rosters_tab,
        conf_drafts_tab,
    ) = st.tabs(["📊 Standings", "📅 Schedule", "👥 Rosters", "🧾 Drafts"])
    with conf_standings_tab:
        under_construction(f"{selected_conference} Standings")
    with conf_schedule_tab:
        conference_schedule = filter_conference_schedule(
            schedule,
            schools,
            selected_conference,
        )
        weeks = schedule_weeks(conference_schedule)
        if weeks:
            selected_week = st.selectbox(
                "Week",
                weeks,
                key=f"conference_schedule_week_{selected_conference}",
                format_func=week_label,
            )
            week_games = conference_schedule.loc[
                conference_schedule["Week"].eq(selected_week)
            ].copy()
            render_schedule_cards(
                week_games,
                scores,
                schools,
                empty_label=f"No Week {selected_week} {selected_conference} games",
            )
            render_conference_schedule_matrix(
                conference_schedule,
                scores,
                schools,
                selected_conference,
            )
        else:
            render_schedule_cards(
                conference_schedule,
                scores,
                schools,
                empty_label=f"No {selected_conference} games",
            )
            render_conference_schedule_matrix(
                conference_schedule,
                scores,
                schools,
                selected_conference,
            )
    with conf_rosters_tab:
        render_roster_matrix(conference_rosters)
    with conf_drafts_tab:
        under_construction(f"{selected_conference} Drafts")

with team_tab:
    team_options = (
        all_rosters["team_name"]
        .dropna()
        .astype(str)
        .sort_values()
        .drop_duplicates()
        .tolist()
    )
    selected_team = st.selectbox("Team", team_options)
    render_team_hero(all_rosters, selected_team)
    team_schedule_tab, team_roster_tab = st.tabs(["📅 Schedule", "👥 Rosters"])
    with team_schedule_tab:
        team_schedule = schedule.loc[
            schedule["TeamA"].eq(selected_team)
            | schedule["TeamB"].eq(selected_team)
        ].copy()
        render_schedule_cards(
            team_schedule,
            scores,
            schools,
            empty_label=f"No {selected_team} games",
            stacked=True,
        )
    with team_roster_tab:
        render_team_roster(all_rosters, selected_team)
