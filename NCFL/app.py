from __future__ import annotations

import html
import hashlib
import re
import unicodedata
from datetime import datetime
from functools import wraps
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from data import LEAGUES, POSITIONS, load_all_rosters as fetch_all_rosters
from data import get_future_draft_picks as fetch_future_draft_picks
from data import load_branding_data as fetch_branding_data


LEAGUE_NAME = "NCAA/NFL Crossover"
LEAGUE_LOGO = "https://upload.wikimedia.org/wikipedia/en/c/cf/NCAA_football_icon_logo.svg"
SILHOUETTE_PLAYER_HEADSHOT = (
    "data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 200 200%27%3E"
    "%3Crect width=%27200%27 height=%27200%27 fill=%27%23eef2f7%27/%3E"
    "%3Ccircle cx=%27100%27 cy=%2772%27 r=%2742%27 fill=%27%2305070b%27/%3E"
    "%3Cpath d=%27M30 200c4-55 30-82 70-82s66 27 70 82z%27 fill=%27%2305070b%27/%3E%3C/svg%3E"
)
PLAYER_PICTURE_LOOKUP: dict[str, str] = {}
LEAGUE_ROSTER_ORDER = [
    "Big 12",
    "B1G",
    "SEC",
    "Pac-12",
    "ACC",
    "G6",
    "MW",
    "MAC",
    "C-USA",
    "SBC",
    "AAC",
    "F12",
]
SUPERFLEX_CONFERENCES = {"Big 12", "B1G", "SEC", "Pac-12", "ACC", "G6"}
ACTIVE_CONFERENCE_COUNT_BY_YEAR = {2022: 3, 2023: 4, 2024: 6, 2025: 6, 2026: 12}
DYNASTY_PLAYER_VALUES_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv"
DYNASTY_PICK_VALUES_URL = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-picks.csv"
DYNASTY_PLAYER_ALIASES = {
    "marquisebrown": "hollywoodbrown",
}
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
CACHE_TTL_SECONDS = 60 * 60 * 24
DATA_CACHE_VERSION = "conference-sheet-logos-v1"
STANDINGS_CACHE_VERSION = "ignore-zero-future-games-v1"


def clean_text(value: object, fallback: str = "") -> str:
    if pd.isna(value):
        return fallback
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("\u00a0", " ").replace("\u200b", "").strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in {"", "nan", "none"}:
        return fallback
    return text


def esc(value: object, fallback: str = "") -> str:
    return html.escape(clean_text(value, fallback))


def loading_spinner(message: str):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with st.spinner(message, show_time=True):
                return function(*args, **kwargs)

        return wrapped

    return decorator


def first_value(frame: pd.DataFrame, column: str, fallback: str = "") -> str:
    if frame.empty or column not in frame.columns:
        return fallback
    values = frame[column].dropna().astype(str).str.strip()
    values = values.loc[~values.str.lower().isin(["", "nan", "none"])]
    return values.iloc[0] if len(values) else fallback


def match_key(value: object) -> str:
    return clean_text(value).casefold()


def player_picture_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).casefold())


def player_picture(player: object) -> str:
    return PLAYER_PICTURE_LOOKUP.get(
        player_picture_key(player),
        SILHOUETTE_PLAYER_HEADSHOT,
    )


def player_picture_fallback() -> str:
    return f"this.onerror=null;this.src='{SILHOUETTE_PLAYER_HEADSHOT}';"


def dynasty_player_key(value: object) -> str:
    words = re.findall(r"[a-z0-9]+", clean_text(value).casefold())
    while words and words[-1] in {"jr", "sr", "ii", "iii", "iv", "v"}:
        words.pop()
    key = "".join(words)
    return DYNASTY_PLAYER_ALIASES.get(key, key)


def canonical_team_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_text(value).casefold())


def official_team_resolver(schools: pd.DataFrame) -> dict[str, str]:
    resolver = {
        canonical_team_key(team): team
        for team in schools["School"].dropna().map(clean_text)
        if team
    }
    resolver.update(
        {
            "oregonst": "Oregon State",
            "oregonstate": "Oregon State",
            "fsu": "Florida State",
            "miami": "Miami (FL)",
            "smu": "Southern Methodist",
        }
    )
    return resolver


def official_team_name(value: object, resolver: dict[str, str]) -> str:
    text = clean_text(value)
    return resolver.get(canonical_team_key(text), text)


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
  min-width: 0;
  table-layout: fixed;
}
.roster-table th {
  min-width: 0;
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  border-right: 1px solid #e8ecf3;
  padding: 8px 5px;
  vertical-align: bottom;
}
.team-head {
  border-top: 5px solid var(--team-color);
}
.team-head img {
  max-width: 72px;
  max-height: 38px;
  object-fit: contain;
}
.roster-table td {
  border-right: 1px solid #edf0f7;
  border-bottom: 1px solid #edf0f7;
  padding: 6px 5px;
  font-family: 'Barlow', sans-serif;
  font-size: 12px;
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
.team-hero-record {
  margin-top: 10px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 1px;
  color: rgba(255,255,255,0.92);
}
.team-hero-owner {
  display: inline-flex;
  margin-top: 10px;
  border-radius: 999px;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.28);
  color: #ffffff;
  padding: 5px 11px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.8px;
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
.player-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  flex-shrink: 0;
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
  min-width: 0;
  table-layout: fixed;
}
.league-matrix .player-col {
  min-width: 0;
  width: 170px;
  max-width: 170px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
}
.league-matrix .value-col {
  min-width: 0;
  width: 58px;
  max-width: 58px;
  text-align: center;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 900;
  color: #334155;
}
.league-player {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}
.league-player img {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  flex-shrink: 0;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.league-player span {
  overflow: hidden;
  text-overflow: ellipsis;
}
.league-matrix .taken-col {
  min-width: 0;
  width: 42px;
  text-align: center;
}
.league-matrix th {
  min-width: 0;
  padding: 6px 4px;
}
.league-matrix td {
  padding: 5px 4px;
}
.taken-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 24px;
  border-radius: 5px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
}
.league-matrix .conf-head img {
  width: 58px;
  height: 42px;
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
  max-width: 28px;
  max-height: 28px;
  object-fit: contain;
}
.roster-player-cell {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}
.roster-player-cell img {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  flex-shrink: 0;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.roster-player-cell span {
  overflow: hidden;
  text-overflow: ellipsis;
}
.team-roster-board {
  display: grid;
  grid-template-columns: repeat(var(--roster-card-count), minmax(0, 1fr));
  gap: 16px;
  align-items: start;
}
.team-roster-status {
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-top: 7px solid var(--team-color);
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
  overflow: hidden;
}
.team-roster-status-title {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  background: #05070b;
  color: #ffffff;
  padding: 12px 14px 8px;
}
.team-roster-status-title span:first-child {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 34px;
  letter-spacing: 2px;
  line-height: 1;
}
.team-roster-status-title span:last-child {
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 900;
  color: #b0baca;
}
.team-roster-player {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid #edf0f7;
}
.team-roster-player:nth-child(even) {
  background: #fbfcff;
}
.team-roster-player img {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
}
.team-roster-player img.draft-pick-roster-logo {
  border-radius: 0;
  object-fit: contain;
  object-position: center;
  border: 0;
  background: transparent;
}
.team-roster-player-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 21px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #111827;
  line-height: 1.05;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.team-roster-player-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 4px;
}
.position-chip {
  display: inline-flex;
  border-radius: 999px;
  padding: 2px 8px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 900;
  color: #111827;
  background: #eef2f7;
}
.team-roster-empty {
  padding: 18px 14px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 800;
  color: #9aa5be;
  text-align: center;
}
.draft-capital {
  margin-top: 24px;
}
.draft-capital-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.draft-pick-card {
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-top: 5px solid var(--team-color);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
  padding: 11px 12px;
}
.draft-pick-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.draft-pick-year {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 31px;
  letter-spacing: 1.5px;
  color: #111827;
  line-height: 1;
}
.draft-pick-round {
  border-radius: 999px;
  background: #05070b;
  color: #ffffff;
  padding: 3px 8px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 900;
  text-transform: uppercase;
}
.draft-pick-origin {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  min-width: 0;
}
.draft-pick-origin img {
  width: 36px;
  height: 36px;
  object-fit: contain;
  flex-shrink: 0;
}
.draft-pick-origin-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  color: #4a5a78;
  line-height: 1.05;
}
.roster-snapshot-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-left: 7px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
  padding: 10px 14px;
  margin: 4px 0 16px;
}
.roster-snapshot-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1.4px;
  text-transform: uppercase;
  color: #111827;
}
.roster-snapshot-pill {
  border-radius: 999px;
  background: var(--accent);
  color: #ffffff;
  padding: 4px 10px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 900;
  text-transform: uppercase;
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
  margin-bottom: 8px;
}
.schedule-card.bowl-game {
  border: 1px solid #d7b65d;
  border-top: 5px solid #d4a72c;
  box-shadow: 0 7px 24px rgba(111, 78, 10, 0.20);
}
.schedule-card.rivalry-game:not(.bowl-game) {
  border: 1px solid #c7d2fe;
  border-top: 5px solid #4f46e5;
  box-shadow: 0 7px 24px rgba(79, 70, 229, 0.16);
}
.schedule-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e6ef;
}
.schedule-card.bowl-game .schedule-card-top {
  background: #111827;
  border-bottom-color: #2b3445;
}
.schedule-card.bowl-game .week-chip {
  color: #f8e7aa;
}
.schedule-card.bowl-game .game-badge {
  color: #17120a;
  background: #f2cf68;
}
.schedule-card.rivalry-game:not(.bowl-game) .schedule-card-top {
  background: #111827;
  border-bottom-color: #2b3445;
}
.schedule-card.rivalry-game:not(.bowl-game) .week-chip {
  color: #c7d2fe;
}
.schedule-card.rivalry-game:not(.bowl-game) .game-badge {
  background: #c7d2fe;
  color: #111827;
}
.bowl-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 13px;
  min-height: 78px;
  padding: 10px 14px;
  color: #ffffff;
  background: #05070b;
  border-bottom: 1px solid #303849;
  text-align: left;
}
.bowl-banner img {
  width: 72px;
  height: 58px;
  padding: 4px;
  object-fit: contain;
  border-radius: 6px;
  background: #ffffff;
}
.bowl-kicker {
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #f2cf68;
}
.bowl-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 25px;
  font-weight: 800;
  line-height: 1.05;
  letter-spacing: 0;
  text-transform: uppercase;
}
.rivalry-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 68px;
  padding: 12px 16px;
  overflow: hidden;
  color: #ffffff;
  background:
    radial-gradient(circle at top left, rgba(242,207,104,0.30), transparent 34%),
    linear-gradient(135deg, #111827, #312e81 55%, #4c1d95);
  border-bottom: 1px solid rgba(255,255,255,0.18);
  text-align: center;
}
.rivalry-banner::before,
.rivalry-banner::after {
  content: "";
  position: absolute;
  width: 82px;
  height: 2px;
  background: #f2cf68;
  opacity: 0.75;
}
.rivalry-banner::before { left: 18px; }
.rivalry-banner::after { right: 18px; }
.rivalry-kicker {
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #f2cf68;
}
.rivalry-name {
  margin-top: 2px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 25px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}
.rivalry-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  border-radius: 999px;
  padding: 3px 10px 4px;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #312e81;
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1.1px;
  text-transform: uppercase;
  white-space: nowrap;
}
.schedule-rivalry-note {
  padding: 8px 14px;
  background: #fff7ed;
  border-bottom: 1px solid #fed7aa;
  text-align: center;
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
.schedule-card-divider {
  height: 1px;
  background: #dde2ed;
  margin: 2px 0 18px;
}
div[data-testid="stDialog"] {
  width: 95vw !important;
  max-width: 95vw !important;
}
div[data-testid="stDialog"] > div {
  width: 95vw !important;
  max-width: 95vw !important;
}
div[data-testid="stButton"] button {
  background: #05070b !important;
  color: #ffffff !important;
  border: 1px solid #05070b !important;
  border-radius: 4px !important;
  font-family: 'Barlow Condensed', sans-serif !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  letter-spacing: 1.8px !important;
  text-transform: uppercase !important;
}
.boxscore-matchup-card {
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-radius: 14px;
  box-shadow: 0 8px 30px rgba(15,23,42,0.13);
  overflow: hidden;
  margin-bottom: 18px;
}
.boxscore-bowl-masthead {
  position: relative;
  display: grid;
  grid-template-columns: 132px minmax(0, 1fr) 132px;
  align-items: center;
  min-height: 142px;
  margin: 2px 0 18px;
  padding: 18px 28px;
  overflow: hidden;
  color: #ffffff;
  background: #05070b;
  border: 1px solid #d7b65d;
  border-top: 7px solid #f2cf68;
  border-bottom: 7px solid #f2cf68;
  border-radius: 12px;
  box-shadow: 0 9px 32px rgba(111, 78, 10, 0.28);
}
.boxscore-bowl-logo {
  width: 116px;
  height: 94px;
  padding: 8px;
  object-fit: contain;
  justify-self: center;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 4px 18px rgba(0,0,0,0.28);
}
.boxscore-bowl-copy {
  min-width: 0;
  text-align: center;
}
.boxscore-bowl-kicker {
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #f2cf68;
}
.boxscore-bowl-title {
  margin-top: 3px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 58px;
  line-height: 0.95;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #ffffff;
}
.boxscore-bowl-meta {
  margin-top: 8px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #cbd5e1;
}
.boxscore-rivalry-masthead {
  margin: 2px 0 18px;
  padding: 18px 22px;
  color: #ffffff;
  background:
    radial-gradient(circle at 12% 18%, rgba(242,207,104,0.28), transparent 28%),
    linear-gradient(135deg, #111827, #312e81 55%, #4c1d95);
  border: 1px solid #c7d2fe;
  border-top: 6px solid #4f46e5;
  border-radius: 12px;
  box-shadow: 0 9px 32px rgba(79, 70, 229, 0.23);
  text-align: center;
}
.boxscore-rivalry-masthead.compact {
  margin-top: -8px;
  padding: 9px 16px;
  background: #111827;
  border-top-width: 0;
  box-shadow: 0 4px 14px rgba(15,23,42,0.18);
}
.boxscore-rivalry-kicker {
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #f2cf68;
}
.boxscore-rivalry-title {
  margin-top: 3px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  line-height: 1;
  letter-spacing: 2px;
  text-transform: uppercase;
}
.boxscore-rivalry-masthead.compact .boxscore-rivalry-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 20px;
  letter-spacing: 1.4px;
}
.boxscore-matchup-top {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 170px minmax(0, 1fr);
  align-items: stretch;
}
.boxscore-team-panel {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  align-items: center;
  gap: 18px;
  padding: 22px 24px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--team-color) 16%, white), #ffffff 70%);
  border-top: 8px solid var(--team-color);
}
.boxscore-team-panel.right {
  grid-template-columns: minmax(0, 1fr) 104px;
  text-align: right;
  background: linear-gradient(270deg, color-mix(in srgb, var(--team-color) 16%, white), #ffffff 70%);
}
.boxscore-team-panel img {
  width: 104px;
  height: 104px;
  object-fit: contain;
}
.boxscore-rank {
  font-family: 'Rajdhani', sans-serif;
  font-size: 15px;
  font-weight: 800;
  color: #ffffff;
  background: #05070b;
  border-radius: 4px;
  padding: 3px 8px;
  display: inline-block;
  margin-bottom: 6px;
}
.boxscore-team-name {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 56px;
  letter-spacing: 3px;
  line-height: 0.95;
  color: #111827;
}
.boxscore-team-sub {
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 800;
  color: #8a96b0;
}
.boxscore-record {
  display: inline-flex;
  margin-top: 8px;
  border-radius: 999px;
  background: #eef2f7;
  color: #4a5a78;
  padding: 4px 10px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 900;
}
.boxscore-center {
  background: #05070b;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 18px 12px;
}
.boxscore-week-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #b0baca;
}
.boxscore-week-number {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 62px;
  letter-spacing: 4px;
  line-height: 0.95;
}
.boxscore-vs {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 32px;
  letter-spacing: 4px;
  color: #8a96b0;
  line-height: 1;
  margin-top: 5px;
}
.boxscore-score-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 170px minmax(0, 1fr);
  align-items: center;
  border-top: 1px solid #e2e6ef;
}
.boxscore-score-cell {
  padding: 12px 24px 16px;
  background: #fbfcff;
}
.boxscore-score-cell.right {
  text-align: right;
}
.boxscore-score-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #8a96b0;
}
.boxscore-score-value {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 82px;
  letter-spacing: 3px;
  line-height: 0.95;
  color: #111827;
}
.boxscore-score-mid {
  height: 100%;
  background: #f8fafc;
  border-left: 1px solid #e2e6ef;
  border-right: 1px solid #e2e6ef;
}
.win-prob {
  position: relative;
  height: 46px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--left-color) 0%, var(--left-color) var(--left-pct), var(--right-color) var(--left-pct), var(--right-color) 100%);
  box-shadow: inset 0 0 0 2px rgba(255,255,255,0.75), 0 2px 12px rgba(15,23,42,0.12);
  margin: 6px 0 22px;
}
.win-prob-marker {
  position: absolute;
  top: 50%;
  left: var(--left-pct);
  transform: translate(-50%, -50%);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #ffffff;
  border: 4px solid #05070b;
  box-shadow: 0 2px 10px rgba(15,23,42,0.25);
}
.win-prob-label {
  position: absolute;
  top: 50%;
  left: var(--label-pct);
  transform: translate(-50%, -50%);
  background: #05070b;
  color: #ffffff;
  border-radius: 5px;
  padding: 5px 9px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 800;
  white-space: nowrap;
}
.boxscore-section-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 40px;
  letter-spacing: 2px;
  color: #ffffff;
  background: #05070b;
  border-radius: 8px;
  padding: 8px 14px 5px;
  margin: 12px 0 8px;
}
.boxscore-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
}
.boxscore-table th:nth-child(1),
.boxscore-table td:nth-child(1),
.boxscore-table th:nth-child(5),
.boxscore-table td:nth-child(5) {
  width: 33%;
}
.boxscore-table th:nth-child(2),
.boxscore-table td:nth-child(2),
.boxscore-table th:nth-child(4),
.boxscore-table td:nth-child(4) {
  width: 11%;
}
.boxscore-table th:nth-child(3),
.boxscore-table td:nth-child(3) {
  width: 12%;
  text-align: center;
}
.boxscore-table th {
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  padding: 10px 12px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #8a96b0;
}
.boxscore-table td {
  border-bottom: 1px solid #edf0f7;
  padding: 9px 12px;
  vertical-align: middle;
}
.boxscore-player-left,
.boxscore-player-right {
  font-family: 'Barlow Condensed', sans-serif;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #111827;
}
.boxscore-player-right {
  text-align: right;
}
.boxscore-player-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.boxscore-player-right .boxscore-player-wrap {
  justify-content: flex-end;
}
.boxscore-headshot {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  border: 2px solid #e2e8f0;
  background: #f8fafc;
  flex-shrink: 0;
}
.boxscore-player-name {
  font-size: 20px;
  line-height: 1.05;
}
.boxscore-stat-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.boxscore-player-right .boxscore-stat-row {
  justify-content: flex-end;
}
.boxscore-stat-pill {
  display: inline-flex;
  border-radius: 999px;
  background: #eef2f7;
  color: #4a5a78;
  padding: 2px 6px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 800;
  text-transform: none;
  letter-spacing: 0;
}
.boxscore-points {
  font-family: 'Rajdhani', sans-serif;
  font-size: 22px;
  font-weight: 800;
  color: #111827;
  text-align: center;
}
.boxscore-proj {
  display: inline-flex;
  margin-top: 3px;
  border-radius: 999px;
  background: #eef2f7;
  color: #64748b;
  padding: 1px 7px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 900;
}
.boxscore-slot {
  text-align: center;
}
.slot-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 54px;
  border-radius: 999px;
  padding: 4px 10px;
  color: #111827;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 900;
}
.boxscore-total td {
  background: #05070b !important;
  color: #ffffff !important;
  border-bottom: none;
}
.boxscore-total .boxscore-player-left,
.boxscore-total .boxscore-player-right,
.boxscore-total .boxscore-points {
  color: #ffffff !important;
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
.schedule-matrix-rivalry {
  display: block;
  margin-top: 3px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 9px;
  font-weight: 900;
  letter-spacing: 0.9px;
  text-transform: uppercase;
  color: #312e81;
}
.schedule-bye {
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 800;
  color: #b0baca;
}
.standings-wrap {
  margin: 18px 0 30px;
}
.standings-title {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 18px 0 10px;
}
.standings-title img {
  width: 54px;
  height: 54px;
  object-fit: contain;
}
.standings-title span {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 48px;
  letter-spacing: 3px;
  line-height: 1;
  color: #111827;
}
.standings-title div {
  flex: 1;
  height: 1px;
  background: #dde2ed;
}
.standings-scroll {
  overflow-x: auto;
  border: 1px solid #e2e6ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
}
.standings-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 1180px;
  table-layout: fixed;
}
.standings-table col.standings-team-column {
  width: 380px;
}
.standings-table th {
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  border-right: 1px solid #e8ecf3;
  padding: 10px 12px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #8a96b0;
  text-align: right;
  white-space: nowrap;
}
.standings-table th.team-col {
  text-align: left;
  width: 380px;
}
.standings-table td {
  border-bottom: 1px solid #edf0f7;
  border-right: 1px solid #edf0f7;
  padding: 10px 12px;
  text-align: right;
  vertical-align: middle;
}
.standings-table tr:nth-child(even) td { background: #fbfcff; }
.standings-table tr.championship-row td {
  background: #ecfdf5;
  box-shadow: inset 0 1px 0 rgba(22,101,52,0.12), inset 0 -1px 0 rgba(22,101,52,0.12);
}
.standings-team-cell {
  border-left: 6px solid var(--team-color);
  text-align: left !important;
}
.standings-team {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.standings-team > div {
  min-width: 0;
}
.standings-team img {
  width: 42px;
  height: 42px;
  object-fit: contain;
  flex-shrink: 0;
}
.standings-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eef2f7;
  color: #4a5a78;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 800;
}
.standings-team-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #1a2030;
  line-height: 1.05;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.standings-team-sub {
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 700;
  color: #9aa5be;
}
.record-main {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 28px;
  letter-spacing: 1px;
  color: #1a2030;
  line-height: 1;
}
.record-sub {
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 800;
  color: #8a96b0;
  margin-top: 2px;
}
.metric-main {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 28px;
  font-weight: 400;
  letter-spacing: 1px;
  color: #1a2030;
  line-height: 1;
}
.metric-rank {
  margin-top: 2px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 800;
  color: #8a96b0;
}
.rules-hero {
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-left: 8px solid #c8102e;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
  padding: 28px 32px;
  margin: 14px 0 22px;
}
.rules-kicker {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 5px;
  text-transform: uppercase;
  color: #c8102e;
}
.rules-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 68px;
  letter-spacing: 3px;
  line-height: 1;
  color: #111827;
  margin-top: 4px;
}
.rules-sub {
  font-family: 'Barlow', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #64748b;
  max-width: 980px;
  line-height: 1.6;
  margin-top: 8px;
}
.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
  margin: 18px 0;
}
.rules-grid-thirds {
  grid-template-columns: 1fr 2fr;
}
.rules-card {
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-top: 5px solid var(--accent);
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
  padding: 18px 20px;
}
.rules-card-wide {
  grid-column: 1 / -1;
}
.rules-card-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 38px;
  letter-spacing: 2px;
  color: #111827;
  line-height: 1;
  margin-bottom: 8px;
}
.rules-card p,
.rules-card li {
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.55;
  color: #4a5a78;
}
.rules-card ul {
  margin: 8px 0 0 18px;
  padding: 0;
}
.rules-table-wrap {
  overflow-x: auto;
  border: 1px solid #e2e6ef;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
  margin-top: 12px;
}
.rules-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 720px;
  table-layout: auto;
}
.rules-table th {
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  border-right: 1px solid #e8ecf3;
  padding: 10px 14px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #8a96b0;
  text-align: left;
}
.rules-table td {
  border-bottom: 1px solid #edf0f7;
  border-right: 1px solid #edf0f7;
  padding: 10px 14px;
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #1a2030;
  white-space: normal;
  overflow-wrap: anywhere;
  vertical-align: top;
}
.rules-table tr:nth-child(even) td { background: #fbfcff; }
.rules-table-ranking {
  min-width: 0;
  table-layout: fixed;
}
.rules-table-ranking th:nth-child(1),
.rules-table-ranking td:nth-child(1) {
  width: 18%;
}
.rules-table-ranking th:nth-child(2),
.rules-table-ranking td:nth-child(2) {
  width: 14%;
}
.rules-table-ranking th:nth-child(3),
.rules-table-ranking td:nth-child(3) {
  width: 68%;
}
.rules-note {
  margin-top: 12px;
  padding: 12px 14px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-left: 5px solid #f97316;
  border-radius: 8px;
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #9a3412;
}
.rules-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.rules-pill {
  font-family: 'Rajdhani', sans-serif;
  font-size: 14px;
  font-weight: 800;
  color: #1a2030;
  background: #eef2f7;
  border-radius: 5px;
  padding: 5px 10px;
}
.rankings-layout {
  display: grid;
  grid-template-columns: minmax(0, 3.25fr) minmax(420px, 2fr);
  gap: 18px;
  align-items: start;
  --poll-panel-height: 1960px;
  --poll-row-height: 66px;
}
.rankings-layout.ap-only {
  grid-template-columns: minmax(0, 1fr);
}
.poll-panel {
  background: #fff;
  border: 1px solid #e2e6ef;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
  overflow: hidden;
  height: var(--poll-panel-height);
  display: flex;
  flex-direction: column;
}
.poll-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 18px;
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
}
.poll-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 46px;
  letter-spacing: 3px;
  color: #111827;
  line-height: 1;
}
.poll-subtitle {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #8a96b0;
}
.poll-table-wrap {
  overflow-x: auto;
  overflow-y: hidden;
  flex: 1;
}
.poll-table {
  border-collapse: collapse;
  width: 100%;
  min-width: 1080px;
  table-layout: fixed;
}
.poll-table.ap th:nth-child(1),
.poll-table.ap td:nth-child(1) {
  width: 54px;
}
.poll-table.ap th:nth-child(2),
.poll-table.ap td:nth-child(2) {
  width: 58px;
  text-align: center;
}
.poll-table.ap th:nth-child(3),
.poll-table.ap td:nth-child(3) {
  width: 320px;
}
.poll-table.ap th:nth-child(4),
.poll-table.ap td:nth-child(4),
.poll-table.ap th:nth-child(5),
.poll-table.ap td:nth-child(5),
.poll-table.ap th:nth-child(6),
.poll-table.ap td:nth-child(6),
.poll-table.ap th:nth-child(7),
.poll-table.ap td:nth-child(7),
.poll-table.ap th:nth-child(8),
.poll-table.ap td:nth-child(8) {
  width: 92px;
}
.poll-table.ap th:nth-child(9),
.poll-table.ap td:nth-child(9) {
  width: 170px;
}
.poll-table.coaches {
  min-width: 560px;
}
.poll-table.coaches th:nth-child(1),
.poll-table.coaches td:nth-child(1) {
  width: 54px;
}
.poll-table.coaches th:nth-child(2),
.poll-table.coaches td:nth-child(2) {
  width: 58px;
  text-align: center;
}
.poll-table.coaches th:nth-child(3),
.poll-table.coaches td:nth-child(3) {
  min-width: 210px;
}
.poll-table.coaches th:nth-child(4),
.poll-table.coaches td:nth-child(4),
.poll-table.coaches th:nth-child(5),
.poll-table.coaches td:nth-child(5),
.poll-table.coaches th:nth-child(6),
.poll-table.coaches td:nth-child(6) {
  width: 76px;
}
.poll-table th {
  background: #fbfcff;
  border-bottom: 1px solid #e2e6ef;
  border-right: 1px solid #edf0f7;
  padding: 9px 10px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #8a96b0;
  text-align: left;
  white-space: nowrap;
  height: 42px;
  box-sizing: border-box;
}
.poll-table td {
  border-bottom: 1px solid #edf0f7;
  border-right: 1px solid #edf0f7;
  padding: 9px 10px;
  vertical-align: middle;
  height: var(--poll-row-height);
  box-sizing: border-box;
}
.poll-table tr {
  height: var(--poll-row-height);
}
.poll-table tr:nth-child(even) td { background: #fbfcff; }
.poll-rank {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #eef2f7;
  color: #1a2030;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: 'Rajdhani', sans-serif;
  font-size: 17px;
  font-weight: 800;
}
.poll-rank-cell,
.poll-logo-cell {
  text-align: center;
}
.poll-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
}
.poll-team {
  display: flex;
  align-items: center;
  gap: 10px;
}
.poll-team-logo {
  width: 38px;
  height: 38px;
  object-fit: contain;
}
.poll-team-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #1a2030;
  line-height: 1.05;
  white-space: nowrap;
}
.poll-team-sub {
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 700;
  color: #8a96b0;
  white-space: nowrap;
}
.poll-metric {
  font-family: 'Rajdhani', sans-serif;
  font-size: 18px;
  font-weight: 800;
  color: #1a2030;
  white-space: nowrap;
}
.trend-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 54px;
  border-radius: 5px;
  padding: 3px 8px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 800;
}
.trend-up { background: #dcfce7; color: #166534; }
.trend-down { background: #fee2e2; color: #991b1b; }
.trend-flat { background: #eef2f7; color: #4a5a78; }
.trend-new { background: #fef3c7; color: #92400e; }
.last-game {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 800;
  color: #1a2030;
  white-space: nowrap;
}
.last-game span {
  color: #8a96b0;
  font-size: 12px;
}
.orv-box {
  padding: 14px 18px 16px;
  background: #fbfcff;
  border-top: 1px solid #e2e6ef;
  min-height: 96px;
}
.orv-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #8a96b0;
  margin-bottom: 4px;
}
.orv-text {
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.5;
  color: #1a2030;
}
.rankings-detail-table {
  border-collapse: collapse;
  width: 100%;
  background: #111827;
  border: 1px solid #334155;
  border-radius: 10px;
  overflow: hidden;
  font-family: 'Rajdhani', sans-serif;
}
.rankings-detail-table th {
  background: #1f2937;
  color: #ffffff;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #334155;
}
.rankings-detail-table td {
  color: #f8fafc;
  padding: 9px 12px;
  border-bottom: 1px solid #243044;
  font-size: 15px;
  font-weight: 800;
}
.rankings-detail-table tr:nth-child(even) td {
  background: #172033;
}
.rankings-detail-table td.numeric,
.rankings-detail-table th.numeric {
  text-align: right;
}
.draft-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-left: 8px solid var(--accent);
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
  padding: 20px 24px;
  margin: 10px 0 18px;
}
.draft-hero-main {
  display: flex;
  align-items: center;
  gap: 16px;
}
.draft-hero img {
  width: 72px;
  height: 72px;
  object-fit: contain;
}
.draft-kicker {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #8a96b0;
}
.draft-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 58px;
  letter-spacing: 3px;
  line-height: 1;
  color: #111827;
}
.draft-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.draft-chip {
  font-family: 'Rajdhani', sans-serif;
  font-size: 15px;
  font-weight: 800;
  color: #1a2030;
  background: #eef2f7;
  border-radius: 5px;
  padding: 7px 11px;
}
.draft-round {
  margin: 18px 0 24px;
}
.draft-round-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0 0 10px;
}
.draft-round-title span:first-child {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  letter-spacing: 2px;
  color: #111827;
  line-height: 1;
}
.draft-round-title img {
  width: 46px;
  height: 46px;
  object-fit: contain;
}
.draft-round-title img + span {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  letter-spacing: 2px;
  color: #111827;
  line-height: 1;
}
.draft-round-title span:last-child {
  flex: 1;
  height: 1px;
  background: #dde2ed;
}
.draft-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(112px, 1fr));
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.draft-card {
  display: grid;
  grid-template-rows: auto auto 76px;
  align-items: start;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-left: 7px solid var(--team-color);
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
  padding: 10px 9px 12px;
  min-height: 214px;
}
.draft-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.draft-pick {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #eef2f7;
  color: #1a2030;
  font-family: 'Rajdhani', sans-serif;
  font-size: 16px;
  font-weight: 800;
}
.draft-team-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
  flex-shrink: 0;
}
.draft-player-photo {
  display: block;
  width: 72px;
  height: 72px;
  object-fit: cover;
  object-position: top center;
  border-radius: 50%;
  border: 3px solid #eef2f7;
  background: #f8fafc;
  margin: 2px auto 10px;
}
.draft-player {
  display: -webkit-box;
  align-items: center;
  justify-content: center;
  height: 76px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 24px;
  letter-spacing: 1px;
  color: #111827;
  line-height: 1.05;
  overflow-wrap: break-word;
  word-break: normal;
  hyphens: auto;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  text-align: center;
}
.draft-empty-player {
  color: #b0baca;
}
.draft-type-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 22px 0 12px;
}
.draft-type-heading span:first-child {
  border-radius: 5px;
  padding: 6px 11px;
  color: #ffffff;
  background: #05070b;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 15px;
  font-weight: 900;
  letter-spacing: 2.5px;
  text-transform: uppercase;
}
.draft-type-heading span:last-child {
  flex: 1;
  height: 2px;
  background: #111827;
}
.league-draft-wrap {
  overflow-x: visible;
  padding: 2px 0 18px;
}
.league-draft-phase-headings {
  display: grid;
  grid-template-columns: repeat(var(--conference-count), minmax(0, 1fr));
  gap: 10px;
  margin: 16px 0 12px;
}
.league-draft-phase-title {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 4px 10px 4px 12px;
  border-left: 7px solid var(--phase-color);
}
.league-draft-phase-title.phase-start {
  padding-left: 12px;
}
.league-draft-phase-title span:first-child {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  line-height: 1;
  letter-spacing: 2px;
  color: #111827;
  white-space: nowrap;
}
.league-draft-phase-title span:last-child {
  flex: 1;
  height: 2px;
  background: var(--phase-color);
}
.league-draft-board {
  --conf-header-height: 82px;
  --conf-logo-size: 38px;
  --conf-font-size: 22px;
  --pick-icon-size: 30px;
  --pick-photo-size: 31px;
  --pick-slot-size: 31px;
  --pick-slot-font: 11px;
  --pick-player-font: 14px;
  --pick-row-height: 82px;
  display: grid;
  grid-template-columns: repeat(var(--conference-count), minmax(0, 1fr));
  gap: 10px;
  width: 100%;
  align-items: start;
}
.league-draft-board.medium {
  --conf-header-height: 98px;
  --conf-logo-size: 50px;
  --conf-font-size: 29px;
  --pick-icon-size: 42px;
  --pick-photo-size: 44px;
  --pick-slot-size: 42px;
  --pick-slot-font: 14px;
  --pick-player-font: 19px;
  --pick-row-height: 112px;
  gap: 14px;
}
.league-draft-board.roomy {
  --conf-header-height: 124px;
  --conf-logo-size: 70px;
  --conf-font-size: 40px;
  --pick-icon-size: 58px;
  --pick-photo-size: 60px;
  --pick-slot-size: 54px;
  --pick-slot-font: 17px;
  --pick-player-font: 26px;
  --pick-row-height: 146px;
  gap: 18px;
}
.league-draft-column {
  min-width: 0;
  overflow: hidden;
  background: #ffffff;
  border: 1px solid #dfe4ed;
  border-radius: 9px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
}
.league-draft-column.phase-start {
  margin-left: 4px;
  border-left: 5px solid #111827;
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  box-shadow: -7px 0 0 #ffffff, -9px 0 0 #111827, 0 2px 10px rgba(15,23,42,0.07);
}
.league-draft-header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: var(--conf-header-height);
  padding: 9px 6px;
  color: #111827;
  background: #f8fafc;
  border-bottom: 5px solid #c8102e;
}
.league-draft-header img {
  width: var(--conf-logo-size);
  height: var(--conf-logo-size);
  object-fit: contain;
}
.league-draft-header span {
  font-family: 'Bebas Neue', sans-serif;
  font-size: var(--conf-font-size);
  line-height: 1;
  letter-spacing: 1px;
  text-align: center;
}
.league-draft-pick {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: var(--pick-row-height);
  box-sizing: border-box;
  padding: 6px 5px;
  background: #ffffff;
  border-bottom: 1px solid #e6eaf1;
  border-left: 5px solid var(--team-color);
  text-align: center;
}
.league-draft-pick-top {
  display: grid;
  grid-template-columns: repeat(3, var(--pick-icon-size));
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-bottom: 4px;
}
.league-draft-pick-number {
  width: var(--pick-slot-size);
  height: var(--pick-slot-size);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #111827;
  background: #eef2f7;
  font-family: 'Rajdhani', sans-serif;
  font-size: var(--pick-slot-font);
  font-weight: 900;
}
.league-draft-pick img {
  width: var(--pick-icon-size);
  height: var(--pick-icon-size);
  object-fit: contain;
}
.league-draft-pick img.league-draft-player-photo {
  width: var(--pick-photo-size);
  height: var(--pick-photo-size);
  border: 2px solid #e2e8f0;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  background: #f8fafc;
}
.league-draft-player {
  display: -webkit-box;
  min-height: 2.1em;
  min-width: 0;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: var(--pick-player-font);
  font-weight: 900;
  line-height: 1.05;
  color: #111827;
  text-transform: uppercase;
  overflow: hidden;
  overflow-wrap: break-word;
  word-break: normal;
  hyphens: auto;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}
