from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

import numpy as np
import pandas as pd


def clock_seconds(value: str | None) -> int:
    if not value or ":" not in value:
        return 0
    minutes, seconds = value.split(":", 1)
    return int(minutes) * 60 + int(seconds)


def absolute_seconds(period: int, time_in_period: str) -> int:
    # Regulation periods are 20 minutes. OT event clocks simply continue from 60:00.
    return (period - 1) * 1200 + clock_seconds(time_in_period)


def parse_situation(code: str | int | None) -> dict[str, Any]:
    value = str(code or "").zfill(4)
    if len(value) != 4 or not value.isdigit():
        return {
            "away_goalie": np.nan,
            "away_skaters": np.nan,
            "home_skaters": np.nan,
            "home_goalie": np.nan,
        }
    return {
        "away_goalie": int(value[0]),
        "away_skaters": int(value[1]),
        "home_skaters": int(value[2]),
        "home_goalie": int(value[3]),
    }


def state_label(for_skaters: Any, against_skaters: Any) -> str:
    try:
        return f"{int(for_skaters)}v{int(against_skaters)}"
    except (TypeError, ValueError):
        return "Unknown"


def flatten_schedule(payload: dict[str, Any]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for game in payload.get("games", []):
        away = game.get("awayTeam", {})
        home = game.get("homeTeam", {})
        games.append(
            {
                "game_id": int(game["id"]),
                "season": int(game.get("season", 0)),
                "game_type": int(game.get("gameType", 0)),
                "game_date": game.get("gameDate"),
                "start_time_utc": game.get("startTimeUTC"),
                "game_state": game.get("gameState"),
                "away_id": away.get("id"),
                "away_team": away.get("abbrev"),
                "away_score": away.get("score"),
                "home_id": home.get("id"),
                "home_team": home.get("abbrev"),
                "home_score": home.get("score"),
                "venue": (game.get("venue") or {}).get("default"),
            }
        )
    return games


def roster_lookup(pbp: dict[str, Any]) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for player in pbp.get("rosterSpots", []):
        player_id = player.get("playerId")
        if player_id is not None:
            result[int(player_id)] = {
                "team_id": player.get("teamId"),
                "position": player.get("positionCode"),
                "first_name": (player.get("firstName") or {}).get("default"),
                "last_name": (player.get("lastName") or {}).get("default"),
            }
    return result


def flatten_plays(pbp: dict[str, Any], game: dict[str, Any]) -> pd.DataFrame:
    roster = roster_lookup(pbp)
    home_team = game["home_team"]
    away_team = game["away_team"]
    home_id = game["home_id"]
    away_id = game["away_id"]
    home_score = 0
    away_score = 0
    rows: list[dict[str, Any]] = []

    for play in pbp.get("plays", []):
        details = play.get("details") or {}
        period = int((play.get("periodDescriptor") or {}).get("number", 1))
        event_type = play.get("typeDescKey")
        situation = parse_situation(play.get("situationCode"))
        event_team_id = details.get("eventOwnerTeamId")
        event_team = (
            home_team if event_team_id == home_id else away_team if event_team_id == away_id else None
        )
        scoring_team = event_team if event_type == "goal" else None

        actor_id = details.get("shootingPlayerId") or details.get("scoringPlayerId")
        actor = roster.get(int(actor_id), {}) if actor_id else {}
        row = {
            "game_id": game["game_id"],
            "season": game["season"],
            "game_type": game["game_type"],
            "game_date": game["game_date"],
            "event_id": play.get("eventId"),
            "sort_order": play.get("sortOrder"),
            "event_type": event_type,
            "period": period,
            "period_type": (play.get("periodDescriptor") or {}).get("periodType"),
            "time_in_period": play.get("timeInPeriod"),
            "elapsed_seconds": absolute_seconds(period, play.get("timeInPeriod", "00:00")),
            "situation_code": play.get("situationCode"),
            "home_team": home_team,
            "away_team": away_team,
            "event_team": event_team,
            "scoring_team": scoring_team,
            "home_score_before": home_score,
            "away_score_before": away_score,
            "home_diff_before": home_score - away_score,
            "x_coord": details.get("xCoord"),
            "y_coord": details.get("yCoord"),
            "shot_type": details.get("shotType"),
            "shooting_player_id": actor_id,
            "actor_name": " ".join(
                part for part in [actor.get("first_name"), actor.get("last_name")] if part
            ) or None,
            "goalie_id": details.get("goalieInNetId"),
            **situation,
        }

        if event_type == "goal":
            if details.get("homeScore") is not None:
                home_score = int(details["homeScore"])
                away_score = int(details["awayScore"])
            elif scoring_team == home_team:
                home_score += 1
            elif scoring_team == away_team:
                away_score += 1
        row["home_score_after"] = home_score
        row["away_score_after"] = away_score
        rows.append(row)

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["event_team_diff_before"] = np.where(
        frame["event_team"].eq(home_team),
        frame["home_diff_before"],
        -frame["home_diff_before"],
    )
    frame["exact_score_home"] = (
        frame["home_score_before"].astype(str) + "-" + frame["away_score_before"].astype(str)
    )
    frame["for_skaters"] = np.where(
        frame["event_team"].eq(home_team), frame["home_skaters"], frame["away_skaters"]
    )
    frame["against_skaters"] = np.where(
        frame["event_team"].eq(home_team), frame["away_skaters"], frame["home_skaters"]
    )
    frame["official_state"] = [
        state_label(a, b) for a, b in zip(frame["for_skaters"], frame["against_skaters"])
    ]
    return frame


def normalize_shifts(
    shift_payload: dict[str, Any], pbp: dict[str, Any], game: dict[str, Any]
) -> pd.DataFrame:
    roster = roster_lookup(pbp)
    team_by_id = {
        game["home_id"]: game["home_team"],
        game["away_id"]: game["away_team"],
    }
    valid_abbrevs = {game["home_team"], game["away_team"]}
    rows = []
    seen_shift_keys = set()
    for shift in shift_payload.get("data", []):
        period = int(shift.get("period", 0) or 0)
        if period < 1:
            continue
        player_id = int(shift.get("playerId", 0) or 0)
        player = roster.get(player_id, {})
        start = absolute_seconds(period, shift.get("startTime", "00:00"))
        end = absolute_seconds(period, shift.get("endTime", "00:00"))
        if end <= start:
            continue
        team_id = shift.get("teamId") or player.get("team_id")
        team = team_by_id.get(team_id) or shift.get("teamAbbrev")
        if team not in valid_abbrevs:
            continue
        shift_key = (
            player_id,
            team,
            period,
            shift.get("shiftNumber"),
            shift.get("startTime"),
            shift.get("endTime"),
        )
        if shift_key in seen_shift_keys:
            continue
        seen_shift_keys.add(shift_key)
        rows.append(
            {
                "game_id": game["game_id"],
                "player_id": player_id,
                "team": team,
                "team_id": team_id,
                "position": player.get("position"),
                "period": period,
                "start_second": start,
                "end_second": end,
                "duration": end - start,
            }
        )
    return pd.DataFrame(rows)


def build_second_states(
    shifts: pd.DataFrame, plays: pd.DataFrame, game: dict[str, Any]
) -> pd.DataFrame:
    if not shifts.empty:
        duration = int(shifts["end_second"].max())
    elif not plays.empty:
        duration = max(3600, int(plays["elapsed_seconds"].max()) + 1)
    else:
        return pd.DataFrame()
    duration = min(max(duration, 3600), 6000)
    seconds = pd.DataFrame({"second": np.arange(duration, dtype=int)})

    for side in ("home", "away"):
        team = game[f"{side}_team"]
        skater_delta = np.zeros(duration + 1, dtype=np.int16)
        goalie_delta = np.zeros(duration + 1, dtype=np.int16)
        team_shifts = shifts[shifts["team"].eq(team)] if not shifts.empty else shifts
        for row in team_shifts.itertuples(index=False):
            start = max(0, min(duration, int(row.start_second)))
            end = max(0, min(duration, int(row.end_second)))
            target = goalie_delta if row.position == "G" else skater_delta
            target[start] += 1
            target[end] -= 1
        seconds[f"{side}_skaters"] = np.cumsum(skater_delta[:-1])
        seconds[f"{side}_goalies"] = np.cumsum(goalie_delta[:-1])

    seconds["home_score"] = 0
    seconds["away_score"] = 0
    goals = plays[plays["event_type"].eq("goal")].sort_values("elapsed_seconds")
    for goal in goals.itertuples(index=False):
        at = min(duration, max(0, int(goal.elapsed_seconds)))
        seconds.loc[seconds["second"] >= at, "home_score"] = goal.home_score_after
        seconds.loc[seconds["second"] >= at, "away_score"] = goal.away_score_after
    seconds["home_diff"] = seconds["home_score"] - seconds["away_score"]
    seconds["game_id"] = game["game_id"]
    seconds["season"] = game["season"]
    seconds["game_type"] = game["game_type"]
    seconds["game_date"] = game["game_date"]
    seconds["home_team"] = game["home_team"]
    seconds["away_team"] = game["away_team"]
    return seconds


def _diff_bucket(value: int) -> str:
    if value <= -3:
        return "Down 3+"
    if value < 0:
        return f"Down {abs(value)}"
    if value == 0:
        return "Tied"
    if value >= 3:
        return "Up 3+"
    return f"Up {value}"


def aggregate_exposure(seconds: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if seconds.empty:
        return pd.DataFrame(), pd.DataFrame()
    frames = []
    for side, other in (("home", "away"), ("away", "home")):
        view = pd.DataFrame(
            {
                "game_id": seconds["game_id"],
                "season": seconds["season"],
                "game_type": seconds["game_type"],
                "game_date": seconds["game_date"],
                "team": seconds[f"{side}_team"],
                "opponent": seconds[f"{other}_team"],
                "second": seconds["second"],
                "for_skaters": seconds[f"{side}_skaters"],
                "against_skaters": seconds[f"{other}_skaters"],
                "for_goalie": seconds[f"{side}_goalies"].gt(0),
                "against_goalie": seconds[f"{other}_goalies"].gt(0),
                "score_for": seconds[f"{side}_score"],
                "score_against": seconds[f"{other}_score"],
            }
        )
        view["score_diff"] = view["score_for"] - view["score_against"]
        view["period"] = (view["second"] // 1200) + 1
        view["game_minute"] = view["second"] // 60
        view["score_bucket"] = view["score_diff"].map(_diff_bucket)
        view["exact_score"] = view["score_for"].astype(str) + "-" + view["score_against"].astype(str)
        view["state"] = [
            state_label(a, b) for a, b in zip(view["for_skaters"], view["against_skaters"])
        ]
        frames.append(view)
    all_seconds = pd.concat(frames, ignore_index=True)
    valid = all_seconds[all_seconds["for_skaters"].between(3, 6) & all_seconds["against_skaters"].between(3, 6)]
    manpower = (
        valid.groupby(
            [
                "game_id", "season", "game_type", "game_date", "team", "opponent",
                "period", "game_minute", "score_diff", "score_bucket", "state", "for_skaters", "against_skaters", "for_goalie", "against_goalie",
            ],
            observed=True,
        )
        .size()
        .rename("seconds")
        .reset_index()
    )
    score = (
        valid.groupby(
            ["game_id", "season", "game_type", "game_date", "team", "opponent", "period", "game_minute", "score_diff", "score_bucket", "exact_score"],
            observed=True,
        )
        .size()
        .rename("seconds")
        .reset_index()
    )
    return manpower, score


def add_state_transitions(plays: pd.DataFrame, seconds: pd.DataFrame) -> pd.DataFrame:
    if plays.empty:
        return plays
    frame = plays.copy().sort_values(["elapsed_seconds", "sort_order"])
    home = frame["home_team"].iloc[0]
    away = frame["away_team"].iloc[0]
    frame["prior_state"] = None
    frame["seconds_since_state_change"] = np.nan
    if seconds.empty:
        return frame
    state_by_team: dict[str, list[str]] = {}
    for team, side, other in ((home, "home", "away"), (away, "away", "home")):
        state_by_team[team] = [
            state_label(a, b)
            for a, b in zip(seconds[f"{side}_skaters"], seconds[f"{other}_skaters"])
        ]
    for idx, event in frame.iterrows():
        team = event["event_team"]
        if team not in state_by_team:
            continue
        at = min(len(seconds) - 1, max(0, int(event["elapsed_seconds"])))
        states = state_by_team[team]
        current = states[at]
        changed_at = at
        while changed_at > 0 and states[changed_at - 1] == current:
            changed_at -= 1
        prior = states[changed_at - 1] if changed_at > 0 else current
        frame.at[idx, "prior_state"] = prior
        frame.at[idx, "seconds_since_state_change"] = at - changed_at
    return frame


def score_transitions(plays: pd.DataFrame, game: dict[str, Any]) -> pd.DataFrame:
    goals = plays[plays["event_type"].eq("goal")].sort_values(["elapsed_seconds", "sort_order"])
    rows = []
    for team, is_home in ((game["home_team"], True), (game["away_team"], False)):
        for goal in goals.itertuples(index=False):
            before_for = goal.home_score_before if is_home else goal.away_score_before
            before_against = goal.away_score_before if is_home else goal.home_score_before
            after_for = goal.home_score_after if is_home else goal.away_score_after
            after_against = goal.away_score_after if is_home else goal.home_score_after
            rows.append(
                {
                    "game_id": game["game_id"],
                    "season": game["season"],
                    "game_type": game["game_type"],
                    "game_date": game["game_date"],
                    "team": team,
                    "period": goal.period,
                    "elapsed_seconds": goal.elapsed_seconds,
                    "source": f"{before_for}-{before_against}",
                    "target": f"{after_for}-{after_against}",
                    "goal_for": goal.scoring_team == team,
                }
            )
    return pd.DataFrame(rows)


def concat_frames(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    nonempty = [frame for frame in frames if frame is not None and not frame.empty]
    return pd.concat(nonempty, ignore_index=True) if nonempty else pd.DataFrame()
