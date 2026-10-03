from __future__ import annotations

import numpy as np
import pandas as pd

from .team_meta import TEAM_NAMES


CATEGORIES = ["Even", "Advantage", "Disadvantage"]


def invert_state(value: object) -> str:
    parts = str(value).split("v")
    return f"{parts[1]}v{parts[0]}" if len(parts) == 2 else "Unknown"


def state_category(value: object) -> str:
    parts = str(value).split("v")
    if len(parts) != 2:
        return "Other"
    try:
        for_skaters, against_skaters = int(parts[0]), int(parts[1])
    except ValueError:
        return "Other"
    if for_skaters > against_skaters:
        return "Advantage"
    if for_skaters < against_skaters:
        return "Disadvantage"
    return "Even"


def _empty_overview() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "season", "game_type", "through_game_date", "carryover_seconds", "team", "team_name",
        "games_played", "wins", "losses", "overtime_losses", "points", "points_pct",
        "raw_goals", "raw_goals_allowed", "raw_goal_difference",
        "Even_gf60", "Even_ga60", "Even_gd60",
        "Advantage_gf60", "Advantage_ga60", "Advantage_gd60",
        "Disadvantage_gf60", "Disadvantage_ga60", "Disadvantage_gd60",
        "total_seconds", "weighted_gf", "weighted_ga", "weighted_gd",
    ])