.league-draft-empty {
  padding: 18px 10px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 800;
  color: #9aa5be;
  text-align: center;
  text-transform: uppercase;
}
.history-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 24px;
  margin: 10px 0 18px;
  padding: 26px 28px;
  color: #ffffff;
  background: #05070b;
  border-top: 7px solid var(--accent);
  border-radius: 10px;
  box-shadow: 0 7px 24px rgba(15,23,42,0.18);
}
.history-kicker {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--accent);
}
.history-title {
  margin-top: 3px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 64px;
  line-height: 0.95;
  letter-spacing: 3px;
}
.history-sub {
  max-width: 760px;
  margin-top: 8px;
  font-family: 'Barlow', sans-serif;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  color: #b8c2d2;
}
.history-hero-logo {
  width: 108px;
  height: 108px;
  object-fit: contain;
}
.history-metrics {
  display: grid;
  grid-template-columns: repeat(var(--metric-count), minmax(0, 1fr));
  gap: 10px;
  margin: 0 0 24px;
}
.history-metric {
  padding: 13px 15px;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-top: 4px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
}
.history-metric-value {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 38px;
  line-height: 1;
  letter-spacing: 1px;
  color: #111827;
}
.history-metric-label {
  margin-top: 3px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #8a96b0;
}
.player-value-main {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 34px;
  line-height: 1;
  letter-spacing: 1px;
  color: #111827;
  white-space: nowrap;
}
.history-section-title {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 22px 0 10px;
}
.history-section-title span {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 42px;
  line-height: 1;
  letter-spacing: 2px;
  color: #111827;
}
.history-section-title div {
  flex: 1;
  height: 2px;
  background: #dce2ec;
}
.history-table-wrap {
  overflow-x: auto;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-radius: 9px;
  box-shadow: 0 2px 12px rgba(15,23,42,0.08);
}
.history-table {
  width: 100%;
  border-collapse: collapse;
}
.history-table th {
  padding: 9px 11px;
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1.7px;
  text-align: center;
  text-transform: uppercase;
  color: #8a96b0;
  white-space: nowrap;
}
.history-table th:first-child { text-align: left; }
.history-table td {
  padding: 9px 11px;
  border-bottom: 1px solid #edf0f7;
  font-family: 'Rajdhani', sans-serif;
  font-size: 15px;
  font-weight: 800;
  text-align: center;
  color: #334155;
}
.history-table td:first-child { text-align: left; }
.history-table .record-main {
  font-family: 'Rajdhani', sans-serif;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.05;
}
.history-table .record-sub {
  margin-top: 2px;
  font-size: 11px;
  font-weight: 700;
  color: #9aa5be;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-table .rivalry-pill {
  margin-top: 4px;
}
.history-table tr.rivalry-series-row td {
  background: linear-gradient(90deg, rgba(238,242,255,0.96), #ffffff 48%);
  border-top: 1px solid #c7d2fe;
  border-bottom: 1px solid #c7d2fe;
}
.history-table tr.rivalry-series-row td:first-child {
  border-left: 5px solid #4f46e5;
}
.history-rivalry-sub {
  margin-top: 4px;
}
.history-grid-rivalry {
  display: inline-block;
  margin-top: 4px;
  border-radius: 999px;
  padding: 2px 7px 3px;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  color: #312e81;
  font-family: 'Rajdhani', sans-serif;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.7px;
  text-transform: uppercase;
}
.champion-star {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 50%;
  color: #111827;
  font-size: 14px;
  font-weight: 900;
}
.champion-star.national {
  background: #f2cf68;
  box-shadow: inset 0 0 0 1px #d7ad31;
}
.champion-star.conference {
  background: #e2e8f0;
  box-shadow: inset 0 0 0 1px #94a3b8;
}
.history-team {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 210px;
}
.history-team img {
  width: 34px;
  height: 34px;
  object-fit: contain;
}
.history-team-name {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 17px;
  font-weight: 900;
  line-height: 1;
  text-transform: uppercase;
  color: #111827;
}
.history-team-sub {
  margin-top: 2px;
  font-size: 10px;
  color: #9aa5be;
}
.player-profile-hero {
  display: grid;
  grid-template-columns: 150px minmax(0, 1fr);
  align-items: center;
  gap: 24px;
  margin: 12px 0 20px;
  padding: 24px 28px;
  color: #ffffff;
  background: #05070b;
  border-top: 7px solid #f2cf68;
  border-radius: 10px;
  box-shadow: 0 7px 24px rgba(15,23,42,0.18);
}
.player-profile-hero img {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
  object-position: top center;
  background: #eef2f7;
  border: 5px solid #ffffff;
}
.player-profile-kicker {
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #f2cf68;
}
.player-profile-name {
  margin-top: 4px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 68px;
  line-height: 0.95;
  letter-spacing: 3px;
}
.player-profile-meta {
  margin-top: 9px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 16px;
  font-weight: 800;
  color: #cbd5e1;
}
.player-ownership-table td,
.player-ownership-table th {
  text-align: center !important;
}
.player-ownership-table td {
  height: 74px;
}
.player-ownership-table .ownership-team-logo {
  width: 52px;
  height: 52px;
  object-fit: contain;
}
.player-draft-stack {
  display: grid;
  gap: 8px;
}
.player-draft-tile {
  display: grid;
  grid-template-columns: 42px 42px minmax(0, 1fr);
  align-items: center;
  gap: 9px;
  min-height: 68px;
  padding: 8px 10px;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-left: 6px solid var(--team-color);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(15,23,42,0.06);
}
.player-draft-tile img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}
.player-draft-pick {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #eef2f7;
  font-family: 'Rajdhani', sans-serif;
  font-size: 13px;
  font-weight: 900;
  color: #111827;
}
.player-draft-year {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 25px;
  line-height: 1;
  color: #111827;
}
.player-draft-meta {
  margin-top: 2px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 900;
  color: #64748b;
  text-transform: uppercase;
}
.player-history-matrix {
  min-width: 1280px;
}
.player-history-matrix th,
.player-history-matrix td {
  text-align: center !important;
  white-space: nowrap;
}
.player-history-matrix .season-row th {
  padding: 9px 12px;
  background: #111827;
  color: #ffffff;
  font-size: 17px;
  text-align: left !important;
}
.player-status {
  font-size: 15px;
}
.player-history-matrix .conf-logo-history {
  width: 42px;
  height: 32px;
  object-fit: contain;
}
.player-chart-shell {
  padding: 4px 10px 10px;
  background: #f8fafc;
  border: 1px solid #e2e6ef;
  border-top: 5px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
}
@media (max-width: 760px) {
  .player-profile-hero {
    grid-template-columns: 90px minmax(0, 1fr);
    gap: 14px;
    padding: 18px;
  }
  .player-profile-hero img {
    width: 90px;
    height: 90px;
  }
  .player-profile-name {
    font-size: 44px;
  }
}
.history-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 11px;
}
.history-card {
  padding: 14px 15px;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-left: 6px solid var(--accent);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15,23,42,0.07);
}
.history-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.history-card-eyebrow {
  font-family: 'Rajdhani', sans-serif;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #8a96b0;
}
.history-card-score {
  margin-top: 5px;
  font-family: 'Bebas Neue', sans-serif;
  font-size: 31px;
  line-height: 1;
  letter-spacing: 1px;
  color: #111827;
}
.history-card-detail {
  margin-top: 4px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
  color: #64748b;
}
.history-card img {
  width: 42px;
  height: 42px;
  object-fit: contain;
}
.history-yearbook {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 11px;
}
.history-year {
  padding: 15px;
  background: #ffffff;
  border: 1px solid #e2e6ef;
  border-top: 5px solid var(--accent);
  border-radius: 8px;
}
.history-year-label {
  font-family: 'Bebas Neue', sans-serif;
  font-size: 34px;
  line-height: 1;
  color: #111827;
}
.history-year-record {
  margin-top: 7px;
  font-family: 'Barlow Condensed', sans-serif;
  font-size: 21px;
  font-weight: 900;
  color: #334155;
}
.history-year-meta {
  margin-top: 4px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 12px;
  font-weight: 800;
  color: #8a96b0;
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
            [2022, 2023, 2024, 2025, 2026],
            index=4,
            key="global_season",
        )
        st.html("</div>")
    return selected_season


def render_data_controls() -> None:
    with st.sidebar:
        st.subheader("Data Controls")
        st.caption("Published data is cached for 24 hours.")
        if st.button(
            "Refresh All Data",
            key="refresh_all_data",
            use_container_width=True,
        ):
            st.cache_data.clear()
            st.rerun()


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


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading team branding...")
def load_branding_data(
    cache_version: str,
) -> tuple[pd.DataFrame, ...]:
    del cache_version
    return fetch_branding_data()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading NCAA/NFL Crossover rosters...")
def load_all_rosters(schools: pd.DataFrame) -> pd.DataFrame:
    return fetch_all_rosters(schools)


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading future draft picks...")
def load_future_draft_picks() -> pd.DataFrame:
    return fetch_future_draft_picks()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner="Loading dynasty asset values...")
def load_dynasty_asset_values() -> tuple[pd.DataFrame, pd.DataFrame]:
    players = pd.read_csv(DYNASTY_PLAYER_VALUES_URL)
    picks = pd.read_csv(DYNASTY_PICK_VALUES_URL)
    return players, picks


@st.cache_data(show_spinner="Calculating dynasty coaches poll...", max_entries=8)
def build_dynasty_coaches_poll(
    rosters: pd.DataFrame,
    draft_picks: pd.DataFrame,
    schools: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "Team", "Conference", "Format", "PlayerValue", "DraftPickValue",
        "TotalValue", "MatchedPlayers", "UnmatchedPlayers", "Rank", "ConferenceRank",
    ]
    if rosters.empty:
        return pd.DataFrame(columns=columns)

    player_values, pick_values = load_dynasty_asset_values()
    player_values["_player_key"] = player_values["player"].map(dynasty_player_key)
    player_values = player_values.drop_duplicates("_player_key", keep="first")
    player_value_lookup = player_values.set_index("_player_key")

    valued_rosters = rosters.copy()
    valued_rosters["_player_key"] = valued_rosters["player_name"].map(dynasty_player_key)
    valued_rosters = valued_rosters.merge(
        player_value_lookup[["value_1qb", "value_2qb"]],
        left_on="_player_key",
        right_index=True,
        how="left",
    )
    valued_rosters["Format"] = valued_rosters["league_name"].map(
        lambda conference: "Superflex" if conference in SUPERFLEX_CONFERENCES else "1QB"
    )
    valued_rosters["PlayerValue"] = valued_rosters.apply(
        lambda row: row["value_2qb"] if row["Format"] == "Superflex" else row["value_1qb"],
        axis=1,
    )
    valued_rosters["MatchedPlayer"] = valued_rosters["PlayerValue"].notna()
    valued_rosters["PlayerValue"] = pd.to_numeric(
        valued_rosters["PlayerValue"], errors="coerce"
    ).fillna(0)
    team_values = (
        valued_rosters.groupby(
            ["league_name", "roster_id", "team_name", "Format"],
            as_index=False,
            dropna=False,
        )
        .agg(
            PlayerValue=("PlayerValue", "sum"),
            Players=("player_name", "count"),
            MatchedPlayers=("MatchedPlayer", "sum"),
        )
        .rename(columns={"league_name": "Conference", "team_name": "Team"})
    )
    team_values["UnmatchedPlayers"] = team_values["Players"] - team_values["MatchedPlayers"]

    pick_values["season"] = pd.to_numeric(
        pick_values["player"].astype(str).str.extract(r"^(\d{4})")[0],
        errors="coerce",
    )
    pick_values["round"] = pd.to_numeric(
        pick_values["player"].astype(str).str.extract(r"(?:Pick\s+)?(\d+)(?:\.|st|nd|rd|th)")[0],
        errors="coerce",
    )
    for value_column, ecr_column in [("value_1qb", "ecr_1qb"), ("value_2qb", "ecr_2qb")]:
        reference = (
            player_values[[ecr_column, value_column]]
            .dropna()
            .groupby(ecr_column, as_index=False)[value_column]
            .mean()
            .sort_values(ecr_column)
        )
        pick_values[value_column] = pd.to_numeric(pick_values[ecr_column], errors="coerce").map(
            lambda ecr: float(
                pd.Series(reference[value_column].values, index=reference[ecr_column])
                .reindex(reference[ecr_column].tolist() + [ecr])
                .sort_index()
                .interpolate(method="index", limit_direction="both")
                .loc[ecr]
            )
            if not pd.isna(ecr)
            else 0
        )
    season_round_values = (
        pick_values.dropna(subset=["season", "round"])
        .groupby(["season", "round"])[["value_1qb", "value_2qb"]]
        .mean()
    )
    current_round_values = (
        pick_values.loc[pick_values["player"].astype(str).str.contains(r"\bPick\s+\d+\.", regex=True)]
        .dropna(subset=["round"])
        .groupby("round")[["value_1qb", "value_2qb"]]
        .mean()
    )

    pick_totals: dict[tuple[str, int], float] = {}
    if not draft_picks.empty:
        for _, pick in draft_picks.iterrows():
            conference = clean_text(pick.get("league_name"))
            owner_id = pd.to_numeric(pick.get("owner_roster_id"), errors="coerce")
            round_number = pd.to_numeric(pick.get("round"), errors="coerce")
            season = pd.to_numeric(pick.get("season"), errors="coerce")
            if pd.isna(owner_id) or pd.isna(round_number):
                continue
            round_key = float(round_number)
            season_key = float(season) if not pd.isna(season) else pd.NA
            value_column = "value_2qb" if conference in SUPERFLEX_CONFERENCES else "value_1qb"
            if not pd.isna(season_key) and (season_key, round_key) in season_round_values.index:
                pick_value = float(season_round_values.loc[(season_key, round_key), value_column])
            elif round_key in current_round_values.index:
                pick_value = float(current_round_values.loc[round_key, value_column])
            else:
                continue
            key = (conference, int(owner_id))
            pick_totals[key] = pick_totals.get(key, 0.0) + pick_value

    team_values["DraftPickValue"] = team_values.apply(
        lambda row: pick_totals.get((row["Conference"], int(row["roster_id"])), 0.0),
        axis=1,
    )
    team_values["TotalValue"] = team_values["PlayerValue"] + team_values["DraftPickValue"]
    team_values["Rank"] = team_values["TotalValue"].rank(ascending=False, method="min").astype(int)
    team_values["ConferenceRank"] = (
        team_values.groupby("Conference")["TotalValue"].rank(ascending=False, method="min").astype(int)
    )
    return team_values[columns].sort_values(["Rank", "Team"]).reset_index(drop=True)


@st.cache_data(show_spinner="Auditing dynasty player values...", max_entries=8)
def unmatched_dynasty_players(rosters: pd.DataFrame) -> pd.DataFrame:
    columns = ["Team", "Conference", "Player", "Position", "Roster Spot"]
    if rosters.empty:
        return pd.DataFrame(columns=columns)

    player_values, _ = load_dynasty_asset_values()
    valued_keys = set(player_values["player"].map(dynasty_player_key))
    audit = rosters.copy()
    audit["_player_key"] = audit["player_name"].map(dynasty_player_key)
    audit = audit.loc[~audit["_player_key"].isin(valued_keys)].copy()
    if audit.empty:
        return pd.DataFrame(columns=columns)

    return (
        audit.rename(
            columns={
                "team_name": "Team",
                "league_name": "Conference",
                "player_name": "Player",
                "position": "Position",
                "roster_spot": "Roster Spot",
            }
        )[columns]
        .drop_duplicates()
        .sort_values(["Team", "Player"])
        .reset_index(drop=True)
    )


@st.cache_data(show_spinner="Indexing team information...", max_entries=16)
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
            "nickname": clean_text(row.get("Nickname")),
            "owner": clean_text(row.get("Owner")),
            "color": clean_text(row.get("Color"), "#1a2030"),
            "color2": clean_text(row.get("Color2"), "#c8102e"),
        }
    return lookup


@st.cache_data(show_spinner="Indexing weekly scores...", max_entries=32)
def score_lookup(scores: pd.DataFrame, cache_version: str = STANDINGS_CACHE_VERSION) -> dict[tuple[str, int], float]:
    del cache_version
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
    return first_value(match, "Logo", "")


def conference_code(conferences: pd.DataFrame, conference: str) -> str:
    match = conferences.loc[conferences["Conference"].astype(str).eq(str(conference))]
    return first_value(match, "Code", conference)


def taken_color(count: int, max_count: int = 12) -> str:
    ratio = count / max(max_count, 1)
    if ratio >= 0.83:
        return "#166534"
    if ratio >= 0.58:
        return "#3f8f29"
    if ratio >= 0.42:
        return "#d97706"
    if ratio >= 0.25:
        return "#dc2626"
    return "#7f1d1d"


def latest_result_week(scores: pd.DataFrame) -> Optional[int]:
    if scores.empty or not {"Week", "Points"}.issubset(scores.columns):
        return None
    completed = scores.loc[
        pd.to_numeric(scores["Week"], errors="coerce").gt(0)
        & pd.to_numeric(scores["Points"], errors="coerce").notna()
    ]
    weeks = pd.to_numeric(completed["Week"], errors="coerce").dropna()
    return int(weeks.max()) if not weeks.empty else None


def latest_completed_week_index(
    weeks: list[int],
    scores: pd.DataFrame,
) -> int:
    if not weeks:
        return 0
    result_week = latest_result_week(scores)
    eligible = [week for week in weeks if result_week is not None and week <= result_week]
    default_week = max(eligible) if eligible else max(weeks)
    return weeks.index(default_week)


def next_unplayed_schedule_week_index(
    weeks: list[int],
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
) -> int:
    if not weeks:
        return 0
    if schedule.empty or not {"Week", "TeamA", "TeamB"}.issubset(schedule.columns):
        return 0

    schedule_copy = schedule.copy()
    schedule_copy["Week"] = pd.to_numeric(schedule_copy["Week"], errors="coerce")
    scores_by_team_week = score_lookup(scores)

    for week in sorted(weeks):
        week_games = schedule_copy.loc[schedule_copy["Week"].eq(week)]
        if week_games.empty:
            continue

        for _, game in week_games.iterrows():
            team_a = clean_text(game.get("TeamA"))
            team_b = clean_text(game.get("TeamB"))
            score_a = scores_by_team_week.get((match_key(team_a), int(week)))
            score_b = scores_by_team_week.get((match_key(team_b), int(week)))
            if not is_completed_score(score_a, score_b):
                return weeks.index(week)

    return len(weeks) - 1


def score_class(points: Optional[float], opponent_points: Optional[float]) -> str:
    if not is_completed_score(points, opponent_points):
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
    ap_ranks: Optional[dict[str, int]] = None,
    record: str = "",
) -> str:
    info = teams.get(team, {})
    logo = clean_text(info.get("logo"))
    nickname = clean_text(info.get("nickname"))
    color = esc(info.get("color"), "#1a2030")
    status = score_class(points, opponent_points)
    score_text = f"{points:.2f}" if points is not None else "-"
    logo_html = f'<img src="{esc(logo)}" alt="{esc(team)}">' if logo else ""
    display_name = f"{rank_prefix(team, ap_ranks)}{team}"

    return f"""
<div class="matchup-row {status if status in ('win', 'loss') else ''}" style="--team-color:{color};">
  <div class="matchup-team">
    {logo_html}
    <div>
      <div class="matchup-name">{esc(display_name)}</div>
      <div class="matchup-conf">{esc(nickname)}{f' {esc(record)}' if record else ''}</div>
    </div>
  </div>
  <div class="score-box {status if status in ('win', 'loss', 'tie') else ''}">{score_text}</div>
</div>
"""


