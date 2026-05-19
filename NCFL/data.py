
from __future__ import annotations
from typing import Any
import pandas as pd
import requests
import streamlit as st

SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"

def _get_json(endpoint: str) -> Any:
    response = requests.get(f"{SLEEPER_API_BASE_URL}{endpoint}", timeout=30)
    response.raise_for_status()
    return response.json()

def get_players() -> pd.DataFrame:
    players = _get_json("/players/nfl")
    rows = []
    for player_id, player in players.items():
        rows.append(
            {   "player_id": player_id,
                "player_name": player.get("full_name"),
                "position": player.get("position"),
                "team": player.get("team"),
                "injury_status": player.get("injury_status")})
    return pd.DataFrame(rows)

def get_rosters(league_id: int | str) -> list[dict[str, Any]]:
    """Return the raw Sleeper rosters for a league."""
    return _get_json(f"/league/{league_id}/rosters")

def get_roster(league_id: int | str, players: pd.DataFrame | None = None, league_name: str | None = None) -> pd.DataFrame:
    rosters = get_rosters(league_id)
    if players is None:
        players = get_players()
    rows = []
    for roster in rosters:
        metadata = roster.get("metadata") or {}
        team_name = metadata.get("team_name") or f"Roster {roster.get('roster_id')}"
        starters = set(roster.get("starters") or [])
        reserve = set(roster.get("reserve") or [])
        taxi = set(roster.get("taxi") or [])
        for player_id in roster.get("players") or []:
            if player_id in starters:
                roster_spot = "starter"
            elif player_id in reserve:
                roster_spot = "reserve"
            elif player_id in taxi:
                roster_spot = "taxi"
            else:
                roster_spot = "bench"
            rows.append({
                    "league_id": roster.get("league_id"),
                    "league_name": league_name,
                    "roster_id": roster.get("roster_id"),
                    "owner_id": roster.get("owner_id"),
                    "team_name": team_name,
                    "player_id": player_id,
                    "roster_spot": roster_spot})
    roster_df = pd.DataFrame(rows)
    if roster_df.empty:
        return roster_df
    return (roster_df.merge(players, on="player_id", how="left")
        .sort_values(["team_name", "roster_spot", "position", "player_name"])
        .reset_index(drop=True))

LEAGUES = {
    "Big 12": "1346983655301455872",
    "B1G": "1346983746389151744",
    "SEC": "1346983807705702400",
    "Pac-12": "1346983783475200000",
    "ACC": "1346983719008768000",
    "G6": "1346983691322130432",
    "MW": "1349455273399431168",
    "MAC": "1349455814967971840",
    "C-USA": "1349455990495379456",
    "SBC": "1349456254895951872",
    "AAC": "1349456864814850048",
    "FCS": "1349457011871354880",
}

POSITIONS = ["QB", "RB", "WR", "TE"]

@st.cache_data(ttl=60 * 60 * 24, show_spinner="Loading Sleeper rosters...")
def load_all_rosters() -> pd.DataFrame:
    players = get_players()
    league_rosters = []
    for league_name, league_id in LEAGUES.items():
        league_rosters.append(
            get_roster(
                league_id=league_id,
                players=players,
                league_name=league_name,))
    return pd.concat(league_rosters, ignore_index=True)

def position_table(rosters: pd.DataFrame, position: str) -> pd.DataFrame:
    filtered = rosters.loc[rosters["position"].eq(position)].copy()
    if filtered.empty:
        return pd.DataFrame()

    filtered["player_label"] = filtered["player_name"].fillna(filtered["player_id"])
    team_players = {}

    for team_name, team_roster in filtered.groupby("team_name"):
        team_players[team_name] = sorted(team_roster["player_label"].dropna())

    return pd.DataFrame.from_dict(team_players, orient="index").transpose().fillna("")
