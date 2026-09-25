from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .api import NHLClient
from .config import NHL_STATS, NHL_WEB, PROCESSED_DIR, RAW_DIR, TEAM_ABBREVS
from .moneypuck import load_moneypuck
from .transform import (
    add_state_transitions,
    aggregate_exposure,
    concat_frames,
    flatten_plays,
    flatten_schedule,
    normalize_shifts,
    score_transitions,
    build_second_states,
)


def save_parquet(frame: pd.DataFrame, path: Path) -> None:
    if frame.empty:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


def discover_games(client: NHLClient, season: int, refresh: bool) -> pd.DataFrame:
    rows = []
    for team in TEAM_ABBREVS:
        url = f"{NHL_WEB}/club-schedule-season/{team}/{season}"
        cache = RAW_DIR / str(season) / "schedules" / f"{team}.json"
        try:
            rows.extend(flatten_schedule(client.get_json(url, cache, refresh)))
        except RuntimeError as exc:
            print(f"Schedule warning for {team}: {exc}")
    games = pd.DataFrame(rows)
    if games.empty:
        raise RuntimeError(f"No games discovered for {season}")
    games = games.drop_duplicates("game_id").sort_values(["game_date", "game_id"])
    return games


def process_season(
    season: int,
    game_types: list[int],
    refresh: bool = False,
    skip_moneypuck: bool = False,
    limit: int | None = None,
) -> None:
    client = NHLClient()
    games = discover_games(client, season, refresh)
    games = games[games["game_type"].isin(game_types)].copy()
    completed = games[games["game_state"].isin(["OFF", "FINAL"])].copy()
    if limit:
        completed = completed.head(limit)
    save_parquet(games, PROCESSED_DIR / f"games_{season}.parquet")
    print(f"{season}: {len(games)} scheduled, {len(completed)} completed games to process")

    play_frames = []
    shift_frames = []
    manpower_frames = []
    score_frames = []
    transition_frames = []
    failures = []

    for number, game_row in enumerate(completed.to_dict("records"), start=1):
        game_id = game_row["game_id"]
        base = RAW_DIR / str(season) / "games"
        try:
            pbp = client.get_json(
                f"{NHL_WEB}/gamecenter/{game_id}/play-by-play",
                base / "pbp" / f"{game_id}.json",
                refresh,
            )
            client.get_json(
                f"{NHL_WEB}/gamecenter/{game_id}/boxscore",
                base / "boxscore" / f"{game_id}.json",
                refresh,
            )
            shifts_json = client.get_json(
                f"{NHL_STATS}/shiftcharts?cayenneExp=gameId={game_id}",
                base / "shifts" / f"{game_id}.json",
                refresh,
            )
            plays = flatten_plays(pbp, game_row)
            shifts = normalize_shifts(shifts_json, pbp, game_row)
            seconds = build_second_states(shifts, plays, game_row)
            plays = add_state_transitions(plays, seconds)
            manpower, score = aggregate_exposure(seconds)
            play_frames.append(plays)
            shift_frames.append(shifts)
            manpower_frames.append(manpower)
            score_frames.append(score)
            transition_frames.append(score_transitions(plays, game_row))
        except Exception as exc:  # retain a complete repair manifest
            failures.append({"game_id": game_id, "error": str(exc)})
            print(f"[{number}/{len(completed)}] FAILED {game_id}: {exc}")
            continue
        if number % 50 == 0 or number == len(completed):
            print(f"[{number}/{len(completed)}] processed")

    save_parquet(concat_frames(play_frames), PROCESSED_DIR / f"plays_{season}.parquet")
    save_parquet(concat_frames(shift_frames), PROCESSED_DIR / f"shifts_{season}.parquet")
    save_parquet(concat_frames(manpower_frames), PROCESSED_DIR / f"manpower_{season}.parquet")
    save_parquet(concat_frames(score_frames), PROCESSED_DIR / f"score_states_{season}.parquet")
    save_parquet(concat_frames(transition_frames), PROCESSED_DIR / f"score_transitions_{season}.parquet")

    if not skip_moneypuck:
        try:
            shots = load_moneypuck(client, season, RAW_DIR, refresh)
            save_parquet(shots, PROCESSED_DIR / f"moneypuck_shots_{season}.parquet")
            print(f"MoneyPuck: {len(shots):,} shots")
        except Exception as exc:
            failures.append({"source": "moneypuck", "error": str(exc)})
            print(f"MoneyPuck warning: {exc}")

    manifest = {
        "season": season,
        "game_types": game_types,
        "scheduled_games": len(games),
        "completed_games": len(completed),
        "failures": failures,
    }
    manifest_path = PROCESSED_DIR / f"manifest_{season}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Done. Failures: {len(failures)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build NHL game-state datasets")
    parser.add_argument("--season", type=int, required=True, help="YYYYYYYY, e.g. 20252026")
    parser.add_argument("--game-types", type=int, nargs="+", default=[2, 3])
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--skip-moneypuck", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Development-only game limit")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    process_season(
        args.season,
        args.game_types,
        refresh=args.refresh,
        skip_moneypuck=args.skip_moneypuck,
        limit=args.limit,
    )