def bowl_for_notes(notes: object, bowls: Optional[pd.DataFrame]) -> dict[str, str]:
    note_text = clean_text(notes)
    if not note_text or "bowl" not in note_text.casefold():
        return {}

    fallback = {"name": note_text, "logo": ""}
    if bowls is None or bowls.empty or "Bowl" not in bowls.columns:
        return fallback

    note_key = match_key(note_text)
    matches = []
    for _, row in bowls.iterrows():
        bowl_name = clean_text(row.get("Bowl"))
        bowl_key = match_key(bowl_name)
        if bowl_name and (bowl_key in note_key or note_key in bowl_key):
            matches.append(
                {
                    "name": bowl_name,
                    "logo": clean_text(row.get("Logo")),
                }
            )
    return max(matches, key=lambda bowl: len(bowl["name"]), default=fallback)


def rivalry_name(game: object) -> str:
    if isinstance(game, pd.Series):
        return clean_text(game.get("Rivalry")) or clean_text(game.get("Rivarly"))
    if isinstance(game, dict):
        return clean_text(game.get("Rivalry")) or clean_text(game.get("Rivarly"))
    return ""


def render_rivalry_pill(rivalry: str) -> str:
    rivalry = clean_text(rivalry)
    if not rivalry:
        return ""
    return f'<span class="rivalry-pill">Rivalry: {esc(rivalry)}</span>'


def render_rivalry_banner(rivalry: str) -> str:
    rivalry = clean_text(rivalry)
    if not rivalry:
        return ""
    return f"""
<div class="rivalry-banner">
  <div>
    <div class="rivalry-kicker">Rivalry Game</div>
    <div class="rivalry-name">{esc(rivalry)}</div>
  </div>
</div>
"""


def render_bowl_banner(bowl: dict[str, str]) -> str:
    if not bowl:
        return ""
    logo = clean_text(bowl.get("logo"))
    logo_html = f'<img src="{esc(logo)}" alt="{esc(bowl.get("name"))}">' if logo else ""
    return f"""
<div class="bowl-banner">
  {logo_html}
  <div>
    <div class="bowl-kicker">Postseason Bowl</div>
    <div class="bowl-name">{esc(bowl.get("name"))}</div>
  </div>
</div>
"""


def render_boxscore_bowl_masthead(
    bowl: dict[str, str],
    year: int,
    week: int,
) -> str:
    if not bowl:
        return ""
    logo = clean_text(bowl.get("logo"))
    logo_html = (
        f'<img class="boxscore-bowl-logo" src="{esc(logo)}" alt="{esc(bowl.get("name"))}">'
        if logo
        else '<div></div>'
    )
    return f"""
<div class="boxscore-bowl-masthead">
  {logo_html}
  <div class="boxscore-bowl-copy">
    <div class="boxscore-bowl-kicker">NCAA/NFL Crossover Postseason</div>
    <div class="boxscore-bowl-title">{esc(bowl.get("name"))}</div>
    <div class="boxscore-bowl-meta">{year} Bowl Season &nbsp; | &nbsp; Week {week} Box Score</div>
  </div>
  <div></div>
</div>
"""


def render_boxscore_rivalry_masthead(rivalry: str, compact: bool = False) -> str:
    rivalry = clean_text(rivalry)
    if not rivalry:
        return ""
    return f"""
<div class="boxscore-rivalry-masthead{' compact' if compact else ''}">
  <div class="boxscore-rivalry-kicker">Rivalry Game</div>
  <div class="boxscore-rivalry-title">{esc(rivalry)}</div>
</div>
"""


STARTER_SLOTS = [
    ("QB", ["QB"], "#ef4444"),
    ("RB", ["RB"], "#f97316"),
    ("RB", ["RB"], "#f97316"),
    ("WR", ["WR"], "#eab308"),
    ("WR", ["WR"], "#eab308"),
    ("TE", ["TE"], "#22c55e"),
    ("FLX", ["QB", "RB", "WR", "TE"], "#7dd3fc"),
    ("FLX", ["QB", "RB", "WR", "TE"], "#7dd3fc"),
]
BOXSCORE_STATS = [
    ("Pass Yds", 80, 390),
    ("Pass TD", 0, 4),
    ("2PC", 0, 2),
    ("Int", 0, 3),
    ("Rush Yds", 0, 145),
    ("Rush TD", 0, 3),
    ("Rec", 0, 11),
    ("Rec Yds", 0, 155),
    ("Rec TD", 0, 3),
    ("ST TD", 0, 1),
    ("FF", 0, 1),
    ("FR", 0, 1),
    ("FL", 0, 1),
    ("F TD", 0, 1),
]