def build_league_overview_metrics(
    games: pd.DataFrame,
    plays: pd.DataFrame,
    manpower: pd.DataFrame,
    *,
    carryover_seconds: int = 5,
) -> pd.DataFrame:
    if games.empty or plays.empty or manpower.empty:
        return _empty_overview()

    games = games.copy()
    plays = plays.copy()
    manpower = manpower.copy()
    games["game_date"] = pd.to_datetime(games["game_date"])
    completed_games = games[games["game_state"].isin(["OFF", "FINAL"])].copy()
    if completed_games.empty:
        return _empty_overview()

    completed_ids = set(completed_games["game_id"])
    plays = plays[plays["game_id"].isin(completed_ids)].copy()
    manpower = manpower[manpower["game_id"].isin(completed_ids)].copy()
    if plays.empty or manpower.empty:
        return _empty_overview()

    max_period_by_game = plays.groupby("game_id", as_index=False)["period"].max().rename(columns={"period": "max_period"})
    overview_rows = []

    for game_type_value, type_games in completed_games.groupby("game_type"):
        type_ids = set(type_games["game_id"])
        type_plays = plays[plays["game_id"].isin(type_ids)].copy()
        type_manpower = manpower[manpower["game_id"].isin(type_ids)].copy()
        if type_plays.empty or type_manpower.empty:
            continue

        teams = sorted(
            set(type_games["home_team"].dropna()) | set(type_games["away_team"].dropna()),
            key=lambda abbreviation: TEAM_NAMES.get(abbreviation, abbreviation),
        )
        teams_frame = pd.DataFrame({"team": teams})

        home_results = type_games[[
            "game_id", "season", "game_type", "home_team", "away_team", "home_score", "away_score"
        ]].rename(columns={"home_team": "team", "away_team": "opponent", "home_score": "score_for", "away_score": "score_against"})
        away_results = type_games[[
            "game_id", "season", "game_type", "away_team", "home_team", "away_score", "home_score"
        ]].rename(columns={"away_team": "team", "home_team": "opponent", "away_score": "score_for", "home_score": "score_against"})
        result_rows = pd.concat([home_results, away_results], ignore_index=True).merge(max_period_by_game, on="game_id", how="left")
        result_rows["win"] = result_rows["score_for"].gt(result_rows["score_against"]).astype(int)
        result_rows["otl"] = (
            result_rows["score_for"].lt(result_rows["score_against"])
            & result_rows["game_type"].eq(2)
            & result_rows["max_period"].fillna(3).gt(3)
        ).astype(int)
        result_rows["loss"] = result_rows["score_for"].lt(result_rows["score_against"]).astype(int) - result_rows["otl"]
        standings = result_rows.groupby("team", as_index=False).agg(
            games_played=("game_id", "nunique"),
            wins=("win", "sum"),
            losses=("loss", "sum"),
            overtime_losses=("otl", "sum"),
        )
        standings["points"] = 2 * standings["wins"] + standings["overtime_losses"]
        standings["points_pct"] = standings["points"] / (2 * standings["games_played"])

        type_manpower["category"] = type_manpower["state"].map(state_category)
        type_manpower["stage_key"] = (
            type_manpower["state"].astype(str)
            + "|FG" + type_manpower["for_goalie"].astype(int).astype(str)
            + "|AG" + type_manpower["against_goalie"].astype(int).astype(str)
        )
        exposure_category = type_manpower.groupby(["team", "category"], as_index=False)["seconds"].sum()
        exposure_stage = type_manpower.groupby(["team", "stage_key"], as_index=False)["seconds"].sum()
        team_total_seconds = type_manpower.groupby("team", as_index=False)["seconds"].sum().rename(columns={"seconds": "total_seconds"})

        goals = type_plays[type_plays["event_type"].eq("goal")].copy()
        if "period_type" in goals:
            goals = goals[~goals["period_type"].eq("SO")].copy()
        if goals.empty:
            goal_view = pd.DataFrame(columns=["team", "category", "stage_key", "raw_goals", "raw_goals_allowed"])
        else:
            scoring_home = goals["scoring_team"].eq(goals["home_team"])
            scoring_team = goals["scoring_team"]
            allowed_team = np.where(scoring_home, goals["away_team"], goals["home_team"])
            scoring_goalie = np.where(scoring_home, goals["home_goalie"], goals["away_goalie"]).astype(bool)
            allowed_goalie = np.where(scoring_home, goals["away_goalie"], goals["home_goalie"]).astype(bool)
            goals["credited_state"] = goals["official_state"]
            carry_mask = (
                goals["seconds_since_state_change"].le(carryover_seconds)
                & goals["prior_state"].notna()
                & goals["prior_state"].ne(goals["official_state"])
            )
            goals.loc[carry_mask, "credited_state"] = goals.loc[carry_mask, "prior_state"]
            goals_for_view = pd.DataFrame({
                "team": scoring_team,
                "state": goals["credited_state"],
                "team_goalie": scoring_goalie,
                "opponent_goalie": allowed_goalie,
                "raw_goals": 1.0,
                "raw_goals_allowed": 0.0,
            })
            goals_allowed_view = pd.DataFrame({
                "team": allowed_team,
                "state": goals["credited_state"].map(invert_state),
                "team_goalie": allowed_goalie,
                "opponent_goalie": scoring_goalie,
                "raw_goals": 0.0,
                "raw_goals_allowed": 1.0,
            })
            goal_view = pd.concat([goals_for_view, goals_allowed_view], ignore_index=True)
            goal_view["category"] = goal_view["state"].map(state_category)
            goal_view["stage_key"] = (
                goal_view["state"].astype(str)
                + "|FG" + goal_view["team_goalie"].astype(int).astype(str)
                + "|AG" + goal_view["opponent_goalie"].astype(int).astype(str)
            )

        goals_category = goal_view.groupby(["team", "category"], as_index=False)[["raw_goals", "raw_goals_allowed"]].sum()
        goals_stage = goal_view.groupby(["team", "stage_key"], as_index=False)[["raw_goals", "raw_goals_allowed"]].sum()
        raw_goals = goal_view.groupby("team", as_index=False)[["raw_goals", "raw_goals_allowed"]].sum()

        category_grid = teams_frame.merge(pd.DataFrame({"category": CATEGORIES}), how="cross")
        category_table = (
            category_grid
            .merge(exposure_category, on=["team", "category"], how="left")
            .merge(goals_category, on=["team", "category"], how="left")
            .fillna({"seconds": 0, "raw_goals": 0, "raw_goals_allowed": 0})
        )
        category_table["gf60"] = np.where(category_table["seconds"].gt(0), category_table["raw_goals"] * 3600 / category_table["seconds"], np.nan)
        category_table["ga60"] = np.where(category_table["seconds"].gt(0), category_table["raw_goals_allowed"] * 3600 / category_table["seconds"], np.nan)
        category_table["gd60"] = category_table["gf60"] - category_table["ga60"]
        category_wide = category_table.pivot(index="team", columns="category", values=["gf60", "ga60", "gd60"])
        category_wide.columns = [f"{category}_{metric}" for metric, category in category_wide.columns]
        category_wide = category_wide.reset_index()

        stage_seconds = type_manpower.groupby("stage_key", as_index=False)["seconds"].sum()
        total_stage_seconds = stage_seconds["seconds"].sum()
        stage_seconds["league_share"] = stage_seconds["seconds"] / total_stage_seconds
        league_stage_goals = goal_view.groupby("stage_key", as_index=False)[["raw_goals", "raw_goals_allowed"]].sum()
        league_stage = stage_seconds.merge(league_stage_goals, on="stage_key", how="left").fillna({"raw_goals": 0, "raw_goals_allowed": 0})
        league_stage["league_gf_rate"] = np.where(league_stage["seconds"].gt(0), league_stage["raw_goals"] / league_stage["seconds"], 0)
        league_stage["league_ga_rate"] = np.where(league_stage["seconds"].gt(0), league_stage["raw_goals_allowed"] / league_stage["seconds"], 0)

        team_stage = exposure_stage.merge(goals_stage, on=["team", "stage_key"], how="left").fillna({"raw_goals": 0, "raw_goals_allowed": 0})
        team_stage["team_gf_rate"] = np.where(team_stage["seconds"].gt(0), team_stage["raw_goals"] / team_stage["seconds"], np.nan)
        team_stage["team_ga_rate"] = np.where(team_stage["seconds"].gt(0), team_stage["raw_goals_allowed"] / team_stage["seconds"], np.nan)
        weighted_grid = teams_frame.merge(league_stage[["stage_key", "league_share", "league_gf_rate", "league_ga_rate"]], how="cross")
        weighted_grid = weighted_grid.merge(
            team_stage[["team", "stage_key", "team_gf_rate", "team_ga_rate"]],
            on=["team", "stage_key"], how="left",
        )
        weighted_grid["gf_rate"] = weighted_grid["team_gf_rate"].fillna(weighted_grid["league_gf_rate"])
        weighted_grid["ga_rate"] = weighted_grid["team_ga_rate"].fillna(weighted_grid["league_ga_rate"])
        weighted_rates = weighted_grid.groupby("team", as_index=False).apply(
            lambda group: pd.Series({
                "weighted_gf_rate": (group["league_share"] * group["gf_rate"]).sum(),
                "weighted_ga_rate": (group["league_share"] * group["ga_rate"]).sum(),
            }),
            include_groups=False,
        ).reset_index(drop=True)
        weighted = teams_frame.merge(team_total_seconds, on="team", how="left").merge(weighted_rates, on="team", how="left")
        weighted[["total_seconds", "weighted_gf_rate", "weighted_ga_rate"]] = weighted[["total_seconds", "weighted_gf_rate", "weighted_ga_rate"]].fillna(0)
        weighted["weighted_gf"] = weighted["total_seconds"] * weighted["weighted_gf_rate"]
        weighted["weighted_ga"] = weighted["total_seconds"] * weighted["weighted_ga_rate"]
        weighted["weighted_gd"] = weighted["weighted_gf"] - weighted["weighted_ga"]

        table = (
            teams_frame
            .merge(standings, on="team", how="left")
            .merge(raw_goals, on="team", how="left")
            .merge(category_wide, on="team", how="left")
            .merge(weighted[["team", "total_seconds", "weighted_gf", "weighted_ga", "weighted_gd"]], on="team", how="left")
        )
        fill_zero = ["games_played", "wins", "losses", "overtime_losses", "points", "raw_goals", "raw_goals_allowed", "total_seconds", "weighted_gf", "weighted_ga", "weighted_gd"]
        table[fill_zero] = table[fill_zero].fillna(0)
        table["raw_goal_difference"] = table["raw_goals"] - table["raw_goals_allowed"]
        table["team_name"] = table["team"].map(lambda value: TEAM_NAMES.get(value, value))
        table["season"] = int(type_games["season"].iloc[0])
        table["game_type"] = int(game_type_value)
        table["through_game_date"] = type_games["game_date"].max().date().isoformat()
        table["carryover_seconds"] = carryover_seconds
        overview_rows.append(table)

    return pd.concat(overview_rows, ignore_index=True) if overview_rows else _empty_overview()
