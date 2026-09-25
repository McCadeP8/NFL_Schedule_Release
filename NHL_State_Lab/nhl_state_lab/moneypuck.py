from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from .api import NHLClient
from .config import MONEYPUCK_SHOTS_URL
from .transform import state_label


def load_moneypuck(
    client: NHLClient, season: int, raw_dir: Path, refresh: bool = False
) -> pd.DataFrame:
    start_year = str(season)[:4]
    zip_path = raw_dir / "moneypuck" / f"shots_{start_year}.zip"
    url = MONEYPUCK_SHOTS_URL.format(start_year=start_year)
    client.download(url, zip_path, refresh=refresh)
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            return pd.DataFrame()
        with archive.open(csv_names[0]) as handle:
            shots = pd.read_csv(handle, low_memory=False)

    rename_candidates = {
        "game_id": "game_id",
        "gameId": "game_id",
        "xGoal": "xg",
        "xGoals": "xg",
        "teamCode": "event_team",
        "team": "event_team",
        "homeTeamCode": "home_team",
        "awayTeamCode": "away_team",
        "homeTeamGoals": "home_score_before",
        "awayTeamGoals": "away_score_before",
        "time": "elapsed_seconds",
        "period": "period",
        "goal": "is_goal",
    }
    for source, target in rename_candidates.items():
        if source in shots.columns and target not in shots.columns:
            shots = shots.rename(columns={source: target})
    shots["season"] = season
    if "game_id" in shots:
        # MoneyPuck stores the within-season portion (e.g. 20001); NHL uses 2025020001.
        game_ids = pd.to_numeric(shots["game_id"], errors="coerce")
        shots["game_id"] = game_ids.where(
            game_ids.ge(10_000_000), int(str(season)[:4]) * 1_000_000 + game_ids
        ).astype("Int64")
    if "id" in shots and "event_id" not in shots:
        shots["event_id"] = shots["id"]
    shots["game_type"] = shots.get("isPlayoffGame", 0).map({0: 2, 1: 3}).fillna(2).astype(int)
    if "home_score_before" in shots and "away_score_before" in shots:
        shots["home_diff_before"] = shots["home_score_before"] - shots["away_score_before"]
        shots["event_team_diff_before"] = shots["home_diff_before"].where(
            shots["event_team"].eq(shots["home_team"]), -shots["home_diff_before"]
        )
        shots["exact_score_for"] = shots["home_score_before"].where(
            shots["event_team"].eq(shots["home_team"]), shots["away_score_before"]
        ).astype("Int64").astype(str) + "-" + shots["away_score_before"].where(
            shots["event_team"].eq(shots["home_team"]), shots["home_score_before"]
        ).astype("Int64").astype(str)
    if {"homeSkatersOnIce", "awaySkatersOnIce"}.issubset(shots.columns):
        shooting_home = shots["event_team"].eq(shots["home_team"])
        shots["for_skaters"] = shots["homeSkatersOnIce"].where(
            shooting_home, shots["awaySkatersOnIce"]
        )
        shots["against_skaters"] = shots["awaySkatersOnIce"].where(
            shooting_home, shots["homeSkatersOnIce"]
        )
        shots["state"] = [
            state_label(a, b)
            for a, b in zip(shots["for_skaters"], shots["against_skaters"])
        ]
        shots["for_goalie"] = ~shots["homeEmptyNet"].where(
            shooting_home, shots["awayEmptyNet"]
        ).fillna(0).astype(bool)
        shots["against_goalie"] = ~shots["awayEmptyNet"].where(
            shooting_home, shots["homeEmptyNet"]
        ).fillna(0).astype(bool)
    return shots