def seeded_float(*parts: object, low: float = 0.0, high: float = 1.0) -> float:
    seed = "|".join(clean_text(part) for part in parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    value = int(digest[:12], 16) / float(0xFFFFFFFFFFFF)
    return low + ((high - low) * value)


def boxscore_points(team: str, week: int, player: str, slot: str) -> float:
    return round(seeded_float(team, week, player, slot, low=1.8, high=28.6), 2)


def boxscore_projection(team: str, week: int, player: str, slot: str) -> float:
    return round(seeded_float(team, week, player, slot, "projection", low=4.0, high=24.0), 1)


def boxscore_total(rows: list[dict[str, object]], team: str, week: int) -> float:
    total = 0.0
    for row in rows:
        player = clean_text(row.get("player"))
        slot = clean_text(row.get("slot"))
        if player and player != "TBD":
            actual_points = pd.to_numeric(row.get("points"), errors="coerce")
            if not pd.isna(actual_points):
                total += float(actual_points)
            else:
                total += boxscore_points(team, week, player, slot)
    return total


def player_stat_pills(team: str, week: int, player: str, slot: str) -> str:
    if not player or player == "TBD":
        return ""

    stat_count = int(seeded_float(team, week, player, slot, "stat-count", low=2, high=5.99))
    stats = sorted(
        BOXSCORE_STATS,
        key=lambda stat: seeded_float(team, week, player, slot, stat[0], "stat-order"),
    )[:stat_count]
    pills = []
    for label, low, high in stats:
        value = int(round(seeded_float(team, week, player, slot, label, low=low, high=high)))
        if value == 0 and label not in {"Int", "FL"}:
            value = 1
        pills.append(f'<span class="boxscore-stat-pill">{esc(label)}: {value}</span>')
    return f'<div class="boxscore-stat-row">{"".join(pills)}</div>'


def team_boxscore_players(rosters: pd.DataFrame, team: str) -> dict[str, list[dict[str, object]]]:
    team_roster = rosters.loc[rosters["team_name"].eq(team)].copy()
    if team_roster.empty:
        return {"Starters": [], "Bench": [], "Injured Reserve": [], "Taxi": []}

    team_roster["status_sort"] = team_roster["roster_spot"].map(ROSTER_STATUS_ORDER).fillna(9)
    team_roster = team_roster.sort_values(["status_sort", "position", "player_name"], na_position="last")
    starters_pool = team_roster.loc[team_roster["roster_spot"].eq("Starter")].copy()
    used_indexes: set[int] = set()
    starters = []

    for slot, eligible_positions, color in STARTER_SLOTS:
        available = starters_pool.loc[
            starters_pool["position"].isin(eligible_positions)
            & ~starters_pool.index.isin(used_indexes)
        ]
        if available.empty:
            starters.append(
                {
                    "player": "TBD",
                    "position": "",
                    "slot": slot,
                    "color": color,
                }
            )
            continue

        player = available.iloc[0]
        used_indexes.add(int(player.name))
        starters.append(
            {
                "player": clean_text(player.get("player_name"), "TBD"),
                "position": clean_text(player.get("position")),
                "slot": slot,
                "color": color,
            }
        )

    groups = {"Starters": starters, "Bench": [], "Injured Reserve": [], "Taxi": []}
    status_labels = {
        "Bench": "Bench",
        "Reserve": "Injured Reserve",
        "Taxi": "Taxi",
    }
    for roster_spot, label in status_labels.items():
        rows = team_roster.loc[team_roster["roster_spot"].eq(roster_spot)].copy()
        for _, row in rows.iterrows():
            groups[label].append(
                {
                    "player": clean_text(row.get("player_name"), "TBD"),
                    "position": clean_text(row.get("position")),
                    "slot": "",
                    "color": "#e5e7eb",
                }
            )

    return groups


def team_boxscore_from_starters(starters: pd.DataFrame, team: str, week: int) -> dict[str, list[dict[str, object]]]:
    groups = {"Starters": [], "Bench": [], "Injured Reserve": [], "Taxi": []}
    if starters.empty:
        return groups

    rows = starters.loc[
        starters["Team"].astype(str).eq(team)
        & pd.to_numeric(starters["Week"], errors="coerce").eq(week)
    ].copy()
    if rows.empty:
        return groups

    position_order = {"QB": 0, "RB": 1, "WR": 2, "TE": 3}
    rows["position_sort"] = rows["Position"].map(position_order).fillna(9)
    rows = rows.sort_values(["position_sort", "Player"], na_position="last")
    if "RosterSpot" in rows.columns and rows["RosterSpot"].notna().any():
        starter_rows = rows.loc[rows["RosterSpot"].astype(str).eq("Starter")].copy()
    else:
        starter_rows = rows.copy()
    available = starter_rows.to_dict("records")
    used_indexes: set[int] = set()

    def take_player(slot: str, eligible_positions: list[str], color: str) -> dict[str, object]:
        for index, player in enumerate(available):
            if index in used_indexes:
                continue
            if clean_text(player.get("Position")) in eligible_positions:
                used_indexes.add(index)
                return {
                    "player": clean_text(player.get("Player"), "TBD"),
                    "position": clean_text(player.get("Position")),
                    "slot": slot,
                    "color": color,
                    "points": player.get("Points"),
                }
        return {"player": "TBD", "position": "", "slot": slot, "color": color, "points": pd.NA}

    for slot, eligible_positions, color in STARTER_SLOTS:
        groups["Starters"].append(take_player(slot, eligible_positions, color))

    status_labels = {
        "Bench": "Bench",
        "Reserve": "Injured Reserve",
        "Taxi": "Taxi",
    }
    if "RosterSpot" in rows.columns:
        for roster_spot, label in status_labels.items():
            group_rows = rows.loc[rows["RosterSpot"].astype(str).eq(roster_spot)]
            for _, player in group_rows.iterrows():
                groups[label].append(
                    {
                        "player": clean_text(player.get("Player"), "TBD"),
                        "position": clean_text(player.get("Position")),
                        "slot": "",
                        "color": "#e5e7eb",
                        "points": player.get("Points"),
                    }
                )

    return groups


def starter_points_for_team_week(starters: pd.DataFrame, team: str, week: int) -> Optional[float]:
    if starters.empty or not {"Team", "Week", "Points"}.issubset(starters.columns):
        return None

    rows = starters.loc[
        starters["Team"].astype(str).eq(team)
        & pd.to_numeric(starters["Week"], errors="coerce").eq(week)
    ].copy()
    if rows.empty:
        return None

    if "TeamPoints" in rows.columns:
        team_points = pd.to_numeric(rows["TeamPoints"], errors="coerce").dropna()
        if not team_points.empty:
            return float(team_points.iloc[0])

    points = pd.to_numeric(rows["Points"], errors="coerce").sum(min_count=1)
    if pd.isna(points):
        return None
    return float(points)


@st.cache_data(show_spinner="Calculating starter scores...", max_entries=16)
def starter_score_lookup(starters: pd.DataFrame) -> dict[tuple[str, int], float]:
    if starters.empty or not {"Team", "Week", "Points"}.issubset(starters.columns):
        return {}

    rows = starters.copy()
    rows["Week"] = pd.to_numeric(rows["Week"], errors="coerce")
    rows["Points"] = pd.to_numeric(rows["Points"], errors="coerce")
    rows = rows.dropna(subset=["Team", "Week"])
    starter_rows = rows
    if "RosterSpot" in rows.columns and rows["RosterSpot"].notna().any():
        starter_rows = rows.loc[rows["RosterSpot"].astype(str).eq("Starter")].copy()

    group_columns = ["Team", "Week"]
    if "TeamPoints" in rows.columns:
        rows["TeamPoints"] = pd.to_numeric(rows["TeamPoints"], errors="coerce")
        official = (
            rows.dropna(subset=["TeamPoints"])
            .groupby(group_columns, dropna=False)["TeamPoints"]
            .first()
        )
    else:
        official = pd.Series(dtype=float)

    player_sums = starter_rows.groupby(group_columns, dropna=False)["Points"].sum(min_count=1)
    lookup = {}
    for team_week, points in player_sums.items():
        official_points = official.get(team_week, pd.NA)
        final_points = official_points if not pd.isna(official_points) else points
        if not pd.isna(final_points):
            lookup[(match_key(team_week[0]), int(team_week[1]))] = float(final_points)
    return lookup


@st.cache_data(show_spinner="Applying season ownership...", max_entries=8)
def apply_season_owners(schools: pd.DataFrame, season: int) -> pd.DataFrame:
    schools = schools.copy()
    expected = f"{season}owner"
    owner_column = next(
        (
            column
            for column in schools.columns
            if "".join(character for character in str(column).casefold() if character.isalnum())
            == expected
        ),
        None,
    )
    schools["Owner"] = schools[owner_column].fillna("").astype(str).str.strip() if owner_column else ""
    return schools


def nickname_owner(nickname: object, owner: object) -> str:
    values = [clean_text(nickname), clean_text(owner)]
    return " · ".join(value for value in values if value)


def boxscore_team_header(
    team: str,
    teams: dict[str, dict[str, str]],
    ranks: dict[str, int],
    record: str,
    side: str = "left",
) -> str:
    info = teams.get(team, {})
    logo = clean_text(info.get("logo"))
    nickname = clean_text(info.get("nickname"))
    color = esc(info.get("color"), "#1a2030")
    rank = rank_for_team(team, ranks)
    return f"""
<div class="boxscore-team-panel {side}" style="--team-color:{color};">
  {f'<img src="{esc(logo)}" alt="{esc(team)}">' if logo and side == 'left' else ''}
  <div>
    {f'<span class="boxscore-rank">No. {rank}</span>' if rank is not None and rank <= 25 else ''}
    <div class="boxscore-team-name">{esc(team)}</div>
    <div class="boxscore-team-sub">{esc(nickname)}</div>
    {f'<div class="boxscore-record">{esc(record)}</div>' if record else ''}
  </div>
  {f'<img src="{esc(logo)}" alt="{esc(team)}">' if logo and side == 'right' else ''}
</div>
"""


def boxscore_rows_html(
    left_rows: list[dict[str, object]],
    right_rows: list[dict[str, object]],
    left_team: str,
    right_team: str,
    week: int,
    include_total: bool = True,
    show_projections: bool = True,
    show_stats: bool = True,
) -> str:
    row_count = max(len(left_rows), len(right_rows))
    rows = []
    left_total = 0.0
    right_total = 0.0

    for index in range(row_count):
        left = left_rows[index] if index < len(left_rows) else {"player": "", "slot": "", "color": "#e5e7eb"}
        right = right_rows[index] if index < len(right_rows) else {"player": "", "slot": "", "color": "#e5e7eb"}
        slot = clean_text(left.get("slot")) or clean_text(right.get("slot"))
        color = clean_text(left.get("color"), clean_text(right.get("color"), "#e5e7eb"))
        left_player = clean_text(left.get("player"))
        right_player = clean_text(right.get("player"))
        left_actual = pd.to_numeric(left.get("points"), errors="coerce")
        right_actual = pd.to_numeric(right.get("points"), errors="coerce")
        left_points = (
            float(left_actual)
            if not pd.isna(left_actual)
            else boxscore_points(left_team, week, left_player, slot)
            if left_player and left_player != "TBD"
            else 0.0
        )
        right_points = (
            float(right_actual)
            if not pd.isna(right_actual)
            else boxscore_points(right_team, week, right_player, slot)
            if right_player and right_player != "TBD"
            else 0.0
        )
        left_projection = (
            boxscore_projection(left_team, week, left_player, slot)
            if show_projections and left_player and left_player != "TBD"
            else None
        )
        right_projection = (
            boxscore_projection(right_team, week, right_player, slot)
            if show_projections and right_player and right_player != "TBD"
            else None
        )
        left_stats = player_stat_pills(left_team, week, left_player, slot) if show_stats else ""
        right_stats = player_stat_pills(right_team, week, right_player, slot) if show_stats else ""
        left_total += left_points
        right_total += right_points
        left_player_html = (
            f"""
    <div class="boxscore-player-wrap">
      <img class="boxscore-headshot" src="{esc(player_picture(left_player))}" alt="{esc(left_player)}" onerror="{player_picture_fallback()}">
      <div>
        <div class="boxscore-player-name">{esc(left_player)}</div>
        {left_stats}
      </div>
    </div>
"""
            if left_player
            else ""
        )
        right_player_html = (
            f"""
    <div class="boxscore-player-wrap">
      <div>
        <div class="boxscore-player-name">{esc(right_player)}</div>
        {right_stats}
      </div>
      <img class="boxscore-headshot" src="{esc(player_picture(right_player))}" alt="{esc(right_player)}" onerror="{player_picture_fallback()}">
    </div>
"""
            if right_player
            else ""
        )
        left_points_html = (
            f'{left_points:.2f}'
            f'{f"""<br><span class="boxscore-proj">{left_projection:.1f}</span>""" if left_projection is not None else ""}'
            if left_player
            else ""
        )
        right_points_html = (
            f'{right_points:.2f}'
            f'{f"""<br><span class="boxscore-proj">{right_projection:.1f}</span>""" if right_projection is not None else ""}'
            if right_player
            else ""
        )
        rows.append(
            f"""
<tr>
  <td class="boxscore-player-left">{left_player_html}</td>
  <td class="boxscore-points">{left_points_html}</td>
  <td class="boxscore-slot"><span class="slot-pill" style="background:{esc(color)};">{esc(slot)}</span></td>
  <td class="boxscore-points">{right_points_html}</td>
  <td class="boxscore-player-right">{right_player_html}</td>
</tr>
"""
        )

    if include_total:
        rows.append(
            f"""
<tr class="boxscore-total">
  <td class="boxscore-player-left">Total</td>
  <td class="boxscore-points">{left_total:.2f}</td>
  <td class="boxscore-slot">Total</td>
  <td class="boxscore-points">{right_total:.2f}</td>
  <td class="boxscore-player-right">Total</td>
</tr>
"""
        )
    return "".join(rows)


@st.dialog("Box Score", width="large")
def render_box_score_dialog(
    game: dict[str, object],
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    rankings: Optional[pd.DataFrame],
    rosters: pd.DataFrame,
    starters: pd.DataFrame,
    bowls: Optional[pd.DataFrame] = None,
) -> None:
    week = int(game["Week"]) if not pd.isna(game.get("Week")) else 0
    year = int(game["Year"]) if not pd.isna(game.get("Year")) else 0
    show_projections = year > 2025
    team_a = clean_text(game.get("TeamA"))
    team_b = clean_text(game.get("TeamB"))
    bowl = bowl_for_notes(game.get("Notes"), bowls)
    rivalry = rivalry_name(game)
    teams = team_lookup(schools)
    ranks = schedule_ap_top25(rankings, week)
    team_a_color = clean_text(teams.get(team_a, {}).get("color"), "#1a2030")
    team_b_color = clean_text(teams.get(team_b, {}).get("color"), "#c8102e")
    win_probability = seeded_float(team_a, team_b, week, "win-probability", low=0.05, high=0.95)
    favorite = team_a if win_probability >= 0.5 else team_b
    favorite_probability = win_probability if favorite == team_a else 1 - win_probability
    label_pct = min(max(win_probability * 100, 14), 86)
    team_a_rows = team_boxscore_from_starters(starters, team_a, week)
    team_b_rows = team_boxscore_from_starters(starters, team_b, week)
    if not team_a_rows["Starters"]:
        team_a_rows = team_boxscore_players(rosters, team_a)
    if not team_b_rows["Starters"]:
        team_b_rows = team_boxscore_players(rosters, team_b)
    team_a_total = boxscore_total(team_a_rows["Starters"], team_a, week)
    team_b_total = boxscore_total(team_b_rows["Starters"], team_b, week)
    record_week = max(week - 1, 0)
    team_a_record = team_record_through_week(schedule, scores, schools, team_a, record_week)
    team_b_record = team_record_through_week(schedule, scores, schools, team_b, record_week)

    sections = []
    for section_name, include_total in [
        ("Starters", True),
        ("Bench", False),
        ("Injured Reserve", False),
        ("Taxi", False),
    ]:
        left_section = team_a_rows.get(section_name, [])
        right_section = team_b_rows.get(section_name, [])
        if section_name != "Starters" and not left_section and not right_section:
            continue

        rows_html = boxscore_rows_html(
            left_section,
            right_section,
            team_a,
            team_b,
            week,
            include_total=include_total,
            show_projections=show_projections and section_name == "Starters",
            show_stats=section_name == "Starters",
        )
        sections.append(
            f"""
<div class="boxscore-section-title">{esc(section_name)}</div>
<table class="boxscore-table">
  <thead>
    <tr>
      <th>{esc(team_a)}</th>
      <th>Points</th>
      <th>Position</th>
      <th>Points</th>
      <th>{esc(team_b)}</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
"""
        )

    st.html(
        f"""
{render_boxscore_bowl_masthead(bowl, year, week)}
{render_boxscore_rivalry_masthead(rivalry, compact=bool(bowl))}
<div class="boxscore-matchup-card">
  <div class="boxscore-matchup-top">
    {boxscore_team_header(team_a, teams, ranks, team_a_record, "left")}
    <div class="boxscore-center">
      <div class="boxscore-week-label">Matchup</div>
      <div class="boxscore-week-number">W{week}</div>
      <div class="boxscore-vs">VS</div>
    </div>
    {boxscore_team_header(team_b, teams, ranks, team_b_record, "right")}
  </div>
  <div class="boxscore-score-row">
    <div class="boxscore-score-cell" style="--team-color:{esc(team_a_color)};">
      <div class="boxscore-score-label">Total Score</div>
    <div class="boxscore-score-value">{team_a_total:.2f}</div>
    </div>
    <div class="boxscore-score-mid"></div>
    <div class="boxscore-score-cell right" style="--team-color:{esc(team_b_color)};">
      <div class="boxscore-score-label">Total Score</div>
      <div class="boxscore-score-value">{team_b_total:.2f}</div>
    </div>
  </div>
</div>
{f'''<div class="win-prob" style="--left-color:{esc(team_a_color)}; --right-color:{esc(team_b_color)}; --left-pct:{win_probability * 100:.2f}%; --label-pct:{label_pct:.2f}%;">
  <div class="win-prob-marker"></div>
  <div class="win-prob-label">{esc(favorite)} {favorite_probability * 100:.0f}% to win</div>
</div>''' if show_projections else ''}
{''.join(sections)}
"""
    )


@loading_spinner("Loading schedule and matchup details...")
def render_schedule_cards(
    games: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    rankings: Optional[pd.DataFrame] = None,
    rosters: Optional[pd.DataFrame] = None,
    starters: Optional[pd.DataFrame] = None,
    bowls: Optional[pd.DataFrame] = None,
    schedule_context: Optional[pd.DataFrame] = None,
    empty_label: str = "No games found",
    stacked: bool = False,
    sort_by_rank: bool = True,
    key_prefix: str = "schedule",
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
    full_schedule = schedule_context if schedule_context is not None else games
    safe_starters = starters if starters is not None else pd.DataFrame()
    starter_scores_by_team_week = starter_score_lookup(safe_starters)
    games = games.copy()
    games["_team_b_sort"] = games["TeamB"].map(lambda value: clean_text(value).casefold())
    games["_team_a_sort"] = games["TeamA"].map(lambda value: clean_text(value).casefold())
    games["_week_sort"] = pd.to_numeric(games["Week"], errors="coerce").fillna(0)
    if sort_by_rank:
        games["_rank_sort"] = games.apply(lambda row: schedule_game_rank_sort(row, rankings), axis=1)
        games = games.sort_values(
            ["_rank_sort", "_team_b_sort", "_team_a_sort", "_week_sort"],
            na_position="last",
        )
    else:
        games = games.sort_values(
            ["_week_sort", "_team_b_sort", "_team_a_sort"],
            na_position="last",
        )

    rendered_games = list(games.iterrows())
    if stacked:
        card_slots = [st.container() for _ in rendered_games]
    else:
        card_slots = []
        for start in range(0, len(rendered_games), 3):
            columns = st.columns(3)
            card_slots.extend(columns[: len(rendered_games) - start])

    safe_rosters = rosters if rosters is not None else pd.DataFrame()
    for game_number, (slot_container, (game_index, game)) in enumerate(zip(card_slots, rendered_games)):
        week = int(game["Week"]) if not pd.isna(game.get("Week")) else 0
        team_a = clean_text(game.get("TeamA"))
        team_b = clean_text(game.get("TeamB"))
        notes = clean_text(game.get("Notes"))
        bowl = bowl_for_notes(notes, bowls)
        rivalry = rivalry_name(game)
        is_conference = bool(game.get("Conference", False))
        score_a = starter_scores_by_team_week.get((match_key(team_a), week))
        score_b = starter_scores_by_team_week.get((match_key(team_b), week))
        if score_a is None:
            score_a = scores_by_team_week.get((match_key(team_a), week))
        if score_b is None:
            score_b = scores_by_team_week.get((match_key(team_b), week))
        badge = "Bowl Game" if bowl else ("Rivalry" if rivalry else ("Conference" if is_conference else "Non-Conf"))
        game_ranks = schedule_ap_top25(rankings, week)
        record_week = max(week - 1, 0)
        team_a_record = team_record_through_week(full_schedule, scores, schools, team_a, record_week)
        team_b_record = team_record_through_week(full_schedule, scores, schools, team_b, record_week)

        with slot_container:
            st.html(
                f"""
<div class="schedule-card{' bowl-game' if bowl else ''}{' rivalry-game' if rivalry else ''}">
  <div class="schedule-card-top">
    <div class="week-chip">Week {week}</div>
    <div class="game-badge">{badge}</div>
  </div>
  {render_bowl_banner(bowl)}
  {f'<div class="schedule-rivalry-note">{render_rivalry_pill(rivalry)}</div>' if bowl and rivalry else render_rivalry_banner(rivalry)}
  {render_matchup_team(team_a, week, score_a, score_b, teams, game_ranks, team_a_record)}
  {render_matchup_team(team_b, week, score_b, score_a, teams, game_ranks, team_b_record)}
  {f'<div class="schedule-notes">{esc(notes)}</div>' if notes and match_key(notes) != match_key(bowl.get("name")) else ''}
</div>
"""
            )
            _, button_col = st.columns([0.66, 0.34])
            with button_col:
                if st.button(
                    "View Box Score",
                    key=(
                        f"{key_prefix}_box_score_{week}_{game_index}_{game_number}_"
                        f"{match_key(team_a)}_{match_key(team_b)}"
                    ),
                    use_container_width=True,
                ):
                    render_box_score_dialog(
                        game.to_dict(),
                        full_schedule,
                        scores,
                        schools,
                        rankings,
                        safe_rosters,
                        safe_starters,
                        bowls,
                    )
            st.html('<div class="schedule-card-divider"></div>')


def schedule_weeks(schedule: pd.DataFrame) -> list[int]:
    if schedule.empty or "Week" not in schedule.columns:
        return []
    return sorted(
        int(week)
        for week in schedule["Week"].dropna().unique()
        if int(week) > 0
    )


def ranking_weeks(rankings: pd.DataFrame) -> list[int]:
    if rankings.empty or "Week" not in rankings.columns:
        return []
    return sorted(
        int(week)
        for week in rankings["Week"].dropna().unique()
        if int(week) >= 0
    )


def week_label(week: int) -> str:
    return f"Week {week}"


@st.cache_data(show_spinner="Filtering season data...", max_entries=32)
def filter_by_season(df: pd.DataFrame, season: int) -> pd.DataFrame:
    if df.empty or "Year" not in df.columns:
        return df.copy()
    return df.loc[pd.to_numeric(df["Year"], errors="coerce").eq(season)].copy()


@st.cache_data(show_spinner="Aggregating weekly scores...", max_entries=16)
def aggregate_scores_from_starters(
    starters: pd.DataFrame,
    fallback_scores: pd.DataFrame,
    cache_version: str = STANDINGS_CACHE_VERSION,
) -> pd.DataFrame:
    del cache_version
    if starters.empty or not {"Team", "Week", "Points"}.issubset(starters.columns):
        return fallback_scores.copy()

    starter_scores = starters.copy()
    starter_scores["Points"] = pd.to_numeric(starter_scores["Points"], errors="coerce")
    if "TeamPoints" in starter_scores.columns:
        starter_scores["TeamPoints"] = pd.to_numeric(starter_scores["TeamPoints"], errors="coerce")
    starter_scores["Week"] = pd.to_numeric(starter_scores["Week"], errors="coerce")
    starter_scores = starter_scores.dropna(subset=["Team", "Week"])
    if starter_scores.empty:
        return fallback_scores.copy()

    group_columns = ["Team", "Week"]
    if "Year" in starter_scores.columns:
        group_columns.insert(0, "Year")

    if "TeamPoints" in starter_scores.columns and pd.to_numeric(starter_scores["TeamPoints"], errors="coerce").notna().any():
        starter_scores["TeamPoints"] = pd.to_numeric(starter_scores["TeamPoints"], errors="coerce")
        scores = (
            starter_scores.dropna(subset=["TeamPoints"])
            .groupby(group_columns, dropna=False)["TeamPoints"]
            .first()
            .reset_index()
            .rename(columns={"TeamPoints": "Points"})
        )
    else:
        if "RosterSpot" in starter_scores.columns and starter_scores["RosterSpot"].notna().any():
            starter_scores = starter_scores.loc[
                starter_scores["RosterSpot"].astype(str).eq("Starter")
            ].copy()
        scores = (
            starter_scores.groupby(group_columns, dropna=False)["Points"]
            .sum(min_count=1)
            .reset_index()
        )
    scores = scores.dropna(subset=["Points"]).copy()
    scores = scores.loc[pd.to_numeric(scores["Points"], errors="coerce").fillna(0).ne(0)]
    return scores.reset_index(drop=True)


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


@loading_spinner("Building conference schedule matrix...")
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
            rivalry = rivalry_name(game_row)
            if rivalry:
                content = f'{content}<span class="schedule-matrix-rivalry">{esc(rivalry)}</span>'

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


def pct(wins: float, losses: float, ties: float) -> float:
    games = wins + losses + ties
    if games == 0:
        return 0.0
    return (wins + (0.5 * ties)) / games


def format_pct(value: float) -> str:
    return f"{value:.3f}".lstrip("0")


def rank_label(rank: object) -> str:
    if pd.isna(rank):
        return "-"
    return f"#{int(rank)}"


def record_html(wins: int, losses: int, ties: int, win_pct: float) -> str:
    record = f"{wins}-{losses}" if ties == 0 else f"{wins}-{losses}-{ties}"
    return f"""
<div class="record-main">{record}</div>
<div class="record-sub">{format_pct(win_pct)}</div>
"""


def record_text(wins: int, losses: int, ties: int) -> str:
    return f"{wins}-{losses}" if ties == 0 else f"{wins}-{losses}-{ties}"


def metric_html(value: float, rank: object) -> str:
    return f"""
<div class="metric-main">{value:,.2f}</div>
<div class="metric-rank">{rank_label(rank)}</div>
"""


def empty_standing(team: str, info: dict[str, str]) -> dict[str, object]:
    return {
        "team": team,
        "conference": clean_text(info.get("conference")),
        "nickname": clean_text(info.get("nickname")),
        "owner": clean_text(info.get("owner")),
        "logo": clean_text(info.get("logo")),
        "color": clean_text(info.get("color"), "#1a2030"),
        "league_wins": 0,
        "league_losses": 0,
        "league_ties": 0,
        "league_pf": 0.0,
        "league_pa": 0.0,
        "conf_wins": 0,
        "conf_losses": 0,
        "conf_ties": 0,
        "conf_pf": 0.0,
        "conf_pa": 0.0,
    }


def apply_game_result(row: dict[str, object], points: float, opponent_points: float, prefix: str) -> None:
    row[f"{prefix}_pf"] += points
    row[f"{prefix}_pa"] += opponent_points
    if points > opponent_points:
        row[f"{prefix}_wins"] += 1
    elif points < opponent_points:
        row[f"{prefix}_losses"] += 1
    else:
        row[f"{prefix}_ties"] += 1


def is_completed_score(score_a: Optional[float], score_b: Optional[float]) -> bool:
    if score_a is None or score_b is None:
        return False
    if pd.isna(score_a) or pd.isna(score_b):
        return False
    return float(score_a) != 0 or float(score_b) != 0


@st.cache_data(show_spinner="Building league standings...", max_entries=32)
def build_standings(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    cache_version: str = STANDINGS_CACHE_VERSION,
) -> pd.DataFrame:
    del cache_version
    teams = team_lookup(schools)
    standings = {
        team: empty_standing(team, info)
        for team, info in teams.items()
    }
    scores_by_team_week = score_lookup(scores)

    for _, game in schedule.iterrows():
        week = game.get("Week")
        if pd.isna(week) or int(week) <= 0:
            continue

        week = int(week)
        team_a = clean_text(game.get("TeamA"))
        team_b = clean_text(game.get("TeamB"))
        if not team_a or not team_b:
            continue

        score_a = scores_by_team_week.get((match_key(team_a), week))
        score_b = scores_by_team_week.get((match_key(team_b), week))
        if not is_completed_score(score_a, score_b):
            continue

        if team_a not in standings:
            standings[team_a] = empty_standing(team_a, {})
        if team_b not in standings:
            standings[team_b] = empty_standing(team_b, {})

        is_conference = bool(game.get("Conference", False))
        apply_game_result(standings[team_a], score_a, score_b, "league")
        apply_game_result(standings[team_b], score_b, score_a, "league")
        if is_conference:
            apply_game_result(standings[team_a], score_a, score_b, "conf")
            apply_game_result(standings[team_b], score_b, score_a, "conf")

    df = pd.DataFrame(standings.values())
    for prefix in ("league", "conf"):
        df[f"{prefix}_games"] = df[f"{prefix}_wins"] + df[f"{prefix}_losses"] + df[f"{prefix}_ties"]
        df[f"{prefix}_win_pct"] = df.apply(
            lambda row: pct(row[f"{prefix}_wins"], row[f"{prefix}_losses"], row[f"{prefix}_ties"]),
            axis=1,
        )
        df[f"{prefix}_pd"] = df[f"{prefix}_pf"] - df[f"{prefix}_pa"]
    return df


def h2h_score(
    team: str,
    tied_teams: set[str],
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    conference_only: bool = False,
) -> float:
    scores_by_team_week = score_lookup(scores)
    wins = losses = ties = 0

    for _, game in schedule.iterrows():
        if conference_only and not bool(game.get("Conference", False)):
            continue

        week = game.get("Week")
        if pd.isna(week) or int(week) <= 0:
            continue

        team_a = clean_text(game.get("TeamA"))
        team_b = clean_text(game.get("TeamB"))
        if team not in {team_a, team_b} or team_a not in tied_teams or team_b not in tied_teams:
            continue

        week = int(week)
        score_a = scores_by_team_week.get((match_key(team_a), week))
        score_b = scores_by_team_week.get((match_key(team_b), week))
        if not is_completed_score(score_a, score_b):
            continue

        team_score = score_a if team == team_a else score_b
        opponent_score = score_b if team == team_a else score_a
        if team_score > opponent_score:
            wins += 1
        elif team_score < opponent_score:
            losses += 1
        else:
            ties += 1

    return pct(wins, losses, ties)


def sort_standings(
    df: pd.DataFrame,
    prefix: str = "league",
    points_prefix: Optional[str] = None,
    schedule: Optional[pd.DataFrame] = None,
    scores: Optional[pd.DataFrame] = None,
    use_h2h: bool = False,
) -> pd.DataFrame:
    df = df.copy()
    pct_col = f"{prefix}_win_pct"
    points_prefix = points_prefix or prefix
    pf_col = f"{points_prefix}_pf"
    sort_cols = [pct_col, pf_col, "team"]
    ascending = [False, False, True]

    if use_h2h and schedule is not None and scores is not None:
        df["h2h_score"] = 0.0
        for _, tied_group in df.groupby(pct_col):
            if len(tied_group) <= 1:
                continue
            tied_teams = set(tied_group["team"])
            for index, row in tied_group.iterrows():
                df.loc[index, "h2h_score"] = h2h_score(
                    row["team"],
                    tied_teams,
                    schedule,
                    scores,
                    conference_only=prefix == "conf",
                )
        sort_cols = [pct_col, "h2h_score", pf_col, "team"]
        ascending = [False, False, False, True]

    return df.sort_values(
        sort_cols,
        ascending=ascending,
    ).reset_index(drop=True)


def render_standings_section(
    standings: pd.DataFrame,
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    conferences: pd.DataFrame,
    conference: str,
    ap_ranks: Optional[dict[str, int]] = None,
    sort_prefix: str = "league",
    show_championship_cut: bool = False,
    show_conference_title: bool = True,
) -> None:
    section = standings.loc[standings["conference"].eq(conference)].copy()
    if section.empty:
        under_construction(f"{conference} Standings")
        return

    section = sort_standings(
        section,
        prefix=sort_prefix,
        points_prefix="league" if sort_prefix == "conf" else sort_prefix,
        schedule=schedule,
        scores=scores,
        use_h2h=sort_prefix == "conf",
    )
    active_conf = section["conf_games"] > 0
    section["conf_pf_rank"] = pd.NA
    section["conf_pa_rank"] = pd.NA
    section.loc[active_conf, "conf_pf_rank"] = section.loc[active_conf, "conf_pf"].rank(
        ascending=False,
        method="min",
    )
    section.loc[active_conf, "conf_pa_rank"] = section.loc[active_conf, "conf_pa"].rank(
        ascending=True,
        method="min",
    )
    conf_logo = conference_logo(conferences, conference)

    rows = []
    for index, row in section.iterrows():
        logo = clean_text(row.get("logo"))
        logo_html = f'<img src="{esc(logo)}" alt="{esc(row["team"])}">' if logo else ""
        championship_row = show_championship_cut and section["conf_games"].sum() > 0 and index < 2
        display_name = f"{rank_prefix(row['team'], ap_ranks)}{clean_text(row['team'])}"
        rows.append(
            f"""
<tr class="{'championship-row' if championship_row else ''}">
  <td class="standings-team-cell" style="--team-color:{esc(row.get("color"), "#1a2030")};">
    <div class="standings-team">
      <span class="standings-rank">{index + 1}</span>
      {logo_html}
      <div>
        <div class="standings-team-name">{esc(display_name)}</div>
        <div class="standings-team-sub">{esc(nickname_owner(row.get("nickname"), row.get("owner")))}</div>
      </div>
    </div>
  </td>
  <td>{record_html(int(row["league_wins"]), int(row["league_losses"]), int(row["league_ties"]), float(row["league_win_pct"]))}</td>
  <td>{metric_html(float(row["league_pf"]), row["league_pf_rank"])}</td>
  <td>{metric_html(float(row["league_pa"]), row["league_pa_rank"])}</td>
  <td>{record_html(int(row["conf_wins"]), int(row["conf_losses"]), int(row["conf_ties"]), float(row["conf_win_pct"]))}</td>
  <td>{metric_html(float(row["conf_pf"]), row["conf_pf_rank"])}</td>
  <td>{metric_html(float(row["conf_pa"]), row["conf_pa_rank"])}</td>
</tr>
"""
        )

    st.html(
        f"""
<div class="standings-wrap">
  {f'''<div class="standings-title">
    {'<img src="' + esc(conf_logo) + '" alt="' + esc(conference) + '">' if conf_logo else ''}
    <span>{esc(conference)}</span>
    <div></div>
  </div>''' if show_conference_title else ''}
  <div class="standings-scroll">
    <table class="standings-table">
      <colgroup>
        <col class="standings-team-column">
        <col span="6">
      </colgroup>
      <thead>
        <tr>
          <th class="team-col">Team</th>
          <th>League Record</th>
          <th>Points For</th>
          <th>Points Against</th>
          <th>Conf Record</th>
          <th>Conf Points For</th>
          <th>Conf Points Against</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</div>
"""
    )


@loading_spinner("Loading league standings...")
def render_league_standings(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    conferences: pd.DataFrame,
    rankings: Optional[pd.DataFrame] = None,
) -> None:
    standings = build_standings(schedule, scores, schools)
    ap_ranks = latest_ap_top25(rankings)
    for prefix in ("league", "conf"):
        active = standings[f"{prefix}_games"] > 0
        standings[f"{prefix}_pf_rank"] = pd.NA
        standings[f"{prefix}_pa_rank"] = pd.NA
        standings.loc[active, f"{prefix}_pf_rank"] = standings.loc[active, f"{prefix}_pf"].rank(ascending=False, method="min")
        standings.loc[active, f"{prefix}_pa_rank"] = standings.loc[active, f"{prefix}_pa"].rank(ascending=True, method="min")

    season_has_real_scores = (standings["league_pf"] + standings["league_pa"]).sum() > 0
    for conference in LEAGUE_ROSTER_ORDER:
        conference_rows = standings.loc[standings["conference"].eq(conference)]
        if season_has_real_scores and conference_rows["league_games"].sum() == 0:
            continue
        render_standings_section(
            standings,
            schedule,
            scores,
            conferences,
            conference,
            ap_ranks=ap_ranks,
            sort_prefix="league",
            show_championship_cut=False,
        )


@loading_spinner("Loading conference standings...")
def render_conference_standings(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    conferences: pd.DataFrame,
    rankings: Optional[pd.DataFrame],
    conference: str,
) -> None:
    standings = build_standings(schedule, scores, schools)
    ap_ranks = latest_ap_top25(rankings)
    for prefix in ("league", "conf"):
        active = standings[f"{prefix}_games"] > 0
        standings[f"{prefix}_pf_rank"] = pd.NA
        standings[f"{prefix}_pa_rank"] = pd.NA
        standings.loc[active, f"{prefix}_pf_rank"] = standings.loc[active, f"{prefix}_pf"].rank(ascending=False, method="min")
        standings.loc[active, f"{prefix}_pa_rank"] = standings.loc[active, f"{prefix}_pa"].rank(ascending=True, method="min")

    render_standings_section(
        standings,
        schedule,
        scores,
        conferences,
        conference,
        ap_ranks=ap_ranks,
        sort_prefix="conf",
        show_championship_cut=True,
        show_conference_title=False,
    )


def team_record_text(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    team_name: str,
    rankings: Optional[pd.DataFrame] = None,
) -> str:
    standings = build_standings(schedule, scores, schools)
    team = standings.loc[standings["team"].eq(team_name)]
    if team.empty:
        return ""

    row = team.iloc[0]
    overall = record_text(
        int(row["league_wins"]),
        int(row["league_losses"]),
        int(row["league_ties"]),
    )
    conference = record_text(
        int(row["conf_wins"]),
        int(row["conf_losses"]),
        int(row["conf_ties"]),
    )
    return f"{rank_prefix(team_name, latest_ap_top25(rankings))}{overall} ({conference})"


def team_record_through_week(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    team_name: str,
    week: int,
) -> str:
    schedule_part, scores_part = through_week(schedule, scores, week)
    standings = build_standings(schedule_part, scores_part, schools)
    team = standings.loc[standings["team"].eq(team_name)]
    if team.empty:
        return ""

    row = team.iloc[0]
    overall = record_text(
        int(row["league_wins"]),
        int(row["league_losses"]),
        int(row["league_ties"]),
    )
    conference = record_text(
        int(row["conf_wins"]),
        int(row["conf_losses"]),
        int(row["conf_ties"]),
    )
    return f"{overall} ({conference})"


@st.cache_data(show_spinner="Building historical results...", max_entries=8)
def build_history_ledger(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    rankings: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "Year", "Week", "Team", "Opponent", "Conference", "OpponentConference",
        "Points", "OpponentPoints", "Margin", "Result", "ConferenceGame",
        "OpponentRank", "Notes", "Rivalry",
    ]
    if schedule.empty or scores.empty:
        return pd.DataFrame(columns=columns)

    teams = team_lookup(schools)
    resolver = official_team_resolver(schools)
    score_map = {}
    for _, row in scores.iterrows():
        year = pd.to_numeric(row.get("Year"), errors="coerce")
        week = pd.to_numeric(row.get("Week"), errors="coerce")
        points = pd.to_numeric(row.get("Points"), errors="coerce")
        team = official_team_name(row.get("Team"), resolver)
        if team and not pd.isna(year) and not pd.isna(week) and not pd.isna(points):
            score_map[(int(year), int(week), match_key(team))] = float(points)

    rank_map_by_week = {}
    if not rankings.empty:
        ap = rankings.loc[rankings["Type"].astype(str).eq("AP Poll")].copy()
        for _, row in ap.iterrows():
            year = pd.to_numeric(row.get("Year"), errors="coerce")
            week = pd.to_numeric(row.get("Week"), errors="coerce")
            rank = pd.to_numeric(row.get("Rank"), errors="coerce")
            team = official_team_name(row.get("Team"), resolver)
            if team and not pd.isna(year) and not pd.isna(week) and not pd.isna(rank):
                rank_map_by_week[(int(year), int(week), match_key(team))] = int(rank)

    rows = []
    for _, game in schedule.iterrows():
        year = pd.to_numeric(game.get("Year"), errors="coerce")
        week = pd.to_numeric(game.get("Week"), errors="coerce")
        team_a = official_team_name(game.get("TeamA"), resolver)
        team_b = official_team_name(game.get("TeamB"), resolver)
        if pd.isna(year) or pd.isna(week) or not team_a or not team_b:
            continue
        year, week = int(year), int(week)
        score_a = score_map.get((year, week, match_key(team_a)))
        score_b = score_map.get((year, week, match_key(team_b)))
        if score_a is None or score_b is None:
            continue
        for team, opponent, points, opponent_points in [
            (team_a, team_b, score_a, score_b),
            (team_b, team_a, score_b, score_a),
        ]:
            opponent_rank = rank_map_by_week.get(
                (year, max(week - 1, 0), match_key(opponent))
            )
            if opponent_rank is None:
                opponent_rank = rank_map_by_week.get((year, week, match_key(opponent)))
            rows.append(
                {
                    "Year": year,
                    "Week": week,
                    "Team": team,
                    "Opponent": opponent,
                    "Conference": clean_text(teams.get(team, {}).get("conference")),
                    "OpponentConference": clean_text(teams.get(opponent, {}).get("conference")),
                    "Points": points,
                    "OpponentPoints": opponent_points,
                    "Margin": points - opponent_points,
                    "Result": "W" if points > opponent_points else "L" if points < opponent_points else "T",
                    "ConferenceGame": bool(game.get("Conference", False)),
                    "OpponentRank": opponent_rank,
                    "Notes": clean_text(game.get("Notes")),
                    "Rivalry": rivalry_name(game),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def conference_championship_mask(ledger: pd.DataFrame) -> pd.Series:
    return ledger["Notes"].map(match_key).str.contains(
        r"\bconf(?:erence)?\s+champ(?:ionship)?\s+bowl\b",
        regex=True,
        na=False,
    )


def national_championship_mask(ledger: pd.DataFrame) -> pd.Series:
    return ledger["Notes"].map(match_key).str.contains(
        r"\bnational\s+championship\s+bowl\b",
        regex=True,
        na=False,
    )


def national_postseason_mask(ledger: pd.DataFrame) -> pd.Series:
    return ledger["Notes"].map(match_key).str.contains(
        r"\bnational\s+(?:semifinal|championship)\s+bowl\b",
        regex=True,
        na=False,
    )


def history_aggregate(ledger: pd.DataFrame, schools: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    rows = []
    team_names = set(ledger["Team"]) if not ledger.empty else set()
    if schools is not None and not schools.empty:
        team_names.update(schools["School"].dropna().map(clean_text))
    teams = team_lookup(schools) if schools is not None else {}
    for team in sorted(name for name in team_names if name):
        games = ledger.loc[ledger["Team"].eq(team)].copy()
        wins = int(games["Result"].eq("W").sum())
        losses = int(games["Result"].eq("L").sum())
        ties = int(games["Result"].eq("T").sum())
        ranked = games.loc[games["OpponentRank"].between(1, 25, inclusive="both")]
        conf = games.loc[games["ConferenceGame"]]
        conference_titles = games.loc[
            conference_championship_mask(games) & games["Result"].eq("W")
        ]
        national_titles = games.loc[
            national_championship_mask(games) & games["Result"].eq("W")
        ]
        bowls = games.loc[
            games["Notes"].str.contains("bowl", case=False, na=False)
            & ~conference_championship_mask(games)
        ]
        rows.append(
            {
                "Team": team,
                "Conference": first_value(games, "Conference", clean_text(teams.get(team, {}).get("conference"))),
                "Seasons": games["Year"].nunique(),
                "Wins": wins,
                "Losses": losses,
                "Ties": ties,
                "ConfWins": int(conf["Result"].eq("W").sum()),
                "ConfLosses": int(conf["Result"].eq("L").sum()),
                "ConfTies": int(conf["Result"].eq("T").sum()),
                "WinPct": pct(wins, losses, ties),
                "ConfWinPct": pct(
                    int(conf["Result"].eq("W").sum()),
                    int(conf["Result"].eq("L").sum()),
                    int(conf["Result"].eq("T").sum()),
                ),
                "PF": games["Points"].sum(),
                "PA": games["OpponentPoints"].sum(),
                "RankedWins": int(ranked["Result"].eq("W").sum()),
                "RankedGames": len(ranked),
                "BowlWins": int(bowls["Result"].eq("W").sum()),
                "BowlLosses": int(bowls["Result"].eq("L").sum()),
                "BowlTies": int(bowls["Result"].eq("T").sum()),
                "ConferenceChampionshipYears": ", ".join(
                    str(year)
                    for year in sorted(
                        conference_titles["Year"].dropna().astype(int).unique()
                    )
                ),
                "NationalChampionshipYears": ", ".join(
                    str(year)
                    for year in sorted(
                        national_titles["Year"].dropna().astype(int).unique()
                    )
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["Wins", "WinPct", "PF", "Team"], ascending=[False, False, False, True]
    ).reset_index(drop=True)


def history_hero(title: str, subtitle: str, logo: str = "", accent: str = "#f2cf68") -> None:
    st.html(
        f"""
<div class="history-hero" style="--accent:{esc(accent)};">
  <div>
    <div class="history-kicker">Historical Archive</div>
    <div class="history-title">{esc(title)}</div>
    <div class="history-sub">{esc(subtitle)}</div>
  </div>
  {f'<img class="history-hero-logo" src="{esc(logo)}" alt="{esc(title)}">' if logo else ''}
</div>
"""
    )


def history_metrics(items: list[tuple[str, str]], accent: str = "#c8102e") -> None:
    cards = "".join(
        f'<div class="history-metric" style="--accent:{esc(accent)};"><div class="history-metric-value">{esc(value)}</div><div class="history-metric-label">{esc(label)}</div></div>'
        for value, label in items
    )
    st.html(f'<div class="history-metrics" style="--metric-count:{len(items)};">{cards}</div>')


def player_value_metrics(
    dynasty: dict[str, object],
    last_finish: str,
    current_rank: str,
) -> None:
    items = [
        (
            f'{float(dynasty["one_qb"]):,.0f} · {dynasty["one_qb_rank"]} · {dynasty["one_qb_overall"]}',
            "Current Flex Value",
        ),
        (
            f'{float(dynasty["superflex"]):,.0f} · {dynasty["superflex_rank"]} · {dynasty["superflex_overall"]}',
            "Current Superflex Value",
        ),
        (last_finish, "Last Season Finish"),
        (current_rank, "This Season Rank"),
    ]
    cards = "".join(
        f"""
<div class="history-metric" style="--accent:#7dd3fc;">
  <div class="player-value-main">{esc(value)}</div>
  <div class="history-metric-label">{esc(label)}</div>
</div>
"""
        for value, label in items
    )
    st.html(f'<div class="history-metrics" style="--metric-count:4;">{cards}</div>')


def history_program_table(aggregate: pd.DataFrame, schools: pd.DataFrame, limit: Optional[int] = None) -> None:
    if aggregate.empty:
        return
    teams = team_lookup(schools)
    rows = []
    for index, row in aggregate.head(limit).iterrows():
        info = teams.get(clean_text(row["Team"]), {})
        logo = clean_text(info.get("logo"))
        nickname = clean_text(info.get("nickname"))
        ranked_record = f'{int(row["RankedWins"])}-{int(row["RankedGames"] - row["RankedWins"])}'
        bowl_record = record_text(int(row["BowlWins"]), int(row["BowlLosses"]), int(row["BowlTies"]))
        rows.append(
            f"""
<tr>
  <td><div class="standings-team"><span class="standings-rank">{index + 1}</span>{f'<img src="{esc(logo)}" alt="{esc(row["Team"])}">' if logo else ''}<div><div class="standings-team-name">{esc(row["Team"])}</div><div class="standings-team-sub">{esc(nickname)}</div></div></div></td>
  <td>{record_html(int(row["Wins"]), int(row["Losses"]), int(row["Ties"]), float(row["WinPct"]))}</td>
  <td>{record_html(int(row["ConfWins"]), int(row["ConfLosses"]), int(row["ConfTies"]), float(row["ConfWinPct"]))}</td>
  <td>{float(row["PF"]):,.2f}</td><td>{float(row["PA"]):,.2f}</td><td>{ranked_record}</td><td>{bowl_record}</td>
  <td>{esc(row["ConferenceChampionshipYears"], "-")}</td><td>{esc(row["NationalChampionshipYears"], "-")}</td>
</tr>
"""
        )
    st.html(
        f"""
<div class="history-section-title"><span>All-Time Programs</span><div></div></div>
<div class="history-table-wrap"><table class="history-table">
<thead><tr><th>Program</th><th>Record</th><th>Conf Record</th><th>Points For</th><th>Points Against</th><th>vs Top 25</th><th>Bowl Record</th><th>Conf Championships</th><th>National Championships</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
"""
    )


def history_signature_wins(ledger: pd.DataFrame, schools: pd.DataFrame, title: str = "Signature Wins") -> None:
    wins = ledger.loc[
        ledger["Result"].eq("W") & ledger["OpponentRank"].between(1, 25, inclusive="both")
    ].sort_values(["OpponentRank", "Margin", "Year"], ascending=[True, False, False]).head(12)
    if wins.empty:
        return
    teams = team_lookup(schools)
    cards = []
    for _, game in wins.iterrows():
        team = clean_text(game["Team"])
        info = teams.get(team, {})
        logo = clean_text(info.get("logo"))
        rivalry = clean_text(game.get("Rivalry"))
        cards.append(
            f"""
<div class="history-card" style="--accent:{esc(info.get("color"), "#1a2030")};">
  <div class="history-card-top"><div class="history-card-eyebrow">{int(game["Year"])} · Week {int(game["Week"])} · Beat No. {int(game["OpponentRank"])}</div>{f'<img src="{esc(logo)}" alt="{esc(team)}">' if logo else ''}</div>
  <div class="history-card-score">{esc(team)}</div>
  <div class="history-card-detail">{float(game["Points"]):.2f}-{float(game["OpponentPoints"]):.2f} over {esc(game["Opponent"])}</div>
  {f'<div class="history-rivalry-sub">{render_rivalry_pill(rivalry)}</div>' if rivalry else ''}
</div>
"""
        )
    st.html(
        f'<div class="history-section-title"><span>{esc(title)}</span><div></div></div><div class="history-card-grid">{"".join(cards)}</div>'
    )


def historical_owner(schools: pd.DataFrame, team: str, year: int) -> str:
    row = schools.loc[schools["School"].astype(str).eq(team)]
    if row.empty:
        return ""
    target = f"{year}owner"
    column = next(
        (column for column in schools.columns if "".join(char for char in str(column).casefold() if char.isalnum()) == target),
        None,
    )
    return clean_text(row.iloc[0].get(column)) if column else ""


def record_book_score_html(game: pd.Series, label: str) -> str:
    points = float(game["Points"])
    opponent_points = float(game["OpponentPoints"])
    if "Combined Points" in label:
        detail = points + opponent_points
    elif "Victory" in label or "Defeat" in label:
        detail = abs(points - opponent_points)
    else:
        detail = None

    subtext = (
        f'<div class="record-sub">{detail:,.2f}</div>'
        if detail is not None
        else ""
    )
    return f'<div class="record-book-score">{points:,.2f}-{opponent_points:,.2f}{subtext}</div>'


def history_record_book(ledger: pd.DataFrame, schools: pd.DataFrame, title: str = "Record Book") -> None:
    if ledger.empty:
        return
    winners = ledger.loc[ledger["Result"].eq("W")]
    losses = ledger.loc[ledger["Result"].eq("L")]
    candidates = [
        ("Highest Score", lambda games: games.sort_values("Points", ascending=False).head(1)),
        ("Lowest Score", lambda games: games.sort_values("Points").head(1)),
        ("Highest Score in Loss", lambda games: games.loc[games["Result"].eq("L")].sort_values("Points", ascending=False).head(1)),
        ("Lowest Score in Win", lambda games: games.loc[games["Result"].eq("W")].sort_values("Points").head(1)),
        ("Largest Victory", lambda games: games.loc[games["Result"].eq("W")].sort_values("Margin", ascending=False).head(1)),
        ("Closest Victory", lambda games: games.loc[games["Result"].eq("W")].sort_values("Margin").head(1)),
        ("Most Combined Points", lambda games: games.assign(Combined=games["Points"] + games["OpponentPoints"]).sort_values("Combined", ascending=False).head(1)),
        ("Least Combined Points", lambda games: games.assign(Combined=games["Points"] + games["OpponentPoints"]).sort_values("Combined").head(1)),
        ("Largest Defeat", lambda games: games.loc[games["Result"].eq("L")].sort_values("Margin").head(1)),
        ("Closest Defeat", lambda games: games.loc[games["Result"].eq("L")].sort_values("Margin", ascending=False).head(1)),
    ]
    rows = []
    teams = team_lookup(schools)
    team_specific = ledger["Team"].nunique() == 1
    if not team_specific:
        candidates = [
            candidate
            for candidate in candidates
            if candidate[0] not in {"Largest Defeat", "Closest Defeat"}
        ]
    sections = [("All-Time", ledger)]
    sections.extend(
        (f"{year} Season", ledger.loc[ledger["Year"].eq(year)])
        for year in sorted(ledger["Year"].dropna().astype(int).unique(), reverse=True)
    )
    for section_label, year_games in sections:
        column_count = 4 if team_specific else 5
        rows.append(f'<tr><th colspan="{column_count}" style="text-align:left;font-size:18px;color:#111827;background:#eef2f7;">{esc(section_label)}</th></tr>')
        for label, selector in candidates:
            frame = selector(year_games)
            if frame.empty:
                continue
            game = frame.iloc[0]
            team = clean_text(game["Team"])
            logo = clean_text(teams.get(team, {}).get("logo"))
            opponent = clean_text(game["Opponent"])
            opponent_logo = clean_text(teams.get(opponent, {}).get("logo"))
            score_html = record_book_score_html(game, label)
            game_period = (
                f'{int(game["Year"])} · Week {int(game["Week"])}'
                if section_label == "All-Time"
                else f'Week {int(game["Week"])}'
            )
            rows.append(
                f"""<tr><td>{esc(label)}</td>{f'<td><div class="history-team" style="justify-content:flex-end;">{f"""<div class="history-team-name">{esc(team)}</div><img src="{esc(logo)}" alt="{esc(team)}">""" if logo else f"""<div class="history-team-name">{esc(team)}</div>"""}</div></td>' if not team_specific else ''}<td>{score_html}</td><td><div class="history-team">{f'<img src="{esc(opponent_logo)}" alt="{esc(opponent)}">' if opponent_logo else ''}<div class="history-team-name">{esc(opponent)}</div></div></td><td>{esc(game_period)}</td></tr>"""
            )
    team_header = "" if team_specific else "<th>Team</th>"
    st.html(f'<div class="history-section-title"><span>{esc(title)}</span><div></div></div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Record</th>{team_header}<th>Score</th><th>Opponent</th><th>Week</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def history_champions(
    ledger: pd.DataFrame,
    schools: pd.DataFrame,
    bowls: pd.DataFrame,
    conference: str = "",
) -> None:
    source = ledger.copy()
    if conference:
        source = source.loc[source["Conference"].eq(conference)]
    source = source.drop_duplicates(["Year", "Week", "Team", "Opponent"])
    if source.empty:
        return
    teams = team_lookup(schools)
    sections = []
    conference_champions = source.loc[
        conference_championship_mask(source) & source["Result"].eq("W")
    ]
    national_games = source.loc[national_postseason_mask(source)]
    if not conference:
        national_games = national_games.loc[national_games["Result"].eq("W")]
    groups = [
        (
            "Conference Championships",
            conference_champions,
            not conference,
        ),
        (
            "National Championship",
            national_games,
            False,
        ),
    ]
    for title, group, show_conference in groups:
        if group.empty:
            continue
        star_class = "conference" if title == "Conference Championships" else "national"
        rows = []
        for year, year_games in group.sort_values(["Year", "Week"], ascending=[False, False]).groupby("Year", sort=False):
            column_count = 5 if show_conference else 4
            rows.append(f'<tr><th colspan="{column_count}" style="text-align:left;font-size:18px;color:#111827;background:#eef2f7;">{int(year)} Season</th></tr>')
            for _, game in year_games.iterrows():
                team = clean_text(game["Team"])
                opponent = clean_text(game["Opponent"])
                team_logo = clean_text(teams.get(team, {}).get("logo"))
                opponent_logo = clean_text(teams.get(opponent, {}).get("logo"))
                event = bowl_for_notes(game["Notes"], bowls)
                event_logo = clean_text(event.get("logo"))
                event_html = (
                    f'<img src="{esc(event_logo)}" alt="{esc(game["Notes"])}" title="{esc(game["Notes"])}" style="width:44px;height:36px;object-fit:contain;">'
                    if event_logo
                    else esc(game["Notes"])
                )
                winner_star = (
                    f'<span class="champion-star {star_class}" title="Winner">&#9733;</span>'
                    if game["Result"] == "W"
                    else '<span style="width:24px;flex-shrink:0;"></span>'
                )
                rows.append(
                    f"""<tr><td>{event_html}</td>{f'<td>{esc(game["Conference"])}</td>' if show_conference else ''}<td><div class="history-team" style="justify-content:flex-end;">{winner_star}{f'<div class="history-team-name">{esc(team)}</div><img src="{esc(team_logo)}" alt="{esc(team)}">' if team_logo else f'<div class="history-team-name">{esc(team)}</div>'}</div></td><td>{float(game["Points"]):,.2f}-{float(game["OpponentPoints"]):,.2f}</td><td><div class="history-team">{f'<img src="{esc(opponent_logo)}" alt="{esc(opponent)}">' if opponent_logo else ''}<div class="history-team-name">{esc(opponent)}</div></div></td></tr>"""
                )
        conference_header = "<th>Conference</th>" if show_conference else ""
        winner_header = "Champion" if title == "Conference Championships" else "Winner"
        sections.append(f'<div class="history-section-title"><span>{esc(title)}</span><div></div></div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Event</th>{conference_header}<th>{winner_header}</th><th>Score</th><th>Opponent</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    if sections:
        st.html("".join(sections))


def conference_history_matrix(ledger: pd.DataFrame, schools: pd.DataFrame, conference: str) -> None:
    games = ledger.loc[ledger["Conference"].eq(conference) & ledger["OpponentConference"].eq(conference)]
    lookup = team_lookup(schools)
    teams = sorted(
        team
        for team, info in lookup.items()
        if clean_text(info.get("conference")) == conference
    )
    if not teams:
        return
    headers = "".join(
        f'<th>{f"""<img src="{esc(lookup.get(team, {}).get("logo"))}" alt="{esc(team)}" title="{esc(team)}" style="width:38px;height:38px;object-fit:contain;">""" if clean_text(lookup.get(team, {}).get("logo")) else esc(team)}</th>'
        for team in teams
    )
    rows = []
    for team in teams:
        cells = []
        for opponent in teams:
            if team == opponent:
                cells.append('<td style="background:#111827;color:#fff;text-align:center;">-</td>')
                continue
            series = games.loc[games["Team"].eq(team) & games["Opponent"].eq(opponent)]
            wins = int(series["Result"].eq("W").sum())
            losses = int(series["Result"].eq("L").sum())
            points = series["Points"].sum()
            opponent_points = series["OpponentPoints"].sum()
            rivalry = ""
            if not series.empty and "Rivalry" in series.columns:
                rivalries = series["Rivalry"].map(clean_text)
                rivalry = next((name for name in rivalries if name), "")
            rivalry_html = f'<br><span class="history-grid-rivalry">{esc(rivalry)}</span>' if rivalry else ""
            cells.append(f'<td style="text-align:center;"><strong style="font-size:16px;">{wins}-{losses}</strong><br><span style="font-size:13px;color:#64748b;">{points:,.1f}-{opponent_points:,.1f}</span>{rivalry_html}</td>')
        team_logo = clean_text(lookup.get(team, {}).get("logo"))
        rows.append(f'<tr><th style="text-align:center;">{f"""<img src="{esc(team_logo)}" alt="{esc(team)}" title="{esc(team)}" style="width:38px;height:38px;object-fit:contain;">""" if team_logo else esc(team)}</th>{"".join(cells)}</tr>')
    st.html(f'<div class="history-section-title"><span>All-Time Conference Matchups</span><div></div></div><div style="font-family:Rajdhani,sans-serif;font-size:14px;font-weight:800;color:#64748b;margin:-4px 0 9px;">Each cell is the row team’s record and points scored against the column opponent.</div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Row Team</th>{headers}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def team_history_yearbook(full_ledger: pd.DataFrame, schools: pd.DataFrame, team: str) -> None:
    games = full_ledger.loc[full_ledger["Team"].eq(team)]
    rows = []
    history_years = set(pd.to_numeric(games["Year"], errors="coerce").dropna().astype(int))
    history_years.add(current_roster_season())
    for year in sorted(history_years, reverse=True):
        season = games.loc[games["Year"].eq(year)].copy()
        conf = season.loc[season["ConferenceGame"]]
        bowl = season.loc[
            season["Notes"].str.contains("bowl", case=False, na=False)
            & ~conference_championship_mask(season)
        ]
        highlights = []
        if not bowl.empty:
            highlights.extend(
                f'{esc(game["Notes"])}: {game["Result"]} vs {esc(game["Opponent"])}, {game["Points"]:.2f}-{game["OpponentPoints"]:.2f}'
                for _, game in bowl.sort_values("Week").iterrows()
            )
        bowl_text = "<br>".join(highlights)
        year_totals = full_ledger.loc[full_ledger["Year"].eq(year)].groupby("Team", as_index=False).agg(
            PF=("Points", "sum"),
            PA=("OpponentPoints", "sum"),
        )
        pf_rank = pa_rank = None
        if not year_totals.empty and team in set(year_totals["Team"]):
            year_totals["PFRank"] = year_totals["PF"].rank(ascending=False, method="min")
            year_totals["PARank"] = year_totals["PA"].rank(ascending=True, method="min")
            team_ranks = year_totals.loc[year_totals["Team"].eq(team)].iloc[0]
            pf_rank = int(team_ranks["PFRank"])
            pa_rank = int(team_ranks["PARank"])
        overall_w, overall_l, overall_t = int(season["Result"].eq("W").sum()), int(season["Result"].eq("L").sum()), int(season["Result"].eq("T").sum())
        conf_w, conf_l, conf_t = int(conf["Result"].eq("W").sum()), int(conf["Result"].eq("L").sum()), int(conf["Result"].eq("T").sum())
        rows.append(
            f"""<tr><td>{int(year)}</td><td>{esc(historical_owner(schools, team, int(year)), "-")}</td><td>{record_html(overall_w, overall_l, overall_t, pct(overall_w, overall_l, overall_t))}</td><td>{record_html(conf_w, conf_l, conf_t, pct(conf_w, conf_l, conf_t))}</td><td>{season["Points"].sum():,.2f}{f' ({pf_rank})' if pf_rank is not None else ''}</td><td>{season["OpponentPoints"].sum():,.2f}{f' ({pa_rank})' if pa_rank is not None else ''}</td><td>{int((season["OpponentRank"].between(1,25) & season["Result"].eq("W")).sum())}</td><td style="text-align:left;">{bowl_text}</td></tr>"""
        )
    st.html(f'<div class="history-section-title"><span>Program Yearbook</span><div></div></div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Season</th><th>Owner</th><th>Record</th><th>Conf Record</th><th>PF</th><th>PA</th><th>Top-25 Wins</th><th>Bowl Result</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def team_opponent_series(ledger: pd.DataFrame, schools: pd.DataFrame, team: str) -> None:
    games = ledger.loc[ledger["Team"].eq(team)]
    lookup = team_lookup(schools)
    rows = []
    for opponent, series in games.groupby("Opponent"):
        last = series.sort_values(["Year", "Week"]).iloc[-1]
        logo = clean_text(lookup.get(opponent, {}).get("logo"))
        last_matchup = (
            f'{int(last["Year"])}, W{int(last["Week"])} · '
            f'{last["Result"]} {last["Points"]:.2f}-{last["OpponentPoints"]:.2f}'
        )
        rivalry = clean_text(last.get("Rivalry"))
        if rivalry:
            last_matchup = f'{last_matchup}<br>{render_rivalry_pill(rivalry)}'
        rows.append((len(series), f"""<tr><td><div class="history-team">{f'<img src="{esc(logo)}" alt="{esc(opponent)}">' if logo else ''}<div class="history-team-name">{esc(opponent)}</div></div></td><td>{len(series)}</td><td>{record_text(int(series["Result"].eq("W").sum()), int(series["Result"].eq("L").sum()), int(series["Result"].eq("T").sum()))}</td><td>{series["Points"].sum():,.2f}</td><td>{series["OpponentPoints"].sum():,.2f}</td><td>{last_matchup}</td></tr>"""))
    rows = [html for _, html in sorted(rows, key=lambda item: -item[0])]
    st.html(f'<div class="history-section-title"><span>Opponent Series</span><div></div></div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Opponent</th><th>Games</th><th>Record</th><th>PF</th><th>PA</th><th>Last Matchup</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def team_opponent_series_with_next_game(
    ledger: pd.DataFrame,
    full_schedule: pd.DataFrame,
    schools: pd.DataFrame,
    team: str,
) -> None:
    games = ledger.loc[ledger["Team"].eq(team)].copy()
    lookup = team_lookup(schools)
    upcoming = full_schedule.loc[
        full_schedule["TeamA"].eq(team) | full_schedule["TeamB"].eq(team)
    ].copy()
    if not upcoming.empty:
        upcoming["Week"] = pd.to_numeric(upcoming["Week"], errors="coerce")
        if "Year" in upcoming.columns:
            upcoming["Year"] = pd.to_numeric(upcoming["Year"], errors="coerce")
            played_pairs = set(
                games[["Year", "Week", "Opponent"]]
                .drop_duplicates()
                .itertuples(index=False, name=None)
            )
            upcoming = upcoming.loc[
                ~upcoming.apply(
                    lambda row: (
                        row.get("Year"),
                        row.get("Week"),
                        clean_text(row.get("TeamB"))
                        if clean_text(row.get("TeamA")) == team
                        else clean_text(row.get("TeamA")),
                    )
                    in played_pairs,
                    axis=1,
                )
            ]

    opponents = set(games["Opponent"].dropna().map(clean_text))
    if not upcoming.empty:
        opponents.update(
            upcoming.apply(
                lambda row: clean_text(row.get("TeamB"))
                if clean_text(row.get("TeamA")) == team
                else clean_text(row.get("TeamA")),
                axis=1,
            )
        )

    rows = []
    for opponent in sorted(opponents):
        if not opponent:
            continue
        series = games.loc[games["Opponent"].eq(opponent)]
        logo = clean_text(lookup.get(opponent, {}).get("logo"))
        next_games = upcoming.loc[
            (upcoming["TeamA"].eq(team) & upcoming["TeamB"].eq(opponent))
            | (upcoming["TeamB"].eq(team) & upcoming["TeamA"].eq(opponent))
        ].sort_values(["Year", "Week"] if "Year" in upcoming.columns else ["Week"])
        next_game = "-"
        series_rivalry = ""
        if not next_games.empty:
            next_row = next_games.iloc[0]
            year_label = (
                f'{int(next_row["Year"])}, '
                if "Year" in next_games.columns and not pd.isna(next_row.get("Year"))
                else ""
            )
            next_game = f'{year_label}W{int(next_row["Week"])}'
            next_rivalry = rivalry_name(next_row)
            if next_rivalry:
                series_rivalry = next_rivalry

        if series.empty:
            games_played = wins = losses = ties = 0
            points_for = points_against = 0.0
            last_matchup = "-"
        else:
            last = series.sort_values(["Year", "Week"]).iloc[-1]
            games_played = len(series)
            wins = int(series["Result"].eq("W").sum())
            losses = int(series["Result"].eq("L").sum())
            ties = int(series["Result"].eq("T").sum())
            points_for = float(series["Points"].sum())
            points_against = float(series["OpponentPoints"].sum())
            last_matchup = (
                f'{int(last["Year"])}, W{int(last["Week"])} - '
                f'{last["Result"]} {last["Points"]:.2f}-{last["OpponentPoints"]:.2f}'
            )
            last_rivalry = clean_text(last.get("Rivalry"))
            if last_rivalry:
                series_rivalry = series_rivalry or last_rivalry
        opponent_html = f"""<div class="history-team">{f'<img src="{esc(logo)}" alt="{esc(opponent)}">' if logo else ''}<div><div class="history-team-name">{esc(opponent)}</div>{render_rivalry_pill(series_rivalry) if series_rivalry else ''}</div></div>"""
        rows.append(
            (
                games_played,
                next_game == "-",
                f"""<tr class="{'rivalry-series-row' if series_rivalry else ''}"><td>{opponent_html}</td><td>{games_played}</td><td>{record_text(wins, losses, ties)}</td><td>{points_for:,.2f}</td><td>{points_against:,.2f}</td><td>{last_matchup}</td><td>{next_game}</td></tr>""",
            )
        )
    rows = [html for _, _, html in sorted(rows, key=lambda item: (-item[0], item[1], item[2]))]
    st.html(f'<div class="history-section-title"><span>Opponent Series</span><div></div></div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Opponent</th><th>Games</th><th>Record</th><th>PF</th><th>PA</th><th>Last Matchup</th><th>Next Game</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def team_starter_history(starters: pd.DataFrame, ledger: pd.DataFrame, team: str) -> None:
    if starters.empty:
        return
    resolver = official_team_resolver(pd.DataFrame({"School": [team]}))
    team_rows = starters.copy()
    team_rows["_official_team"] = team_rows["Team"].map(lambda value: official_team_name(value, resolver))
    team_rows = team_rows.loc[team_rows["_official_team"].eq(team)].copy()
    team_rows["Year"] = pd.to_numeric(team_rows["Year"], errors="coerce")
    team_rows["Week"] = pd.to_numeric(team_rows["Week"], errors="coerce")
    team_rows["Points"] = pd.to_numeric(team_rows["Points"], errors="coerce")
    completed_pairs = set(
        ledger.loc[ledger["Team"].eq(team), ["Year", "Week"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    occurred = team_rows.loc[
        team_rows.apply(lambda row: (row["Year"], row["Week"]) in completed_pairs, axis=1)
    ].drop_duplicates(["Year", "Week", "Player"], keep="last")
    started = occurred.loc[
        occurred["RosterSpot"].astype(str).eq("Starter")
    ].dropna(subset=["Player", "Points"]).drop_duplicates(["Year", "Week", "Player"], keep="last")
    if started.empty:
        return
    summary = started.groupby("Player").agg(Starts=("Player", "size"), Points=("Points", "sum"), Average=("Points", "mean"), Best=("Points", "max"), Position=("Position", "first")).reset_index()
    appearances = occurred.groupby("Player").size().rename("RosterGames").reset_index()
    summary = summary.merge(appearances, on="Player", how="left")
    summary["StartPct"] = summary["Starts"] / summary["RosterGames"].clip(lower=1)
    summary = summary.sort_values(["Points", "Starts"], ascending=[False, False])
    position_colors = {"QB": "#ef4444", "RB": "#f97316", "WR": "#eab308", "TE": "#22c55e"}
    body = "".join(f'<tr><td><span class="standings-rank">{index + 1}</span></td><td><div class="history-team"><img src="{esc(player_picture(row["Player"]))}" alt="{esc(row["Player"])}" onerror="{player_picture_fallback()}" style="border-radius:50%;object-fit:cover;object-position:center 12%;"><div style="display:flex;align-items:center;gap:7px;"><div class="history-team-name">{esc(row["Player"])}</div><span class="position-chip" style="background:{position_colors.get(clean_text(row["Position"]), "#e5e7eb")};">{esc(row["Position"])}</span></div></div></td><td>{int(row["Starts"])}</td><td>{row["StartPct"]:.1%}</td><td>{row["Points"]:,.2f}</td><td>{row["Average"]:,.2f}</td><td>{row["Best"]:,.2f}</td></tr>' for index, (_, row) in enumerate(summary.head(50).iterrows()))
    st.html(f'<div class="history-section-title"><span>All-Time Starter Production</span><div></div></div><div class="history-table-wrap"><table class="history-table"><thead><tr><th>Rank</th><th>Player</th><th>Starts</th><th>Start %</th><th>Points While Starting</th><th>Avg Start</th><th>Best Start</th></tr></thead><tbody>{body}</tbody></table></div>')


@loading_spinner("Loading league history...")
def render_league_history(ledger: pd.DataFrame, schools: pd.DataFrame, bowls: pd.DataFrame) -> None:
    history_hero(
        "League History",
        "The programs, performances, and ranked wins that have shaped the NCAA/NFL Crossover.",
        LEAGUE_LOGO,
    )
    aggregate = history_aggregate(ledger, schools)
    history_metrics(
        [
            (f'{ledger["Year"].nunique()}', "Seasons"),
            (f'{len(ledger) // 2:,}', "Completed Games"),
            (f'{len(aggregate)}', "Programs"),
            (f'{ledger["Points"].sum() / 2:,.2f}', "Points Scored"),
            (f'{int((ledger["OpponentRank"].between(1, 25) & ledger["Result"].eq("W")).sum())}', "Top-25 Wins"),
        ]
    )
    history_program_table(aggregate, schools)
    history_champions(ledger, schools, bowls)
    history_record_book(ledger, schools)


@loading_spinner("Loading conference history...")
def render_conference_history(
    ledger: pd.DataFrame,
    schools: pd.DataFrame,
    conferences: pd.DataFrame,
    bowls: pd.DataFrame,
    conference: str,
) -> None:
    conf_ledger = ledger.loc[ledger["Conference"].eq(conference)].copy()
    history_hero(
        f"{conference} History",
        "An all-time view of the conference's strongest programs and most meaningful victories.",
        conference_logo(conferences, conference),
        "#7dd3fc",
    )
    aggregate = history_aggregate(conf_ledger, schools)
    aggregate = aggregate.loc[aggregate["Conference"].eq(conference)].reset_index(drop=True)
    history_metrics(
        [
            (f'{conf_ledger["Year"].nunique()}', "Seasons"),
            (
                f'{int((national_championship_mask(conf_ledger) & conf_ledger["Result"].eq("W")).sum())}',
                "League Championships",
            ),
            (f'{int(conf_ledger["Result"].eq("W").sum())}', "Wins"),
            (f'{int((conf_ledger["OpponentRank"].between(1, 25) & conf_ledger["Result"].eq("W")).sum())}', "Top-25 Wins"),
        ],
        "#7dd3fc",
    )
    history_program_table(aggregate, schools)
    history_champions(conf_ledger, schools, bowls, conference)
    history_record_book(conf_ledger, schools, "Conference Record Book")
    conference_history_matrix(ledger, schools, conference)


@loading_spinner("Loading team history...")
def render_team_history(
    ledger: pd.DataFrame,
    schedule: pd.DataFrame,
    schools: pd.DataFrame,
    starters: pd.DataFrame,
    team: str,
) -> None:
    games = ledger.loc[ledger["Team"].eq(team)].copy()
    info = team_lookup(schools).get(team, {})
    wins = int(games["Result"].eq("W").sum())
    losses = int(games["Result"].eq("L").sum())
    ties = int(games["Result"].eq("T").sum())
    ranked_wins = int((games["OpponentRank"].between(1, 25) & games["Result"].eq("W")).sum())
    conference_titles = int(
        (conference_championship_mask(games) & games["Result"].eq("W")).sum()
    )
    national_titles = games.loc[
        national_championship_mask(games) & games["Result"].eq("W"),
        "Year",
    ].nunique()
    history_metrics(
        [
            (record_text(wins, losses, ties), "All-Time Record"),
            (f'{games["Points"].sum():,.2f}', "Points Scored"),
            (f"{ranked_wins}", "Top-25 Wins"),
            (f"{conference_titles}", "Conference Championships"),
            (f"{national_titles}", "National Championships"),
        ],
        clean_text(info.get("color"), "#c8102e"),
    )

    team_history_yearbook(ledger, schools, team)
    team_opponent_series_with_next_game(games, schedule, schools, team)
    history_record_book(games, schools, "Team Record Book")
    team_starter_history(starters, ledger, team)


def all_time_player_options(
    rosters: pd.DataFrame,
    starters: pd.DataFrame,
    drafts: pd.DataFrame,
) -> list[str]:
    names: set[str] = set()
    for frame, column in [
        (rosters, "player_name"),
        (starters, "Player"),
        (drafts, "Player"),
    ]:
        if not frame.empty and column in frame.columns:
            names.update(
                clean_text(value)
                for value in frame[column].dropna()
                if clean_text(value)
            )
    return sorted(names, key=str.casefold)


def player_dynasty_snapshot(player: str) -> dict[str, object]:
    values, _ = load_dynasty_asset_values()
    values = values.copy()
    values["_player_key"] = values["player"].map(dynasty_player_key)
    match = values.loc[values["_player_key"].eq(dynasty_player_key(player))]
    if match.empty:
        return {
            "position": "", "team": "", "one_qb": 0, "superflex": 0,
            "one_qb_rank": "-", "superflex_rank": "-",
            "one_qb_overall": "-", "superflex_overall": "-",
        }
    row = match.iloc[0]
    position = clean_text(row.get("pos"))
    positional = values.loc[values["pos"].astype(str).eq(position)].copy()
    positional["one_qb_rank"] = pd.to_numeric(positional["value_1qb"], errors="coerce").rank(ascending=False, method="min")
    positional["superflex_rank"] = pd.to_numeric(positional["value_2qb"], errors="coerce").rank(ascending=False, method="min")
    values["one_qb_overall"] = pd.to_numeric(values["value_1qb"], errors="coerce").rank(ascending=False, method="min")
    values["superflex_overall"] = pd.to_numeric(values["value_2qb"], errors="coerce").rank(ascending=False, method="min")
    ranked = positional.loc[positional["_player_key"].eq(dynasty_player_key(player))].iloc[0]
    overall = values.loc[values["_player_key"].eq(dynasty_player_key(player))].iloc[0]
    return {
        "position": position,
        "team": clean_text(row.get("team")),
        "one_qb": float(pd.to_numeric(row.get("value_1qb"), errors="coerce") or 0),
        "superflex": float(pd.to_numeric(row.get("value_2qb"), errors="coerce") or 0),
        "one_qb_rank": f'{position}{int(ranked["one_qb_rank"])}',
        "superflex_rank": f'{position}{int(ranked["superflex_rank"])}',
        "one_qb_overall": f'OVR{int(overall["one_qb_overall"])}',
        "superflex_overall": f'OVR{int(overall["superflex_overall"])}',
    }


def last_season_player_finish(starters: pd.DataFrame, player: str) -> str:
    if starters.empty:
        return "-"
    history = starters.copy()
    history["Year"] = pd.to_numeric(history["Year"], errors="coerce")
    history["Week"] = pd.to_numeric(history["Week"], errors="coerce")
    history["Points"] = pd.to_numeric(history["Points"], errors="coerce")
    history = history.loc[
        history["Year"].lt(current_roster_season())
        & history["Points"].notna()
    ].sort_values(["Year", "Week", "Player"]).drop_duplicates(
        ["Year", "Week", "Player"], keep="last"
    )
    player_years = history.loc[history["Player"].astype(str).eq(player), "Year"].dropna()
    if player_years.empty:
        return "-"
    year = int(player_years.max())
    season = history.loc[history["Year"].eq(year)].copy()
    totals = season.groupby(["Player", "Position"], as_index=False)["Points"].sum()
    player_row = totals.loc[totals["Player"].eq(player)]
    if player_row.empty:
        return "-"
    position = clean_text(player_row.iloc[0]["Position"])
    position_totals = totals.loc[totals["Position"].astype(str).eq(position)].copy()
    position_totals["Rank"] = position_totals["Points"].rank(ascending=False, method="min")
    rank = int(position_totals.loc[position_totals["Player"].eq(player), "Rank"].iloc[0])
    totals["OverallRank"] = totals["Points"].rank(ascending=False, method="min")
    overall_rank = int(totals.loc[totals["Player"].eq(player), "OverallRank"].iloc[0])
    points = float(player_row.iloc[0]["Points"])
    points_label = f"{points:,.2f}".rstrip("0").rstrip(".")
    return f"{points_label} · {position}{rank} · OVR{overall_rank}"


def current_season_player_rank(starters: pd.DataFrame, player: str) -> str:
    if starters.empty:
        return "0 · - · OVR1"
    player_history = starters.loc[starters["Player"].astype(str).eq(player)]
    fallback_position = (
        clean_text(player_history.iloc[-1].get("Position"))
        if not player_history.empty
        else "-"
    )
    season = starters.copy()
    season["Year"] = pd.to_numeric(season["Year"], errors="coerce")
    season["Week"] = pd.to_numeric(season["Week"], errors="coerce")
    season["Points"] = pd.to_numeric(season["Points"], errors="coerce").fillna(0)
    season = season.loc[season["Year"].eq(current_roster_season())]
    season = season.sort_values(["Year", "Week", "Player"]).drop_duplicates(
        ["Year", "Week", "Player"], keep="last"
    )
    totals = season.groupby(["Player", "Position"], as_index=False)["Points"].sum()
    player_row = totals.loc[totals["Player"].astype(str).eq(player)]
    if player_row.empty:
        return f"0 · {fallback_position}1 · OVR1"
    position = clean_text(player_row.iloc[0]["Position"])
    position_totals = totals.loc[totals["Position"].astype(str).eq(position)].copy()
    position_totals["Rank"] = position_totals["Points"].rank(ascending=False, method="min")
    rank = int(position_totals.loc[position_totals["Player"].astype(str).eq(player), "Rank"].iloc[0])
    totals["OverallRank"] = totals["Points"].rank(ascending=False, method="min")
    overall_rank = int(
        totals.loc[totals["Player"].astype(str).eq(player), "OverallRank"].iloc[0]
    )
    points = float(player_row.iloc[0]["Points"])
    points_label = f"{points:,.2f}".rstrip("0").rstrip(".")
    return f"{points_label} · {position}{rank} · OVR{overall_rank}"


def render_player_current_ownership(
    player: str,
    rosters: pd.DataFrame,
    conferences: pd.DataFrame,
) -> None:
    owned = rosters.loc[rosters["player_name"].astype(str).eq(player)].copy()
    headers = []
    cells = []
    for conference in LEAGUE_ROSTER_ORDER:
        conf_logo = conference_logo(conferences, conference)
        headers.append(
            f'<th class="conf-head">{f"""<img src="{esc(conf_logo)}" alt="{esc(conference)}" title="{esc(conference)}">""" if conf_logo else esc(conference)}</th>'
        )
        match = owned.loc[owned["league_name"].astype(str).eq(conference)]
        if match.empty:
            cells.append("<td></td>")
            continue
        row = match.iloc[0]
        team_logo = clean_text(row.get("team_logo"))
        team = clean_text(row.get("team_name"))
        cells.append(
            f'<td class="team-logo-cell">{f"""<img src="{esc(team_logo)}" alt="{esc(team)}" title="{esc(team)}">""" if team_logo else esc(team)}</td>'
        )
    taken_count = owned["league_name"].nunique()
    headers.append('<th class="taken-col">#</th>')
    cells.append(
        f'<td class="taken-col"><span class="taken-pill" style="background:{taken_color(taken_count, 12)};">{taken_count}</span></td>'
    )
    st.html(
        f'<div class="history-section-title"><span>Current League Ownership</span><div></div></div>'
        f'<div class="roster-scroll"><table class="roster-table league-matrix player-ownership-table">'
        f'<thead><tr>{"".join(headers)}</tr></thead><tbody><tr>{"".join(cells)}</tr></tbody></table></div>'
    )


@loading_spinner("Loading player history and charts...")
def render_player_dashboard(
    player: str,
    rosters: pd.DataFrame,
    starters: pd.DataFrame,
    drafts: pd.DataFrame,
    conferences: pd.DataFrame,
    schools: pd.DataFrame,
) -> None:
    current = rosters.loc[rosters["player_name"].astype(str).eq(player)].copy()
    history = starters.loc[starters["Player"].astype(str).eq(player)].copy()
    draft_history = drafts.loc[drafts["Player"].astype(str).eq(player)].copy()
    dynasty = player_dynasty_snapshot(player)
    position = first_value(current, "position", clean_text(dynasty.get("position")))

    st.html(
        f"""
<div class="player-profile-hero">
  <img src="{esc(player_picture(player))}" alt="{esc(player)}" onerror="{player_picture_fallback()}">
  <div>
    <div class="player-profile-kicker">League Player Archive</div>
    <div class="player-profile-name">{esc(player)}</div>
    <div class="player-profile-meta">{esc(position, "Position Unknown")}</div>
  </div>
</div>
"""
    )

    history["Points"] = pd.to_numeric(history.get("Points"), errors="coerce")
    history["Year"] = pd.to_numeric(history.get("Year"), errors="coerce")
    history["Week"] = pd.to_numeric(history.get("Week"), errors="coerce")
    all_weekly = starters.copy()
    all_weekly["Points"] = pd.to_numeric(all_weekly.get("Points"), errors="coerce")
    all_weekly["Year"] = pd.to_numeric(all_weekly.get("Year"), errors="coerce")
    all_weekly["Week"] = pd.to_numeric(all_weekly.get("Week"), errors="coerce")
    completed_pairs = set(
        all_weekly.loc[all_weekly["Points"].fillna(0).ne(0), ["Year", "Week"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    history = history.loc[
        history.apply(lambda row: (row["Year"], row["Week"]) in completed_pairs, axis=1)
    ].copy()
    weekly_points = (
        history.dropna(subset=["Year", "Week", "Points"])
        .sort_values(["Year", "Week", "Conference", "Team"])
        .drop_duplicates(["Year", "Week", "Player"], keep="last")
        .copy()
    )
    actual_points = weekly_points["Points"]
    history_metrics(
        [
            (f"{current['league_name'].nunique()}", "Current Conferences"),
            (f"{len(draft_history):,}", "Times Drafted"),
            (f"{actual_points.sum():,.2f}", "League Points"),
            (f"{actual_points.max():,.2f}" if not actual_points.empty else "-", "Career High"),
        ],
        "#f2cf68",
    )
    player_value_metrics(
        dynasty,
        last_season_player_finish(starters, player),
        current_season_player_rank(starters, player),
    )

    render_player_current_ownership(player, rosters, conferences)

    draft_column, chart_column = st.columns([0.17, 0.83], gap="large")
    with draft_column:
        st.html('<div class="history-section-title"><span>Draft History</span><div></div></div>')
        if draft_history.empty:
            st.caption("This player has not appeared in a recorded league draft.")
        else:
            teams = team_lookup(schools)
            tiles = []
            draft_history = draft_history.copy()
            draft_history["Year"] = pd.to_numeric(draft_history["Year"], errors="coerce")
            draft_history["Round"] = pd.to_numeric(draft_history["Round"], errors="coerce")
            draft_history["Pick"] = pd.to_numeric(draft_history["Pick"], errors="coerce")
            draft_history = draft_history.sort_values(
                ["Year", "Type", "Round", "Pick"], ascending=[False, True, True, True]
            )
            for _, pick in draft_history.iterrows():
                team = clean_text(pick.get("Team"))
                info = teams.get(team, {})
                team_logo = clean_text(info.get("logo"))
                color = clean_text(info.get("color"), "#1a2030")
                pick_label = (
                    f'{int(pick["Round"])}.{int(pick["Pick"])}'
                    if not pd.isna(pick["Round"]) and not pd.isna(pick["Pick"])
                    else "-"
                )
                draft_type = clean_text(pick.get("Type"))
                draft_type = (
                    "Start-Up"
                    if match_key(draft_type) in {"startup", "start-up", "start up"}
                    else "Rookie"
                    if match_key(draft_type) == "rookie"
                    else draft_type
                )
                tiles.append(
                    f"""
<div class="player-draft-tile" style="--team-color:{esc(color)};">
  <span class="player-draft-pick">{esc(pick_label)}</span>
  {f'<img src="{esc(team_logo)}" alt="{esc(team)}" title="{esc(team)}">' if team_logo else '<span></span>'}
  <div>
    <div class="player-draft-year">{int(pick["Year"]) if not pd.isna(pick["Year"]) else "-"}</div>
    <div class="player-draft-meta">{esc(draft_type)} · {esc(pick.get("Conference"))}</div>
  </div>
</div>
"""
                )
            st.html(f'<div class="player-draft-stack">{"".join(tiles)}</div>')

    with chart_column:
        positive_weekly_points = weekly_points.loc[weekly_points["Points"].gt(0)].copy()
        chart_years = sorted(
            weekly_points["Year"].dropna().astype(int).unique(), reverse=True
        )
        selected_chart_year = st.selectbox(
            "Chart Year",
            ["All"] + chart_years,
            key=f"player_chart_year_{match_key(player)}",
        )
        displayed_chart_years = (
            chart_years if selected_chart_year == "All" else [selected_chart_year]
        )
        chart_axis = pd.DataFrame(
            [
                {
                    "Year": year,
                    "Week": week,
                    "Game": f"{year} W{week:02d}",
                }
                for year in sorted(displayed_chart_years)
                for week in range(1, 19)
            ]
        )
        chart_game_order = chart_axis["Game"].tolist()
        st.html('<div class="history-section-title"><span>Weekly Scoring Trend</span><div></div></div>')
        if not chart_years:
            st.caption("No completed weekly scoring history is available.")
        else:
            chart_data = positive_weekly_points.copy()
            if selected_chart_year != "All":
                chart_data = chart_data.loc[chart_data["Year"].eq(selected_chart_year)].copy()
            chart_data["Year"] = chart_data["Year"].astype(int)
            chart_data["Week"] = chart_data["Week"].astype(int)
            chart_data = chart_axis.merge(
                chart_data.drop(columns=["Game"], errors="ignore"),
                on=["Year", "Week"],
                how="left",
            )
            chart_data = chart_data.sort_values(["Year", "Week"]).reset_index(drop=True)
            plotted_chart_data = chart_data.dropna(subset=["Points"]).copy()
            plotted_points = pd.to_numeric(chart_data["Points"], errors="coerce").dropna()
            max_points = max(float(plotted_points.max()) * 1.2, 1) if not plotted_points.empty else 1
            base = alt.Chart(plotted_chart_data).encode(
                x=alt.X(
                    "Game:N",
                    sort=chart_game_order,
                    title=None,
                    scale=alt.Scale(domain=chart_game_order),
                    axis=alt.Axis(
                        labelAngle=-55,
                        labelColor="#64748b",
                        labelFont="Rajdhani",
                        labelFontSize=10,
                        labelLimit=80,
                        labelOverlap="greedy",
                        tickColor="#cbd5e1",
                        domainColor="#94a3b8",
                        grid=False,
                    ),
                ),
            )
            line = (
                base.mark_line(
                    color="#c8102e",
                    strokeWidth=3.5,
                    interpolate="monotone",
                    strokeCap="round",
                    strokeJoin="round",
                )
                .encode(
                    y=alt.Y(
                        "Points:Q",
                        title="Fantasy Points",
                        scale=alt.Scale(domain=[0, max_points]),
                        axis=alt.Axis(gridColor="#edf0f7", domain=False, tickColor="#cbd5e1"),
                    ),
                )
            )
            points = (
                base.transform_filter(alt.datum.Points > 0)
                .mark_circle(size=82, color="#c8102e", stroke="#ffffff", strokeWidth=2)
                .encode(
                    y=alt.Y("Points:Q", scale=alt.Scale(domain=[0, max_points])),
                    tooltip=[
                        alt.Tooltip("Year:O"),
                        alt.Tooltip("Week:O"),
                        alt.Tooltip("Points:Q", format=".2f"),
                    ],
                )
            )
            point_labels = (
                base.transform_filter(alt.datum.Points > 0)
                .mark_text(
                    dy=-13,
                    color="#111827",
                    font="Barlow Condensed",
                    fontSize=11,
                    fontWeight="bold",
                )
                .encode(
                    y=alt.Y("Points:Q", scale=alt.Scale(domain=[0, max_points])),
                    text=alt.Text("Points:Q", format=".2f"),
                )
            )
            points_chart = (
                (line + points + point_labels)
                .properties(height=336, background="#f8fafc")
                .configure_view(stroke=None)
                .configure_axis(
                    labelFont="Rajdhani",
                    titleFont="Barlow Condensed",
                    labelColor="#64748b",
                    titleColor="#334155",
                )
            )
            st.html('<div class="player-chart-shell" style="--accent:#c8102e;">')
            st.altair_chart(points_chart, use_container_width=True)
            st.html("</div>")

            rank_source = all_weekly.loc[
                all_weekly.apply(lambda row: (row["Year"], row["Week"]) in completed_pairs, axis=1)
                & all_weekly["Position"].astype(str).eq(position)
                & all_weekly["Points"].notna()
            ].sort_values(["Year", "Week", "Player"]).drop_duplicates(
                ["Year", "Week", "Player"], keep="last"
            )
            rank_source["WeeklyRank"] = rank_source.groupby(["Year", "Week"])["Points"].rank(
                ascending=False, method="min"
            )
            player_ranks = rank_source.loc[rank_source["Player"].astype(str).eq(player)].copy()
            player_ranks = player_ranks.loc[player_ranks["Points"].ne(0)].copy()
            player_ranks["Year"] = player_ranks["Year"].astype(int)
            player_ranks["Week"] = player_ranks["Week"].astype(int)
            if selected_chart_year != "All":
                player_ranks = player_ranks.loc[
                    player_ranks["Year"].eq(selected_chart_year)
                ].copy()
            player_ranks = player_ranks.sort_values(["Year", "Week"]).reset_index(drop=True)
            player_ranks["GameOrder"] = range(len(player_ranks))
            player_ranks["Game"] = player_ranks.apply(
                lambda row: f'{int(row["Year"])} W{int(row["Week"]):02d}', axis=1
            )
            player_ranks["RankLabel"] = position + player_ranks["WeeklyRank"].astype(int).astype(str)
            rank_data = chart_axis.merge(
                player_ranks.drop(columns=["Game"], errors="ignore"),
                on=["Year", "Week"],
                how="left",
            )
            if not rank_data.empty:
                plotted_ranks = pd.to_numeric(rank_data["WeeklyRank"], errors="coerce").dropna()
                plotted_rank_data = rank_data.dropna(subset=["WeeklyRank"]).copy()
                max_rank = max(int(plotted_ranks.max()), 1) if not plotted_ranks.empty else 1
                rank_ceiling = max(10, ((max_rank + 9) // 10) * 10)
                rank_domain = [rank_ceiling, 1]
                rank_ticks = [1] + list(range(10, rank_ceiling + 1, 10))
                rank_base = alt.Chart(plotted_rank_data).encode(
                    x=alt.X(
                        "Game:N",
                        sort=chart_game_order,
                        title=None,
                        scale=alt.Scale(domain=chart_game_order),
                        axis=alt.Axis(
                            labelAngle=-55,
                            labelColor="#64748b",
                            labelFont="Rajdhani",
                            labelFontSize=10,
                            labelLimit=80,
                            labelOverlap="greedy",
                            tickColor="#cbd5e1",
                            domainColor="#94a3b8",
                            grid=False,
                        ),
                    ),
                    y=alt.Y(
                        "WeeklyRank:Q",
                        title=f"{position} Weekly Rank",
                        scale=alt.Scale(domain=rank_domain),
                        axis=alt.Axis(
                            grid=True,
                            gridColor="#cbd5e1",
                            gridOpacity=1,
                            gridWidth=1,
                            domain=True,
                            domainColor="#64748b",
                            domainWidth=1.5,
                            tickColor="#64748b",
                            tickWidth=1.5,
                            labels=True,
                            labelColor="#334155",
                            labelFontSize=12,
                            labelFontWeight="bold",
                            orient="left",
                            values=rank_ticks,
                            format="d",
                            labelPadding=7,
                            titlePadding=12,
                        ),
                    ),
                )
                rank_line = rank_base.mark_line(
                    color="#2563eb",
                    strokeWidth=3,
                    interpolate="monotone",
                    strokeCap="round",
                    strokeJoin="round",
                )
                rank_points = rank_base.mark_circle(
                    size=105, color="#ffffff", stroke="#2563eb", strokeWidth=3
                ).encode(
                    tooltip=[
                        alt.Tooltip("Year:O"),
                        alt.Tooltip("Week:O"),
                        alt.Tooltip("RankLabel:N", title="Weekly Rank"),
                        alt.Tooltip("Points:Q", format=".2f"),
                    ],
                )
                rank_labels = rank_base.mark_text(
                    dy=-13,
                    color="#111827",
                    font="Barlow Condensed",
                    fontSize=11,
                    fontWeight="bold",
                ).encode(
                    text="RankLabel:N",
                )
                rank_chart = (
                    (rank_line + rank_points + rank_labels)
                    .properties(height=389, background="#f8fafc")
                    .configure_view(stroke=None)
                    .configure_axis(
                        labelFont="Rajdhani",
                        titleFont="Barlow Condensed",
                        labelColor="#64748b",
                        titleColor="#334155",
                    )
                )
                st.html('<div class="history-section-title"><span>Weekly Position Rank</span><div></div></div>')
                st.html('<div class="player-chart-shell" style="--accent:#f2cf68;">')
                st.altair_chart(rank_chart, use_container_width=True)
                st.html("</div>")

    st.html('<div class="history-section-title"><span>League History</span><div></div></div>')
    if history.empty:
        st.caption("No historical league roster records are available.")
        return
    status_symbols = {
        "Starter": ("✅", "Starter"),
        "Bench": ("❌", "Bench"),
        "Reserve": ("🏥", "Injured Reserve"),
        "Taxi": ("🚕", "Taxi"),
    }
    headers = ["<th>Week</th>"] + [
        f'<th>{f"""<img class="conf-logo-history" src="{esc(conference_logo(conferences, conference))}" alt="{esc(conference)}" title="{esc(conference)}">""" if conference_logo(conferences, conference) else esc(conference)}</th>'
        for conference in LEAGUE_ROSTER_ORDER
    ] + ["<th>Start %</th>", "<th>Position Rank</th>", "<th>Overall Rank</th>", "<th>Points</th>"]
    rows = []
    weekly_rank_source = all_weekly.loc[
        all_weekly.apply(lambda row: (row["Year"], row["Week"]) in completed_pairs, axis=1)
        & all_weekly["Points"].notna()
    ].sort_values(["Year", "Week", "Player"]).drop_duplicates(
        ["Year", "Week", "Player"], keep="last"
    )
    weekly_rank_source["OverallRank"] = weekly_rank_source.groupby(
        ["Year", "Week"]
    )["Points"].rank(ascending=False, method="min")
    weekly_rank_source["PositionRank"] = weekly_rank_source.groupby(
        ["Year", "Week", "Position"]
    )["Points"].rank(ascending=False, method="min")
    player_weekly_ranks = weekly_rank_source.loc[
        weekly_rank_source["Player"].astype(str).eq(player)
    ].set_index(["Year", "Week"])
    positive_points = weekly_points.loc[weekly_points["Points"].gt(0), "Points"]
    min_points = float(positive_points.min()) if not positive_points.empty else 0
    max_points = float(positive_points.max()) if not positive_points.empty else 1
    def points_heat(value: float) -> str:
        if value == 0:
            return "#eef2f7"
        ratio = (value - min_points) / max(max_points - min_points, 1)
        if ratio < 0.5:
            red, green, blue = 254, int(226 + (ratio * 2 * 23)), int(226 - (ratio * 2 * 31))
        else:
            shifted = (ratio - 0.5) * 2
            red, green, blue = int(254 - shifted * 34), int(249 + shifted * 3), int(195 - shifted * 12)
        return f"rgb({red},{green},{blue})"
    player_years = sorted(history["Year"].dropna().astype(int).unique(), reverse=True)
    for year in player_years:
        rows.append(
            f'<tr class="season-row"><th colspan="17">{year} Season</th></tr>'
        )
        year_history = history.loc[history["Year"].eq(year)].copy()
        denominator = ACTIVE_CONFERENCE_COUNT_BY_YEAR.get(year, year_history["Conference"].nunique())
        completed_year_weeks = sorted(
            {
                int(week)
                for completed_year, week in completed_pairs
                if int(completed_year) == year
            },
            reverse=True,
        )
        for week in completed_year_weeks:
            week_history = year_history.loc[year_history["Week"].eq(week)]
            cells = [f"<td>Week {week}</td>"]
            for conference in LEAGUE_ROSTER_ORDER:
                conf_rows = week_history.loc[
                    week_history["Conference"].astype(str).eq(conference)
                ]
                if conf_rows.empty:
                    cells.append('<td><span class="player-status" title="Not on roster">—</span></td>')
                    continue
                statuses = conf_rows["RosterSpot"].dropna().astype(str).tolist()
                status = next(
                    (candidate for candidate in ["Starter", "Bench", "Reserve", "Taxi"] if candidate in statuses),
                    "",
                )
                symbol, label = status_symbols.get(status, ("—", "Not on roster"))
                cells.append(
                    f'<td><span class="player-status" title="{esc(label)}">{symbol}</span></td>'
                )
            starts = week_history.loc[
                week_history["RosterSpot"].astype(str).eq("Starter"), "Conference"
            ].nunique()
            cells.append(f"<td>{starts / max(denominator, 1):.0%}</td>")
            rank_key = (float(year), float(week))
            if rank_key in player_weekly_ranks.index:
                rank_row = player_weekly_ranks.loc[rank_key]
                if isinstance(rank_row, pd.DataFrame):
                    rank_row = rank_row.iloc[0]
                rank_position = clean_text(rank_row.get("Position"), position)
                cells.append(f'<td>{esc(rank_position)}{int(rank_row["PositionRank"])}</td>')
                cells.append(f'<td>OVR{int(rank_row["OverallRank"])}</td>')
            else:
                cells.append("<td></td>")
                cells.append("<td></td>")
            points = weekly_points.loc[
                weekly_points["Year"].eq(year) & weekly_points["Week"].eq(week),
                "Points",
            ]
            if points.empty:
                cells.append("<td></td>")
            else:
                point_value = float(points.iloc[0])
                cells.append(
                    f'<td style="background:{points_heat(point_value)};font-weight:900;">{point_value:,.2f}</td>'
                )
            rows.append(f"<tr>{''.join(cells)}</tr>")
    st.html(
        f'<div class="history-table-wrap"><table class="history-table player-history-matrix">'
        f'<thead><tr>{"".join(headers)}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


@loading_spinner("Loading league rules...")
def render_rules() -> None:
    st.html(
        """
<div class="rules-hero">
  <div class="rules-kicker">Official League Guide</div>
  <div class="rules-title">NCAA/NFL College Football Crossover</div>
  <div class="rules-sub">
    A 12-conference, 144-team dynasty ecosystem built around college football structure:
    conference play, non-conference games, conference championships, bowl season,
    weekly rankings, and the College Football Playoff.
  </div>
</div>

<div class="rules-grid">
  <div class="rules-card" style="--accent:#c8102e;">
    <div class="rules-card-title">Overview</div>
    <p>
      The NCAA/NFL Football Crossover consists of 12, 12-team conferences, each
      representing a conference in the college football landscape.
    </p>
    <p>
      The league includes in-conference and out-of-conference games, conference
      championships, bowl season, weekly rankings, and a playoff.
    </p>
  </div>
  <div class="rules-card" style="--accent:#1d4ed8;">
    <div class="rules-card-title">Setup</div>
    <p>There are two groups of conferences in the league.</p>
    <div class="rules-table-wrap">
      <table class="rules-table">
        <thead><tr><th>Power 6</th><th>Group of 6</th></tr></thead>
        <tbody>
          <tr><td>Big XII</td><td>Sun Belt</td></tr>
          <tr><td>Big Ten</td><td>MAC</td></tr>
          <tr><td>PAC</td><td>American</td></tr>
          <tr><td>ACC</td><td>AAC</td></tr>
          <tr><td>SEC</td><td>C-USA</td></tr>
          <tr><td>The 6ix</td><td>The 12</td></tr>
        </tbody>
      </table>
    </div>
    <ul>
      <li>Owners may own one Power 6 team and one Group of 6 team at the same time.</li>
      <li>Power 6 orphans are offered to Group of 6 owners before the public.</li>
    </ul>
  </div>
</div>

<div class="rules-grid">
  <div class="rules-card" style="--accent:#16a34a;">
    <div class="rules-card-title">Roster</div>
    <p>All teams use the same general roster size.</p>
    <div class="rules-pill-row">
      <span class="rules-pill">8 Starters</span>
      <span class="rules-pill">12 Bench</span>
      <span class="rules-pill">5 Taxi</span>
    </div>
    <div class="rules-note">Taxi size changed for 2026.</div>
    <div class="rules-table-wrap">
      <table class="rules-table">
        <thead><tr><th>Slot</th><th>Power 6</th><th>Group of 6</th></tr></thead>
        <tbody>
          <tr><td>Starter 1</td><td>QB</td><td>QB</td></tr>
          <tr><td>Starter 2</td><td>RB</td><td>RB</td></tr>
          <tr><td>Starter 3</td><td>RB</td><td>RB</td></tr>
          <tr><td>Starter 4</td><td>WR</td><td>WR</td></tr>
          <tr><td>Starter 5</td><td>WR</td><td>WR</td></tr>
          <tr><td>Starter 6</td><td>TE</td><td>TE</td></tr>
          <tr><td>Starter 7</td><td>SUPERFLEX</td><td>FLEX</td></tr>
          <tr><td>Starter 8</td><td>FLEX</td><td>FLEX</td></tr>
        </tbody>
      </table>
    </div>
    <p>The Power 6 receives a slight lineup advantage without removing the Group of 6's ability to compete.</p>
  </div>
  <div class="rules-card" style="--accent:#7c3aed;">
    <div class="rules-card-title">Taxi Squad</div>
    <p>All teams have 5 taxi slots at their disposal.</p>
    <p>Taxi slots lock at the beginning of the NFL season.</p>
    <div class="rules-note">A Week 4 lock was discussed but did not receive enough support, so the existing lock timing remains.</div>
  </div>
</div>

<div class="rules-grid">
  <div class="rules-card" style="--accent:#0f766e;">
    <div class="rules-card-title">Schedule</div>
    <div class="rules-note">Schedule format changed for 2026.</div>
    <div class="rules-table-wrap">
      <table class="rules-table">
        <thead><tr><th>Weeks</th><th>Stage</th></tr></thead>
        <tbody>
          <tr><td>Week 1</td><td>Out-of-conference game</td></tr>
          <tr><td>Weeks 2-12</td><td>Conference play</td></tr>
          <tr><td>Week 13</td><td>Conference championship; non-title teams play an OOC game</td></tr>
          <tr><td>Weeks 14-17</td><td>College Football Playoff / Bowl SZN</td></tr>
        </tbody>
      </table>
    </div>
    <p>There are playoff games in Weeks 13 and 14. Teams have 12 weeks to prepare for these byes.</p>
  </div>
  <div class="rules-card" style="--accent:#d97706;">
    <div class="rules-card-title">College Football Playoff</div>
    <div class="rules-note">Playoff qualification changed for 2026.</div>
    <p>12 teams qualify through a mix of auto-bids and at-large selections.</p>
    <div class="rules-table-wrap">
      <table class="rules-table">
        <thead><tr><th>Bid</th><th>Qualifier</th></tr></thead>
        <tbody>
          <tr><td>P6 Auto-Bid 1</td><td>Big XII conference champion</td></tr>
          <tr><td>P6 Auto-Bid 2</td><td>Big Ten conference champion</td></tr>
          <tr><td>P6 Auto-Bid 3</td><td>ACC conference champion</td></tr>
          <tr><td>P6 Auto-Bid 4</td><td>SEC conference champion</td></tr>
          <tr><td>P6 Auto-Bid 5</td><td>PAC conference champion</td></tr>
          <tr><td>P6 Auto-Bid 6</td><td>6IX conference champion</td></tr>
          <tr><td>Go6 Auto-Bid 1</td><td>Highest ranked Group of 6 conference champion</td></tr>
          <tr><td>Go6 Auto-Bid 2</td><td>Second highest ranked Group of 6 conference champion</td></tr>
          <tr><td>At-large 1-4</td><td>Four highest ranked non-auto-bid teams</td></tr>
        </tbody>
      </table>
    </div>
    <p>The CFP is not necessarily the top 12 teams in the nation. Group of 6 teams need some loving too.</p>
  </div>
</div>

<div class="rules-grid">
  <div class="rules-card rules-card-wide" style="--accent:#2563eb;">
    <div class="rules-card-title">Ranking System</div>
    <p>Work in progress. Current ranking framework:</p>
    <div class="rules-table-wrap">
      <table class="rules-table rules-table-ranking">
        <thead><tr><th>Category</th><th>Weight</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Wins</td><td>30%</td><td>Wins compared to the other 143 teams</td></tr>
          <tr><td>Points For</td><td>30%</td><td>PF compared to the other 143 teams</td></tr>
          <tr><td>SOS</td><td>10%</td><td>Quality of opponents; teams 51-144 are weighted the same</td></tr>
          <tr><td>Last Week</td><td>30%</td><td>Prior week ranking to reduce massive week-to-week fluctuations</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<div class="rules-grid rules-grid-thirds">
  <div class="rules-card" style="--accent:#991b1b;">
    <div class="rules-card-title">Tiebreakers</div>
    <p>Standings are determined by:</p>
    <div class="rules-pill-row">
      <span class="rules-pill">1. Conference Record</span>
      <span class="rules-pill">2. Head-to-Head</span>
      <span class="rules-pill">3. Total PF</span>
      <span class="rules-pill">4. Total Record</span>
    </div>
  </div>
  <div class="rules-card" style="--accent:#4a5a78;">
    <div class="rules-card-title">Draft Order</div>
    <p>Draft order is determined by Max PF at the conclusion of the full season, after Week 18.</p>
    <ul>
      <li>Conference champion picks 12th.</li>
      <li>Conference runner-up picks 11th.</li>
      <li>National champion, if different from conference champion, automatically picks 12th in his conference.</li>
    </ul>
  </div>
</div>
"""
    )


@st.cache_data(show_spinner="Calculating rankings through selected week...", max_entries=32)
def through_week(schedule: pd.DataFrame, scores: pd.DataFrame, week: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    schedule_part = schedule.loc[schedule["Week"].le(week)].copy()
    scores_part = scores.loc[scores["Week"].le(week)].copy()
    return schedule_part, scores_part


def rank_map(rankings: pd.DataFrame, poll_type: str, week: int) -> dict[str, int]:
    poll = rankings.loc[
        rankings["Type"].astype(str).eq(poll_type)
        & rankings["Week"].eq(week)
        & rankings["Rank"].notna()
    ]
    return {
        clean_text(row["Team"]): int(row["Rank"])
        for _, row in poll.iterrows()
    }


def ap_top25_for_week(rankings: Optional[pd.DataFrame], week: int) -> dict[str, int]:
    if rankings is None or rankings.empty:
        return {}
    if not {"Type", "Week", "Rank", "Team"}.issubset(rankings.columns):
        return {}

    poll = rankings.loc[rankings["Type"].astype(str).eq("AP Poll")].copy()
    if poll.empty:
        return {}

    poll["Week"] = pd.to_numeric(poll["Week"], errors="coerce")
    poll["Rank"] = pd.to_numeric(poll["Rank"], errors="coerce")
    poll = poll.loc[poll["Week"].eq(week) & poll["Rank"].notna()]
    poll = poll.loc[poll["Rank"].between(1, 25, inclusive="both")]
    return {
        clean_text(row["Team"]): int(row["Rank"])
        for _, row in poll.sort_values("Rank").iterrows()
    }


def latest_ap_top25(rankings: Optional[pd.DataFrame]) -> dict[str, int]:
    if rankings is None or rankings.empty:
        return {}
    if not {"Type", "Week"}.issubset(rankings.columns):
        return {}

    ap_poll = rankings.loc[rankings["Type"].astype(str).eq("AP Poll")].copy()
    if ap_poll.empty:
        return {}

    ap_poll["Week"] = pd.to_numeric(ap_poll["Week"], errors="coerce")
    weeks = ap_poll["Week"].dropna()
    if weeks.empty:
        return {}
    return ap_top25_for_week(rankings, int(weeks.max()))


def schedule_ap_top25(rankings: Optional[pd.DataFrame], game_week: int) -> dict[str, int]:
    previous_week = max(int(game_week) - 1, 0)
    previous_ranks = ap_top25_for_week(rankings, previous_week)
    return previous_ranks or latest_ap_top25(rankings)


def schedule_game_rank_sort(game: pd.Series, rankings: Optional[pd.DataFrame]) -> int:
    week = int(game["Week"]) if not pd.isna(game.get("Week")) else 0
    game_ranks = schedule_ap_top25(rankings, week)
    team_a_rank = rank_for_team(game.get("TeamA"), game_ranks) or 999
    team_b_rank = rank_for_team(game.get("TeamB"), game_ranks) or 999
    return min(team_a_rank, team_b_rank)


def rank_for_team(team: object, ap_ranks: Optional[dict[str, int]]) -> Optional[int]:
    if not ap_ranks:
        return None

    team_name = clean_text(team)
    rank = ap_ranks.get(team_name)
    if rank is None:
        folded = match_key(team_name)
        rank = next(
            (value for ranked_team, value in ap_ranks.items() if match_key(ranked_team) == folded),
            None,
        )
    return rank


def rank_prefix(team: object, ap_ranks: Optional[dict[str, int]]) -> str:
    rank = rank_for_team(team, ap_ranks)
    if rank is None or rank > 25:
        return ""
    return f"No. {rank} "


def trend_html(current_rank: int, previous_rank: Optional[int]) -> str:
    if previous_rank is None:
        return '<span class="trend-badge trend-new">NEW</span>'
    diff = previous_rank - current_rank
    if diff > 0:
        return f'<span class="trend-badge trend-up">▲ {diff}</span>'
    if diff < 0:
        return f'<span class="trend-badge trend-down">▼ {abs(diff)}</span>'
    return '<span class="trend-badge trend-flat">–</span>'


def team_stats_for_week(
    standings: pd.DataFrame,
    team: str,
) -> dict[str, object]:
    row = standings.loc[standings["team"].eq(team)]
    if row.empty:
        return {
            "record": "0-0",
            "conf_record": "0-0",
            "pf": 0.0,
        }
    row = row.iloc[0]
    return {
        "record": record_text(int(row["league_wins"]), int(row["league_losses"]), int(row["league_ties"])),
        "conf_record": record_text(int(row["conf_wins"]), int(row["conf_losses"]), int(row["conf_ties"])),
        "pf": float(row["league_pf"]),
    }


def last_game_html(
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    team: str,
    week: int,
) -> str:
    games = schedule.loc[
        schedule["Week"].eq(week)
        & (schedule["TeamA"].eq(team) | schedule["TeamB"].eq(team))
    ]
    if games.empty:
        return '<span class="last-game">Idle<span>Week off</span></span>'

    game = games.iloc[0]
    team_a = clean_text(game.get("TeamA"))
    team_b = clean_text(game.get("TeamB"))
    opponent = team_b if team_a == team else team_a
    rivalry = rivalry_name(game)
    scores_by_team_week = score_lookup(scores)
    team_score = scores_by_team_week.get((match_key(team), week))
    opponent_score = scores_by_team_week.get((match_key(opponent), week))
    if team_score is None or opponent_score is None:
        return f'<span class="last-game">vs {esc(opponent)}<span>{esc(rivalry) if rivalry else "Pending"}</span></span>'

    result = "Win" if team_score > opponent_score else "Loss" if team_score < opponent_score else "Tie"
    return f"""
<span class="last-game">
  {result} vs {esc(opponent)}
  <span>{team_score:,.2f}-{opponent_score:,.2f}{f' | {esc(rivalry)}' if rivalry else ''}</span>
</span>
"""


def poll_rows_html(
    poll: pd.DataFrame,
    standings: pd.DataFrame,
    previous_ranks: dict[str, int],
    teams: dict[str, dict[str, str]],
    conferences: pd.DataFrame,
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    week: int,
    include_last_game: bool,
    dynasty_values: Optional[dict[str, float]] = None,
    show_final_metric: bool = True,
) -> str:
    rows = []
    poll = poll.sort_values(["Rank", "Team"])
    for _, item in poll.iterrows():
        rank = int(item["Rank"])
        team = clean_text(item["Team"])
        info = teams.get(team, {})
        conf = clean_text(info.get("conference"))
        conf_logo = conference_logo(conferences, conf)
        team_logo = clean_text(info.get("logo"))
        nickname = clean_text(info.get("nickname"))
        owner = clean_text(info.get("owner"))
        stats = team_stats_for_week(standings, team)
        previous_rank = previous_ranks.get(team)
        last_rank = previous_rank if previous_rank is not None else "-"
        last_game = last_game_html(schedule, scores, team, week) if include_last_game else ""
        final_metric = (
            f"{dynasty_values.get(team, 0):,.0f}"
            if dynasty_values is not None
            else f'{stats["pf"]:,.2f}'
        )

        extra_cells = ""
        if include_last_game:
            extra_cells = f"""
  <td class="poll-metric">{last_rank}</td>
  <td>{trend_html(rank, previous_rank)}</td>
  <td>{last_game}</td>
"""

        rows.append(
            f"""
<tr>
  <td class="poll-rank-cell"><span class="poll-rank">{rank}</span></td>
  <td class="poll-logo-cell">{f'<img class="poll-logo" src="{esc(conf_logo)}" alt="{esc(conf)}">' if conf_logo else ''}</td>
  <td>
    <div class="poll-team">
      {f'<img class="poll-team-logo" src="{esc(team_logo)}" alt="{esc(team)}">' if team_logo else ''}
      <div>
        <div class="poll-team-name">{esc(team)}</div>
        <div class="poll-team-sub">{esc(nickname_owner(nickname, owner))}</div>
      </div>
    </div>
  </td>
  <td class="poll-metric">{stats["record"]}</td>
  <td class="poll-metric">{stats["conf_record"]}</td>
  {f'<td class="poll-metric">{final_metric}</td>' if show_final_metric else ''}
  {extra_cells}
</tr>
"""
        )
    return "".join(rows)


def rankings_detail_table_html(frame: pd.DataFrame) -> str:
    numeric_columns = {
        "Rank", "Conf Rank", "Teams", "Total Value", "Player Value",
        "Draft Pick Value", "Matched Players", "Unmatched Players",
    }
    headers = "".join(
        f'<th class="{"numeric" if column in numeric_columns else ""}">{esc(column)}</th>'
        for column in frame.columns
    )
    rows = []
    for _, row in frame.iterrows():
        cells = []
        for column in frame.columns:
            value = row[column]
            if column in {"Total Value", "Player Value", "Draft Pick Value"} and not pd.isna(value):
                label = f"{float(value):,.0f}"
            elif column in numeric_columns and not pd.isna(value):
                label = f"{int(value):,}"
            else:
                label = clean_text(value, "-")
            cells.append(
                f'<td class="{"numeric" if column in numeric_columns else ""}">{esc(label)}</td>'
            )
        rows.append(f"<tr>{''.join(cells)}</tr>")
    return (
        '<table class="rankings-detail-table">'
        f"<thead><tr>{headers}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )


@loading_spinner("Calculating and loading rankings...")
def render_rankings(
    rankings: pd.DataFrame,
    schedule: pd.DataFrame,
    scores: pd.DataFrame,
    schools: pd.DataFrame,
    conferences: pd.DataFrame,
    rosters: pd.DataFrame,
    draft_picks: pd.DataFrame,
) -> None:
    weeks = ranking_weeks(rankings)
    if not weeks:
        weeks = [0]

    selected_week = st.selectbox(
        "Week",
        weeks,
        index=latest_completed_week_index(weeks, scores),
        key="rankings_week",
        format_func=lambda week: "Preseason" if week == 0 else week_label(week),
    )
    selected_week = int(selected_week)
    schedule_part, scores_part = through_week(schedule, scores, selected_week)
    standings = build_standings(schedule_part, scores_part, schools)
    teams = team_lookup(schools)

    ap_poll = rankings.loc[
        rankings["Type"].astype(str).eq("AP Poll")
        & rankings["Week"].eq(selected_week)
        & rankings["Rank"].notna()
    ].copy()
    dynasty_poll = build_dynasty_coaches_poll(rosters, draft_picks, schools)
    coaches_poll = dynasty_poll[["Team", "Rank"]].copy()
    previous_ap = rank_map(rankings, "AP Poll", selected_week - 1)

    ap_top = ap_poll.loc[ap_poll["Rank"].le(25)].copy()
    ap_orv = (
        ap_poll.loc[ap_poll["Rank"].eq(26), "Team"]
        .dropna()
        .map(clean_text)
    )
    ap_orv = sorted(set(team for team in ap_orv if team))
    coaches_top = coaches_poll.loc[coaches_poll["Rank"].le(25)].copy()
    coaches_orv = sorted(
        coaches_poll.loc[coaches_poll["Rank"].between(26, 35, inclusive="both"), "Team"]
        .dropna()
        .map(clean_text)
        .unique()
    )
    title_week = "Preseason" if selected_week == 0 else f"Week {selected_week}"

    ap_rows = poll_rows_html(
        ap_top,
        standings,
        previous_ap,
        teams,
        conferences,
        schedule,
        scores,
        selected_week,
        include_last_game=True,
    )
    coaches_rows = poll_rows_html(
        coaches_top,
        standings,
        {},
        teams,
        conferences,
        schedule,
        scores,
        selected_week,
        include_last_game=False,
        dynasty_values=dict(zip(dynasty_poll["Team"], dynasty_poll["TotalValue"])),
        show_final_metric=False,
    )
    orv_text = ", ".join(ap_orv) if ap_orv else "None"
    coaches_panel = ""
    if not coaches_top.empty:
        coaches_panel = f"""
  <div class="poll-panel">
    <div class="poll-header">
      <div>
        <div class="poll-title">Coaches Poll</div>
        <div class="poll-subtitle">{esc(title_week)} Rankings</div>
      </div>
    </div>
    <div class="poll-table-wrap">
      <table class="poll-table coaches">
        <thead>
          <tr>
            <th>Rk</th>
            <th>Conf</th>
            <th>Team</th>
            <th>Total</th>
            <th>Conf</th>
          </tr>
        </thead>
        <tbody>{coaches_rows}</tbody>
      </table>
    </div>
    <div class="orv-box">
      <div class="orv-title">Other Receiving Votes</div>
      <div class="orv-text">{esc(", ".join(coaches_orv) if coaches_orv else "None")}</div>
    </div>
  </div>
"""

    st.html(
        f"""
<div class="rankings-layout {'ap-only' if coaches_top.empty else ''}">
  <div class="poll-panel">
    <div class="poll-header">
      <div>
        <div class="poll-title">AP Poll</div>
        <div class="poll-subtitle">{esc(title_week)} Rankings</div>
      </div>
    </div>
    <div class="poll-table-wrap">
      <table class="poll-table ap">
        <thead>
          <tr>
            <th>Rk</th>
            <th>Conf</th>
            <th>Team</th>
            <th>Record</th>
            <th>Conf</th>
            <th>PF</th>
            <th>Last Week</th>
            <th>Trend</th>
            <th>Last Game</th>
          </tr>
        </thead>
        <tbody>{ap_rows}</tbody>
      </table>
    </div>
    <div class="orv-box">
      <div class="orv-title">Other Receiving Votes</div>
      <div class="orv-text">{esc(orv_text)}</div>
    </div>
  </div>
  {coaches_panel}
</div>
"""
    )
    full_poll = dynasty_poll[
        [
            "Rank", "ConferenceRank", "Team", "Conference", "Format",
            "TotalValue", "PlayerValue", "DraftPickValue",
            "MatchedPlayers", "UnmatchedPlayers",
        ]
    ].rename(
        columns={
            "ConferenceRank": "Conf Rank",
            "TotalValue": "Total Value",
            "PlayerValue": "Player Value",
            "DraftPickValue": "Draft Pick Value",
            "MatchedPlayers": "Matched Players",
            "UnmatchedPlayers": "Unmatched Players",
        }
    )
    conference_poll = (
        dynasty_poll.groupby("Conference", as_index=False)
        .agg(
            Teams=("Team", "count"),
            PlayerValue=("PlayerValue", "sum"),
            DraftPickValue=("DraftPickValue", "sum"),
            TotalValue=("TotalValue", "sum"),
            MatchedPlayers=("MatchedPlayers", "sum"),
            UnmatchedPlayers=("UnmatchedPlayers", "sum"),
        )
        .sort_values("TotalValue", ascending=False)
        .reset_index(drop=True)
    )
    conference_poll["Rank"] = range(1, len(conference_poll) + 1)
    conference_poll = conference_poll[
        [
            "Rank", "Conference", "Teams", "TotalValue", "PlayerValue",
            "DraftPickValue", "MatchedPlayers", "UnmatchedPlayers",
        ]
    ].rename(
        columns={
            "TotalValue": "Total Value",
            "PlayerValue": "Player Value",
            "DraftPickValue": "Draft Pick Value",
            "MatchedPlayers": "Matched Players",
            "UnmatchedPlayers": "Unmatched Players",
        }
    )

    with st.expander("Conference Totals", expanded=False):
        st.html(rankings_detail_table_html(conference_poll))
    with st.expander("Full 144-Team Coaches Poll", expanded=False):
        st.html(rankings_detail_table_html(full_poll))
    unmatched = unmatched_dynasty_players(rosters)
    if not unmatched.empty:
        with st.expander(f"Review {len(unmatched):,} Unmatched Players"):
            st.caption(
                "These rostered players receive zero dynasty value because their names "
                "did not match the current DynastyProcess player file."
            )
            st.html(rankings_detail_table_html(unmatched))


@loading_spinner("Loading conference draft board...")
def render_draft_board(
    drafts: pd.DataFrame,
    schools: pd.DataFrame,
    conferences: pd.DataFrame,
    season: int,
    conference: Optional[str] = None,
) -> None:
    if drafts.empty:
        under_construction("Draft Board")
        return

    board = drafts.loc[pd.to_numeric(drafts["Year"], errors="coerce").eq(season)].copy()
    if conference is not None:
        board = board.loc[board["Conference"].astype(str).eq(conference)].copy()
    if board.empty:
        label = f"{season} {conference} Draft Board" if conference else f"{season} Draft Board"
        under_construction(label)
        return

    board["Round"] = pd.to_numeric(board["Round"], errors="coerce")
    board["Pick"] = pd.to_numeric(board["Pick"], errors="coerce")
    board["Conference"] = board["Conference"].astype(str)
    board["Type"] = board["Type"].map(clean_text).replace("", "Draft")
    board["_type_order"] = board["Type"].map(
        {"Rookie": 0, "Start-Up": 1, "Startup": 1}
    ).fillna(2)
    board["_conference_order"] = board["Conference"].map(
        {name: index for index, name in enumerate(LEAGUE_ROSTER_ORDER)}
    ).fillna(999)
    board = board.sort_values(
        ["_conference_order", "Conference", "_type_order", "Type", "Round", "Pick", "Team", "Player"],
        na_position="last",
    )

    teams = team_lookup(schools)
    conf_logo = conference_logo(conferences, conference) if conference else LEAGUE_LOGO
    rounds = int(board["Round"].nunique())
    picks = int(len(board))
    drafted = int(board["Player"].map(clean_text).ne("").sum())
    draft_types = board["Type"].drop_duplicates().tolist()
    board_title = f"{conference} Draft Board" if conference else "League Draft Board"
    board_kicker = f"{season} Conference Draft" if conference else f"{season} League Draft"

    st.html(
        f"""
<div class="draft-hero" style="--accent:#c8102e;">
  <div class="draft-hero-main">
    <img src="{esc(conf_logo)}" alt="{esc(board_title)}">
    <div>
      <div class="draft-kicker">{esc(board_kicker)}</div>
      <div class="draft-title">{esc(board_title)}</div>
    </div>
  </div>
  <div class="draft-meta">
    <span class="draft-chip">{rounds} Rounds</span>
    <span class="draft-chip">{picks} Picks</span>
    <span class="draft-chip">{drafted} Drafted</span>
    {''.join(f'<span class="draft-chip">{esc(draft_type)}</span>' for draft_type in draft_types)}
  </div>
</div>
"""
    )

    groups = [(conference, board)] if conference else [
        (conf, conf_board)
        for conf, conf_board in board.groupby("Conference", sort=False)
    ]

    sections = []
    for group_conference, group_board in groups:
        if conference is None:
            group_logo = conference_logo(conferences, clean_text(group_conference))
            sections.append(
                f"""
<div class="draft-round-title"><img class="conf-logo" src="{esc(group_logo)}" alt="{esc(group_conference)}"><span>{esc(group_conference)}</span><span></span></div>
"""
            )
        for draft_type, type_board in group_board.groupby("Type", sort=False):
            sections.append(
                f'<div class="draft-type-heading"><span>{esc(draft_type)} Draft</span><span></span></div>'
            )
            for round_number, round_rows in type_board.groupby("Round", dropna=False):
                round_label = "Round -" if pd.isna(round_number) else f"Round {int(round_number)}"
                cards = []
                for _, row in round_rows.iterrows():
                    team = clean_text(row.get("Team"))
                    player = clean_text(row.get("Player"))
                    pick = row.get("Pick")
                    pick_label = "-" if pd.isna(pick) else str(int(pick))
                    info = teams.get(team, {})
                    logo = clean_text(info.get("logo"))
                    color = esc(info.get("color"), "#1a2030")
                    cards.append(
                        f"""
<div class="draft-card" style="--team-color:{color};">
  <div class="draft-card-top">
    <span class="draft-pick">{esc(pick_label)}</span>
    {f'<img class="draft-team-logo" src="{esc(logo)}" alt="{esc(team)}">' if logo else '<span></span>'}
  </div>
  <img class="draft-player-photo" src="{esc(player_picture(player))}" alt="{esc(player, 'Player')}" onerror="{player_picture_fallback()}">
  <div class="draft-player {'draft-empty-player' if not player else ''}">{esc(player, 'TBD')}</div>
</div>
"""
                    )

                sections.append(
                    f"""
<section class="draft-round">
  <div class="draft-round-title"><span>{esc(round_label)}</span><span></span></div>
  <div class="draft-grid">{''.join(cards)}</div>
</section>
"""
                )

    st.html("".join(sections))


@loading_spinner("Loading league draft board...")
def render_league_draft_board(
    drafts: pd.DataFrame,
    schools: pd.DataFrame,
    conferences: pd.DataFrame,
    season: int,
) -> None:
    if drafts.empty:
        under_construction(f"{season} League Draft Board")
        return

    board = drafts.loc[pd.to_numeric(drafts["Year"], errors="coerce").eq(season)].copy()
    if board.empty:
        under_construction(f"{season} League Draft Board")
        return

    board["Round"] = pd.to_numeric(board["Round"], errors="coerce")
    board["Pick"] = pd.to_numeric(board["Pick"], errors="coerce")
    board["Conference"] = board["Conference"].map(clean_text)
    board["Type"] = board["Type"].map(clean_text).replace("", "Draft")
    board["_type_order"] = board["Type"].map(
        {"Rookie": 0, "Start-Up": 1, "Startup": 1}
    ).fillna(2)
    board = board.sort_values(
        ["_type_order", "Type", "Round", "Pick", "Team", "Player"],
        na_position="last",
    )

    teams = team_lookup(schools)

    st.html(
        f"""
<div class="draft-hero" style="--accent:#c8102e;">
  <div class="draft-hero-main">
    <img src="{LEAGUE_LOGO}" alt="{esc(LEAGUE_NAME)}">
    <div>
      <div class="draft-kicker">{season} League Draft</div>
      <div class="draft-title">League Draft Board</div>
    </div>
  </div>
</div>
"""
    )

    phase_groups = []
    for draft_type, draft_type_board in board.groupby("Type", sort=False):
        phase_color = "#7dd3fc" if match_key(draft_type) in {"start-up", "startup"} else "#f2cf68"
        phase_active_conferences = set(draft_type_board["Conference"])
        phase_conference_order = [
            conference
            for conference in LEAGUE_ROSTER_ORDER
            if conference in phase_active_conferences
        ]
        phase_conference_order.extend(
            sorted(phase_active_conferences.difference(phase_conference_order))
        )
        phase_groups.append(
            {
                "type": draft_type,
                "color": phase_color,
                "conferences": phase_conference_order,
                "board": draft_type_board,
            }
        )

    conference_count = max(
        sum(len(group["conferences"]) for group in phase_groups),
        1,
    )
    board_size_class = (
        "roomy"
        if conference_count <= 3
        else "medium"
        if conference_count <= 6
        else "compact"
    )
    phase_headers = []
    columns = []
    for phase_index, group in enumerate(phase_groups):
        phase_class = "phase-start" if phase_index > 0 else ""
        phase_headers.append(
            f"""
<div class="league-draft-phase-title {phase_class}" style="--phase-color:{group['color']}; grid-column: span {len(group['conferences'])};">
  <span>{esc(group['type'])} Draft</span><span></span>
</div>
"""
        )
        for conference_index, conference in enumerate(group["conferences"]):
            conference_board = group["board"].loc[group["board"]["Conference"].eq(conference)]
            logo = conference_logo(conferences, conference)
            pick_rows = []
            for _, row in conference_board.iterrows():
                team = clean_text(row.get("Team"))
                player = clean_text(row.get("Player"), "TBD")
                info = teams.get(team, {})
                team_logo = clean_text(info.get("logo"))
                color = esc(info.get("color"), "#1a2030")
                round_number = row.get("Round")
                pick_number = row.get("Pick")
                round_label = "-" if pd.isna(round_number) else str(int(round_number))
                pick_label = "-" if pd.isna(pick_number) else str(int(pick_number))
                draft_slot = f"{round_label}.{pick_label}"
                pick_rows.append(
                    f"""
<div class="league-draft-pick" style="--team-color:{color};">
  <div class="league-draft-pick-top">
    <span class="league-draft-pick-number">{esc(draft_slot)}</span>
    {f'<img src="{esc(team_logo)}" alt="{esc(team)}" title="{esc(team)}">' if team_logo else '<span></span>'}
    <img class="league-draft-player-photo" src="{esc(player_picture(player))}" alt="{esc(player)}" onerror="{player_picture_fallback()}">
  </div>
  <div class="league-draft-player">{esc(player)}</div>
</div>
"""
                )

            column_class = "phase-start" if phase_index > 0 and conference_index == 0 else ""
            columns.append(
                f"""
<section class="league-draft-column {column_class}">
  <div class="league-draft-header">
    {f'<img src="{esc(logo)}" alt="{esc(conference)}">' if logo else ''}
    <span>{esc(conference)}</span>
  </div>
  {''.join(pick_rows)}
</section>
"""
            )

    st.html(
        f"""
<div class="league-draft-wrap">
  <div class="league-draft-phase-headings" style="--conference-count:{conference_count};">{''.join(phase_headers)}</div>
  <div class="league-draft-board {board_size_class}" style="--conference-count:{conference_count};">{''.join(columns)}</div>
</div>
"""
    )


@loading_spinner("Loading conference rosters...")
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
        per_team = len(pos_rosters) / len(teams) if teams else 0

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
                player_name = player[idx] if idx < len(player) else ""
                if player_name:
                    cells.append(
                        f"""
<td>
  <div class="roster-player-cell">
    <img src="{esc(player_picture(player_name))}" alt="{esc(player_name)}" onerror="{player_picture_fallback()}">
    <span>{esc(player_name)}</span>
  </div>
</td>
"""
                    )
                else:
                    cells.append("<td></td>")
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        st.html(
            f"""
<div class="roster-section">
  <div class="position-label"><span>{POSITION_LABELS.get(position, position)} · {per_team:.1f} Per Team</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
        )


def render_conference_draft_pick_matrix(
    rosters: pd.DataFrame,
    draft_picks: pd.DataFrame,
) -> None:
    if rosters.empty or draft_picks.empty:
        return

    league_name = first_value(rosters, "league_name")
    league_picks = draft_picks.loc[draft_picks["league_name"].eq(league_name)].copy()
    if league_picks.empty:
        return

    teams = (
        rosters[
            ["roster_id", "team_name", "team_logo", "team_color"]
        ]
        .drop_duplicates("roster_id")
        .copy()
    )
    teams["roster_id"] = pd.to_numeric(teams["roster_id"], errors="coerce")
    teams = teams.dropna(subset=["roster_id"]).sort_values("team_name")
    teams["roster_id"] = teams["roster_id"].astype(int)
    team_map = teams.set_index("roster_id").to_dict("index")

    team_picks: dict[int, list[dict[str, object]]] = {}
    max_picks = 0
    for _, team in teams.iterrows():
        roster_id = int(team["roster_id"])
        owned = league_picks.loc[
            league_picks["owner_roster_id"].eq(roster_id)
        ].sort_values(["season", "round", "original_roster_id"])
        team_picks[roster_id] = owned.to_dict("records")
        max_picks = max(max_picks, len(owned))

    headers = []
    for _, team in teams.iterrows():
        team_name = clean_text(team.get("team_name"))
        logo = clean_text(team.get("team_logo"))
        color = esc(team.get("team_color"), "#1a2030")
        headers.append(
            f"""
<th class="team-head" style="--team-color:{color};">
  {f'<img src="{esc(logo)}" alt="{esc(team_name)}">' if logo else ''}
</th>
"""
        )

    body_rows = []
    round_labels = {
        1: "1st Round",
        2: "2nd Round",
        3: "3rd Round",
    }
    for index in range(max_picks):
        cells = []
        for _, team in teams.iterrows():
            picks = team_picks.get(int(team["roster_id"]), [])
            if index >= len(picks):
                cells.append("<td></td>")
                continue
            pick = picks[index]
            original = team_map.get(int(pick["original_roster_id"]), {})
            origin_name = clean_text(
                original.get("team_name"),
                f"Roster {int(pick['original_roster_id'])}",
            )
            origin_logo = clean_text(original.get("team_logo"))
            round_number = int(pick["round"])
            round_label = round_labels.get(round_number, f"{round_number}th Round")
            cells.append(
                f"""
<td>
  <div class="roster-player-cell">
    {f'<img src="{esc(origin_logo)}" alt="{esc(origin_name)}">' if origin_logo else ''}
    <span>{int(pick["season"])} {esc(round_label)}</span>
  </div>
</td>
"""
            )
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    st.html(
        f"""
<div class="roster-section">
  <div class="position-label"><span>Draft Picks</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
    )


@loading_spinner("Loading league rosters...")
def render_league_roster_matrix(
    rosters: pd.DataFrame,
    conferences: pd.DataFrame,
    preview_missing_conferences: bool = False,
) -> None:
    player_values, _ = load_dynasty_asset_values()
    player_values = player_values.copy()
    player_values["_player_key"] = player_values["player"].map(dynasty_player_key)
    player_values = player_values.drop_duplicates("_player_key", keep="first")
    value_lookup = player_values.set_index("_player_key")

    def player_value(player_name: str, column: str) -> str:
        key = dynasty_player_key(player_name)
        if not key or key not in value_lookup.index:
            return "-"
        value = pd.to_numeric(value_lookup.at[key, column], errors="coerce")
        if pd.isna(value):
            return "-"
        return f"{float(value):,.0f}"

    active_conferences = set(rosters["league_name"])
    if preview_missing_conferences:
        conference_order = [
            conference if conference in active_conferences else f"SEC Preview {index + 1}"
            for index, conference in enumerate(LEAGUE_ROSTER_ORDER)
        ]
    else:
        conference_order = [
            conference for conference in LEAGUE_ROSTER_ORDER if conference in active_conferences
        ]
    conference_sources = {
        display_conference: display_conference if display_conference in active_conferences else "SEC"
        for display_conference in conference_order
    }
    conference_logos = {
        display_conference: conference_logo(conferences, source_conference)
        for display_conference, source_conference in conference_sources.items()
    }

    for position in POSITIONS:
        pos_rosters = rosters.loc[rosters["position"].eq(position)].copy()
        if pos_rosters.empty:
            continue
        unique_players = pos_rosters["player_id"].nunique()
        team_count = rosters["team_name"].nunique()
        per_team = len(pos_rosters) / team_count if team_count else 0

        rows = []
        for player_id, player_rows in pos_rosters.groupby("player_id"):
            player_name = first_value(player_rows, "player_name", str(player_id))
            row = {
                "player_id": player_id,
                "player_name": player_name,
                "taken_count": player_rows["league_name"].nunique(),
                "FLX": player_value(player_name, "value_1qb"),
                "SFLX": player_value(player_name, "value_2qb"),
            }
            for display_conference, source_conference in conference_sources.items():
                match = player_rows.loc[player_rows["league_name"].eq(source_conference)]
                row[display_conference] = first_value(match, "team_logo", "")
                row[f"{display_conference}_team"] = first_value(match, "team_name", "")
            rows.append(row)

        matrix = pd.DataFrame(rows)
        matrix["_sflx_sort"] = pd.to_numeric(
            matrix["SFLX"].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ).fillna(-1)
        matrix = matrix.sort_values(
            ["taken_count", "_sflx_sort", "player_name"],
            ascending=[False, False, True],
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
        headers.extend(
            [
                '<th class="value-col">FLX</th>',
                '<th class="value-col">SFLX</th>',
                '<th class="taken-col">Count</th>',
            ]
        )

        body_rows = []
        for _, row in matrix.iterrows():
            cells = [
                f"""
<td class="player-col">
  <div class="league-player">
    <img src="{esc(player_picture(row["player_name"]))}" alt="{esc(row["player_name"])}" onerror="{player_picture_fallback()}">
    <span>{esc(row["player_name"])}</span>
  </div>
</td>
"""
            ]
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
            cells.append(f'<td class="value-col">{esc(row["FLX"])}</td>')
            cells.append(f'<td class="value-col">{esc(row["SFLX"])}</td>')
            cells.append(
                f'<td class="taken-col"><span class="taken-pill" style="background:{taken_color(taken_count, len(conference_order))};">{taken_count}</span></td>'
            )
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        st.html(
            f"""
<div class="roster-section">
  <div class="position-label"><span>{POSITION_LABELS.get(position, position)} · {unique_players} Unique · {per_team:.1f} Per Team</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table league-matrix">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
        )


def unique_player_download(rosters: pd.DataFrame) -> pd.DataFrame:
    player_rows = rosters.loc[rosters["position"].isin(POSITIONS)].copy()
    if player_rows.empty:
        return pd.DataFrame(
            columns=[
                "PlayerID",
                "Player",
                "Position",
                "NFLTeam",
                "InjuryStatus",
                "TakenCount",
                "Leagues",
                "Teams",
                "HeadshotURL",
            ]
        )

    rows = []
    for player_id, group in player_rows.groupby("player_id", dropna=False):
        leagues = sorted(group["league_name"].dropna().astype(str).unique())
        teams = sorted(group["team_name"].dropna().astype(str).unique())
        rows.append(
            {
                "PlayerID": player_id,
                "Player": first_value(group, "player_name", str(player_id)),
                "Position": first_value(group, "position"),
                "NFLTeam": first_value(group, "nfl_team"),
                "InjuryStatus": first_value(group, "injury_status"),
                "TakenCount": len(leagues),
                "Leagues": ", ".join(leagues),
                "Teams": ", ".join(teams),
                "HeadshotURL": "",
            }
        )

    return pd.DataFrame(rows).sort_values(["Position", "Player"]).reset_index(drop=True)


def current_roster_season() -> int:
    today = datetime.now()
    return today.year if today.month >= 3 else today.year - 1


@st.cache_data(show_spinner="Building historical roster snapshot...", max_entries=8)
def historical_roster_snapshot(
    starters: pd.DataFrame,
    schools: pd.DataFrame,
    season: int,
) -> pd.DataFrame:
    empty_columns = [
        "team_name",
        "league_name",
        "player_name",
        "player_id",
        "position",
        "roster_spot",
        "nfl_team",
        "injury_status",
        "team_logo",
        "team_wordmark",
        "team_color",
        "team_color2",
        "roster_id",
        "Owner",
    ]
    if starters.empty:
        return pd.DataFrame(columns=empty_columns)

    snapshot = starters.loc[
        pd.to_numeric(starters["Year"], errors="coerce").eq(season)
        & pd.to_numeric(starters["Week"], errors="coerce").eq(18)
    ].copy()
    if snapshot.empty:
        return pd.DataFrame(columns=empty_columns)

    snapshot["Conference"] = snapshot["Conference"].replace({"6IX": "G6", "The 12": "F12"})
    snapshot = snapshot.drop_duplicates(["Team", "Player"], keep="last")
    school_branding = schools.copy()
    school_branding["Conference"] = school_branding["Conference"].replace({"6IX": "G6", "The 12": "F12"})
    school_branding = school_branding.rename(
        columns={
            "School": "Team",
            "Logo": "team_logo",
            "Wordmark": "team_wordmark",
            "Color": "team_color",
            "Color2": "team_color2",
            "TeamID": "roster_id",
        }
    )
    branding_columns = [
        column
        for column in ["Team", "team_logo", "team_wordmark", "team_color", "team_color2", "roster_id", "Owner"]
        if column in school_branding.columns
    ]
    snapshot = snapshot.merge(
        school_branding[branding_columns].drop_duplicates("Team"),
        on="Team",
        how="left",
    )
    snapshot["team_name"] = snapshot["Team"]
    snapshot["league_name"] = snapshot["Conference"]
    snapshot["player_name"] = snapshot["Player"]
    snapshot["player_id"] = snapshot.get("PlayerID", snapshot["Player"]).fillna(snapshot["Player"])
    snapshot["position"] = snapshot["Position"]
    snapshot["roster_spot"] = snapshot.get(
        "RosterSpot",
        pd.Series("Starter", index=snapshot.index),
    ).fillna("Bench")
    snapshot["nfl_team"] = ""
    snapshot["injury_status"] = ""
    snapshot["team_logo"] = snapshot.get("team_logo", pd.Series(index=snapshot.index, dtype=object)).fillna("")
    snapshot["team_wordmark"] = snapshot.get("team_wordmark", pd.Series(index=snapshot.index, dtype=object)).fillna("")
    snapshot["team_color"] = snapshot.get("team_color", pd.Series(index=snapshot.index, dtype=object)).fillna("#1a2030")
    snapshot["team_color2"] = snapshot.get("team_color2", pd.Series(index=snapshot.index, dtype=object)).fillna("#c8102e")
    snapshot["Owner"] = snapshot.get("Owner", pd.Series(index=snapshot.index, dtype=object)).fillna("")
    return snapshot.reset_index(drop=True)


def render_roster_snapshot_banner(season: int, is_current: bool) -> None:
    title = f"{season} Current Roster" if is_current else f"{season} Final Roster Snapshot"
    pill = "Current · Mar-Feb" if is_current else "Week 18"
    accent = "#166534" if is_current else "#4a5a78"
    st.html(
        f"""
<div class="roster-snapshot-banner" style="--accent:{accent};">
  <div class="roster-snapshot-title">{esc(title)}</div>
  <div class="roster-snapshot-pill">{esc(pill)}</div>
</div>
"""
    )


def render_team_hero(rosters: pd.DataFrame, team_name: str, record: str = "") -> None:
    team = rosters.loc[rosters["team_name"].eq(team_name)].copy()
    if team.empty:
        st.warning("No roster rows found for this team.")
        return

    color = first_value(team, "team_color", "#1a2030")
    color2 = first_value(team, "team_color2", "#c8102e")
    logo = first_value(team, "team_logo", LEAGUE_LOGO)
    wordmark = first_value(team, "team_wordmark", "")
    conference = first_value(team, "league_name", "")
    owner = first_value(team, "Owner", "")
    hero_image = wordmark or logo

    st.html(
        f"""
<div class="team-hero" style="--team-color:{esc(color)};--team-color2:{esc(color2)};">
  <div>
    <div class="team-hero-sub">{esc(conference)} Roster</div>
    <div class="team-hero-title">{esc(team_name)}</div>
    {f'<div class="team-hero-record">{esc(record)}</div>' if record else ''}
    {f'<div class="team-hero-owner">Owner · {esc(owner)}</div>' if owner else ''}
  </div>
  <img class="team-hero-wordmark" src="{esc(hero_image)}" alt="{esc(team_name)}">
  <img class="team-hero-logo" src="{esc(logo)}" alt="{esc(team_name)}">
</div>
"""
    )


@loading_spinner("Loading team roster...")
def render_team_roster(
    rosters: pd.DataFrame,
    team_name: str,
    draft_picks: Optional[pd.DataFrame] = None,
) -> None:
    team = rosters.loc[rosters["team_name"].eq(team_name)].copy()
    if team.empty:
        st.warning("No roster rows found for this team.")
        return

    color = first_value(team, "team_color", "#1a2030")
    team["status_sort"] = team["roster_spot"].map(ROSTER_STATUS_ORDER).fillna(9)
    team["position_sort"] = team["position"].map({position: index for index, position in enumerate(POSITIONS)}).fillna(9)
    status_groups = [
        ("Starter", "Starters"),
        ("Bench", "Bench"),
        ("Taxi", "Taxi Squad"),
        ("Reserve", "Injured Reserve"),
    ]
    cards = []

    for roster_spot, label in status_groups:
        group = (
            team.loc[team["roster_spot"].eq(roster_spot)]
            .dropna(subset=["player_name"])
            .sort_values(["position_sort", "player_name"])
        )
        if group.empty:
            continue
        rows = []
        for _, player in group.iterrows():
            injury = clean_text(player.get("injury_status"))
            position = clean_text(player.get("position"))
            display_position = position if roster_spot == "Starter" else {
                "Bench": "Bench",
                "Reserve": "IR",
                "Taxi": "Taxi",
            }.get(roster_spot, position)
            position_color = {
                "QB": "#ef4444",
                "RB": "#f97316",
                "WR": "#eab308",
                "TE": "#22c55e",
                "Bench": "#e5e7eb",
                "IR": "#fee2e2",
                "Taxi": "#dbeafe",
            }.get(display_position, "#e5e7eb")
            rows.append(
                f"""
<div class="team-roster-player">
  <img src="{esc(player_picture(player.get("player_name")))}" alt="{esc(player.get("player_name"))}" onerror="{player_picture_fallback()}">
  <div>
    <div class="team-roster-player-name">{esc(player.get("player_name"))}</div>
    <div class="team-roster-player-meta">
      <span class="position-chip" style="background:{position_color};">{esc(display_position)}</span>
      {f'<span class="nfl-chip">{esc(player.get("nfl_team"))}</span>' if clean_text(player.get("nfl_team")) else ''}
      {f'<span class="injury-chip">{esc(injury[:1].upper())}</span>' if injury else ''}
    </div>
  </div>
  <span class="nfl-chip">{len(rows) + 1}</span>
</div>
"""
            )

        cards.append(
            f"""
<section class="team-roster-status" style="--team-color:{esc(color)};">
  <div class="team-roster-status-title">
    <span>{esc(label)}</span>
    <span>{len(group)}</span>
  </div>
  {''.join(rows) if rows else '<div class="team-roster-empty">No players</div>'}
</section>
"""
        )

    if draft_picks is not None and not draft_picks.empty:
        league_name = first_value(team, "league_name")
        roster_ids = pd.to_numeric(team["roster_id"], errors="coerce").dropna()
        if not roster_ids.empty:
            roster_id = int(roster_ids.iloc[0])
            owned_picks = draft_picks.loc[
                draft_picks["league_name"].eq(league_name)
                & draft_picks["owner_roster_id"].eq(roster_id)
            ].sort_values(["season", "round", "original_roster_id"])

            league_rosters = rosters.loc[rosters["league_name"].eq(league_name)].copy()
            league_rosters["roster_id"] = pd.to_numeric(league_rosters["roster_id"], errors="coerce")
            league_rosters = league_rosters.dropna(subset=["roster_id"])
            league_rosters["roster_id"] = league_rosters["roster_id"].astype(int)
            team_map = (
                league_rosters.drop_duplicates("roster_id")
                .set_index("roster_id")
                .to_dict("index")
            )

            pick_rows = []
            for _, pick in owned_picks.iterrows():
                original = team_map.get(int(pick["original_roster_id"]), {})
                origin_name = clean_text(
                    original.get("team_name"),
                    f"Roster {int(pick['original_roster_id'])}",
                )
                origin_logo = clean_text(original.get("team_logo"))
                pick_rows.append(
                    f"""
<div class="team-roster-player">
  {f'<img class="draft-pick-roster-logo" src="{esc(origin_logo)}" alt="{esc(origin_name)}">' if origin_logo else '<span></span>'}
  <div>
    <div class="team-roster-player-name">{int(pick["season"])} Round {int(pick["round"])}</div>
    <div class="team-roster-player-meta">
      <span class="nfl-chip">{esc(origin_name)} Pick</span>
    </div>
  </div>
  <span class="nfl-chip">R{int(pick["round"])}</span>
</div>
"""
                )

            cards.append(
                f"""
<section class="team-roster-status" style="--team-color:{esc(color)};">
  <div class="team-roster-status-title">
    <span>Draft Picks</span>
    <span>{len(owned_picks)}</span>
  </div>
  {''.join(pick_rows) if pick_rows else '<div class="team-roster-empty">No future picks</div>'}
</section>
"""
            )

    card_count = max(len(cards), 1)
    st.html(
        f'<div class="team-roster-board" style="--roster-card-count:{card_count};">'
        f'{"".join(cards)}</div>'
    )


def render_team_draft_capital(
    draft_picks: pd.DataFrame,
    rosters: pd.DataFrame,
    team_name: str,
) -> None:
    if draft_picks.empty or rosters.empty:
        return

    team = rosters.loc[rosters["team_name"].eq(team_name)].copy()
    if team.empty:
        return

    league_name = first_value(team, "league_name")
    roster_id = pd.to_numeric(team["roster_id"], errors="coerce").dropna()
    if roster_id.empty:
        return
    roster_id = int(roster_id.iloc[0])

    picks = draft_picks.loc[
        draft_picks["league_name"].eq(league_name)
        & draft_picks["owner_roster_id"].eq(roster_id)
    ].sort_values(["season", "round", "original_roster_id"])
    if picks.empty:
        return

    league_rosters = rosters.loc[rosters["league_name"].eq(league_name)].copy()
    league_rosters["roster_id"] = pd.to_numeric(league_rosters["roster_id"], errors="coerce")
    league_rosters = league_rosters.dropna(subset=["roster_id"])
    league_rosters["roster_id"] = league_rosters["roster_id"].astype(int)
    team_map = (
        league_rosters.drop_duplicates("roster_id")
        .set_index("roster_id")
        .to_dict("index")
    )
    cards = []
    for _, pick in picks.iterrows():
        original = team_map.get(int(pick["original_roster_id"]), {})
        origin_name = clean_text(original.get("team_name"), f"Roster {int(pick['original_roster_id'])}")
        origin_logo = clean_text(original.get("team_logo"))
        origin_color = clean_text(original.get("team_color"), "#1a2030")
        cards.append(
            f"""
<div class="draft-pick-card" style="--team-color:{esc(origin_color)};">
  <div class="draft-pick-top">
    <div class="draft-pick-year">{int(pick["season"])}</div>
    <div class="draft-pick-round">Round {int(pick["round"])}</div>
  </div>
  <div class="draft-pick-origin">
    {f'<img src="{esc(origin_logo)}" alt="{esc(origin_name)}">' if origin_logo else ''}
    <div class="draft-pick-origin-name">{esc(origin_name)} Pick</div>
  </div>
</div>
"""
        )

    st.html(
        f"""
<section class="draft-capital">
  <div class="position-label"><span>Future Draft Capital · {len(picks)} Picks</span><div></div></div>
  <div class="draft-capital-grid">{''.join(cards)}</div>
</section>
"""
    )


st.set_page_config(
    page_title=LEAGUE_NAME,
    page_icon=LEAGUE_LOGO,
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_data_controls()
inject_css()
selected_season = masthead()

with st.spinner("Loading league datasets...", show_time=True):
    branding_data = load_branding_data(DATA_CACHE_VERSION)
if len(branding_data) == 9:
    schools, conferences, schedule, scores, rankings, drafts, starters, bowls, player_pictures = branding_data
elif len(branding_data) == 8:
    schools, conferences, schedule, scores, rankings, drafts, starters, bowls = branding_data
    player_pictures = pd.DataFrame(columns=["Player", "Picture"])
elif len(branding_data) == 7:
    schools, conferences, schedule, scores, rankings, drafts, starters = branding_data
    bowls = pd.DataFrame(columns=["Bowl", "Logo"])
    player_pictures = pd.DataFrame(columns=["Player", "Picture"])
else:
    raise ValueError(
        f"Expected 7, 8, or 9 branding datasets, received {len(branding_data)}. "
        "Confirm the published app.py and data.py are from the same version."
    )
PLAYER_PICTURE_LOOKUP = {
    player_picture_key(row["Player"]): clean_text(row["Picture"])
    for _, row in player_pictures.iterrows()
    if player_picture_key(row.get("Player")) and clean_text(row.get("Picture"))
}
with st.spinner(f"Preparing the {selected_season} season...", show_time=True):
    full_schedule = schedule.copy()
    full_rankings = rankings.copy()
    full_starters = starters.copy()
    full_drafts = drafts.copy()
    full_scores = aggregate_scores_from_starters(starters, scores)
    schools = apply_season_owners(schools, selected_season)
    schedule = filter_by_season(schedule, selected_season)
    scores = filter_by_season(scores, selected_season)
    rankings = filter_by_season(rankings, selected_season)
    drafts = filter_by_season(drafts, selected_season)
    starters = filter_by_season(starters, selected_season)
    scores = aggregate_scores_from_starters(starters, scores)
    all_rosters = load_all_rosters(schools)
    future_draft_picks = load_future_draft_picks()
    is_current_roster_season = selected_season == current_roster_season()
    roster_snapshot = (
        all_rosters
        if is_current_roster_season
        else historical_roster_snapshot(starters, schools, selected_season)
    )
    history_ledger = build_history_ledger(full_schedule, full_scores, schools, full_rankings)

league_tab, conference_tab, team_tab, players_tab, rules_tab = st.tabs(
    ["🏆 League", "🏟️ Conference", "🎓 Team", "🏈 Players", "📘 Rules"]
)

with league_tab:
    (
        league_standings_tab,
        league_schedule_tab,
        league_rankings_tab,
        league_rosters_tab,
        league_drafts_tab,
        league_history_tab,
    ) = st.tabs(
        [
            "📊 Standings",
            "📅 Schedule",
            "⭐ Rankings",
            "👥 Rosters",
            "🧾 Drafts",
        ] + ["🕰️ History"]
    )
    with league_standings_tab:
        render_league_standings(schedule, scores, schools, conferences, rankings)
    with league_schedule_tab:
        weeks = schedule_weeks(schedule)
        if weeks:
            selected_week = st.selectbox(
                "Week",
                weeks,
                index=next_unplayed_schedule_week_index(weeks, schedule, scores),
                key="league_schedule_week_v2",
                format_func=week_label,
            )
            week_games = schedule.loc[schedule["Week"].eq(selected_week)].copy()
            render_schedule_cards(
                week_games,
                scores,
                schools,
                rankings=rankings,
                rosters=all_rosters,
                starters=starters,
                bowls=bowls,
                schedule_context=schedule,
                empty_label=f"No Week {selected_week} games",
                key_prefix="league_schedule",
            )
        else:
            render_schedule_cards(
                schedule,
                scores,
                schools,
                rankings=rankings,
                rosters=all_rosters,
                starters=starters,
                bowls=bowls,
                schedule_context=schedule,
                empty_label="No schedule loaded",
                key_prefix="league_schedule_empty",
            )
    with league_rankings_tab:
        render_rankings(
            rankings,
            schedule,
            scores,
            schools,
            conferences,
            all_rosters,
            future_draft_picks,
        )
    with league_rosters_tab:
        # player_download = unique_player_download(all_rosters)
        # st.download_button(
        #     "Download unique player CSV",
        #     data=player_download.to_csv(index=False).encode("utf-8"),
        #     file_name=f"ncaa_nfl_crossover_unique_players_{selected_season}.csv",
        #     mime="text/csv",
        #     use_container_width=True,
        # )
        render_league_roster_matrix(
            roster_snapshot,
            conferences,
            preview_missing_conferences=is_current_roster_season,
        )
    with league_drafts_tab:
        render_league_draft_board(
            drafts,
            schools,
            conferences,
            selected_season,
        )
    with league_history_tab:
        render_league_history(history_ledger, schools, bowls)

with conference_tab:
    conference_options = [name for name in LEAGUES.keys() if name in set(conferences["Conference"].astype(str))]
    if not conference_options:
        conference_options = list(LEAGUES.keys())

    selected_conference = st.selectbox("Conference", conference_options)
    conference_rosters = roster_snapshot.loc[
        roster_snapshot["league_name"].eq(selected_conference)
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
        conf_history_tab,
    ) = st.tabs(["📊 Standings", "📅 Schedule", "👥 Rosters", "🧾 Drafts", "🕰️ History"])
    with conf_history_tab:
        render_conference_history(history_ledger, schools, conferences, bowls, selected_conference)
    with conf_standings_tab:
        render_conference_standings(
            schedule,
            scores,
            schools,
            conferences,
            rankings,
            selected_conference,
        )
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
                index=next_unplayed_schedule_week_index(weeks, conference_schedule, scores),
                key=f"conference_schedule_week_v2_{selected_conference}",
                format_func=week_label,
            )
            week_games = conference_schedule.loc[
                conference_schedule["Week"].eq(selected_week)
            ].copy()
            render_schedule_cards(
                week_games,
                scores,
                schools,
                rankings=rankings,
                rosters=all_rosters,
                starters=starters,
                bowls=bowls,
                schedule_context=schedule,
                empty_label=f"No Week {selected_week} {selected_conference} games",
                key_prefix=f"conference_schedule_{match_key(selected_conference)}",
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
                rankings=rankings,
                rosters=all_rosters,
                starters=starters,
                bowls=bowls,
                schedule_context=schedule,
                empty_label=f"No {selected_conference} games",
                key_prefix=f"conference_schedule_empty_{match_key(selected_conference)}",
            )
            render_conference_schedule_matrix(
                conference_schedule,
                scores,
                schools,
                selected_conference,
            )
    with conf_rosters_tab:
        render_roster_matrix(conference_rosters)
        if is_current_roster_season:
            render_conference_draft_pick_matrix(
                conference_rosters,
                future_draft_picks,
            )
    with conf_drafts_tab:
        render_draft_board(
            drafts,
            schools,
            conferences,
            selected_season,
            selected_conference,
        )

with team_tab:
    team_options = (
        roster_snapshot["team_name"]
        .dropna()
        .astype(str)
        .sort_values()
        .drop_duplicates()
        .tolist()
    )
    if not team_options:
        st.warning(f"No Week 18 roster snapshot is available for {selected_season}.")
        st.stop()
    selected_team = st.selectbox("Team", team_options)
    selected_team_record = team_record_text(schedule, scores, schools, selected_team, rankings)
    render_team_hero(roster_snapshot, selected_team, selected_team_record)
    team_schedule_tab, team_roster_tab, team_history_tab = st.tabs(
        ["📅 Schedule", "👥 Rosters", "🕰️ History"]
    )
    with team_schedule_tab:
        team_schedule = schedule.loc[
            schedule["TeamA"].eq(selected_team)
            | schedule["TeamB"].eq(selected_team)
        ].copy()
        render_schedule_cards(
            team_schedule,
            scores,
            schools,
            rankings=rankings,
            rosters=all_rosters,
            starters=starters,
            bowls=bowls,
            schedule_context=schedule,
            empty_label=f"No {selected_team} games",
            stacked=True,
            sort_by_rank=False,
            key_prefix=f"team_schedule_{match_key(selected_team)}",
        )
    with team_roster_tab:
        render_team_roster(
            roster_snapshot,
            selected_team,
            future_draft_picks if is_current_roster_season else None,
        )
    with team_history_tab:
        render_team_history(history_ledger, full_schedule, schools, full_starters, selected_team)

with players_tab:
    player_options = all_time_player_options(all_rosters, full_starters, full_drafts)
    if not player_options:
        st.warning("No player history is currently available.")
    else:
        selected_player = st.selectbox(
            "Player",
            player_options,
            key="all_time_player_selector",
        )
        render_player_dashboard(
            selected_player,
            all_rosters,
            full_starters,
            full_drafts,
            conferences,
            schools,
        )

with rules_tab:
    render_rules()
