from __future__ import annotations

import sys
from typing import Any, Iterable

import pandas as pd
import requests

from data import SLEEPER_API_BASE_URL, get_players, load_branding_data


LEAGUE_IDS_BY_YEAR: dict[int, dict[str, str]] = {
    2022: {
        "Big 12": "871796028209348608",
        "B1G": "872263979001704448",
        "SEC": "873261676571566080",
    },
    2023: {
        "Big 12": "963848350720180224",
        "B1G": "963848512859389952",
        "SEC": "963848545541427200",
        "Pac-12": "967162381887459328",
    },
    2024: {
        "Big 12": "1078447616993726464",
        "B1G": "1078475295969144832",
        "SEC": "1078476156040503296",
        "Pac-12": "1078476530650562560",
        "ACC": "1083802442891931648",
        "6IX": "1083802856966299648",
    },
    2025: {
        "Big 12": "1194778669893283840",
        "B1G": "1195503356091207680",
        "SEC": "1195503612499632128",
        "Pac-12": "1194797101762039808",
        "ACC": "1195502934522617856",
        "6IX": "1195502588011720704",
    },
    2026: {
        "Big 12": "1346983655301455872",
        "B1G": "1346983746389151744",
        "SEC": "1346983807705702400",
        "Pac-12": "1346983783475200000",
        "ACC": "1346983719008768000",
        "6IX": "1346983691322130432",
        "MW": "1349455273399431168",
        "MAC": "1349455814967971840",
        "C-USA": "1349455990495379456",
        "SBC": "1349456254895951872",
        "AAC": "1349456864814850048",
        "The 12": "1349457011871354880",
    },
}

CONFERENCE_ALIASES = {
    "6IX": "G6",
    "The 12": "F12",
}


def _get_json(endpoint: str) -> Any:
    response = requests.get(f"{SLEEPER_API_BASE_URL}{endpoint}", timeout=30)
    response.raise_for_status()
    return response.json()


def _clean_conference(conference: str) -> str:
    return CONFERENCE_ALIASES.get(conference, conference)


def _team_lookup(schools: pd.DataFrame, conference: str) -> dict[int, str]:
    if schools.empty or not {"School", "Conference", "TeamID"}.issubset(schools.columns):
        return {}

    school_rows = schools.loc[
        schools["Conference"].astype(str).eq(_clean_conference(conference))
    ].copy()
    school_rows["TeamID"] = pd.to_numeric(school_rows["TeamID"], errors="coerce")
    school_rows = school_rows.dropna(subset=["TeamID"])

    return {
        int(row["TeamID"]): str(row["School"]).strip()
        for _, row in school_rows.iterrows()
    }


def _roster_lookup(league_id: str, conference: str, schools: pd.DataFrame) -> dict[int, dict[str, str]]:
    roster_to_school = _team_lookup(schools, conference)
    rosters = _get_json(f"/league/{league_id}/rosters")
    lookup = {}

    for roster in rosters:
        roster_id = roster.get("roster_id")
        if roster_id is None:
            continue

        roster_id = int(roster_id)
        metadata = roster.get("metadata") or {}
        sleeper_team_name = metadata.get("team_name")
        lookup[roster_id] = {
            "Team": roster_to_school.get(roster_id) or sleeper_team_name or f"Roster {roster_id}",
            "SleeperTeamName": sleeper_team_name or "",
            "Players": [str(player_id) for player_id in (roster.get("players") or [])],
            "Reserve": {str(player_id) for player_id in (roster.get("reserve") or [])},
            "Taxi": {str(player_id) for player_id in (roster.get("taxi") or [])},
        }

    return lookup


def _matchups_for_week(league_id: str, week: int) -> list[dict[str, Any]]:
    try:
        matchups = _get_json(f"/league/{league_id}/matchups/{week}")
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            return []
        raise
    return matchups or []


def _player_points(
    matchup: dict[str, Any],
    player_id: Any,
    starter_index: int | None = None,
) -> Any:
    player_id = str(player_id)
    players_points = matchup.get("players_points") or {}
    if player_id in players_points:
        return players_points[player_id]

    starters_points = matchup.get("starters_points") or []
    if starter_index is not None and starter_index < len(starters_points):
        return starters_points[starter_index]

    return pd.NA


def _weekly_roster_rows_for_league(
    league_id: str,
    year: int,
    conference: str,
    players: pd.DataFrame,
    schools: pd.DataFrame,
    weeks: Iterable[int],
) -> list[dict[str, Any]]:
    player_lookup = players.set_index("player_id").to_dict("index")
    try:
        roster_lookup = _roster_lookup(league_id, conference, schools)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            print(
                f"Skipping {year} {conference}: Sleeper league id {league_id} was not found. "
                "This usually means the id was rounded/truncated."
            )
            return []
        raise
    rows = []

    for week in weeks:
        matchups = _matchups_for_week(league_id, week)
        if not matchups:
            continue

        for matchup in matchups:
            roster_id = matchup.get("roster_id")
            team_info = roster_lookup.get(
                int(roster_id),
                {
                    "Team": f"Roster {roster_id}",
                    "SleeperTeamName": "",
                    "Players": [],
                    "Reserve": set(),
                    "Taxi": set(),
                },
            )
            team_name = team_info["Team"]
            starters = matchup.get("starters") or []
            starter_indexes = {
                str(player_id): index
                for index, player_id in enumerate(starters)
                if player_id and str(player_id) != "0"
            }
            matchup_players = matchup.get("players") or starters
            if week == 18:
                matchup_players = list(
                    dict.fromkeys(
                        [str(player_id) for player_id in matchup_players]
                        + team_info.get("Players", [])
                    )
                )

            for player_id in matchup_players:
                if not player_id or str(player_id) == "0":
                    continue

                player_id = str(player_id)
                player = player_lookup.get(str(player_id), {})
                starter_index = starter_indexes.get(player_id)
                if starter_index is not None:
                    roster_spot = "Starter"
                elif player_id in team_info.get("Reserve", set()):
                    roster_spot = "Reserve"
                elif player_id in team_info.get("Taxi", set()):
                    roster_spot = "Taxi"
                else:
                    roster_spot = "Bench"
                rows.append(
                    {
                        "Team": team_name,
                        "SleeperTeamName": team_info.get("SleeperTeamName"),
                        "RosterID": roster_id,
                        "LeagueID": league_id,
                        "Position": player.get("position"),
                        "Player": player.get("player_name") or str(player_id),
                        "PlayerID": str(player_id),
                        "RosterSpot": roster_spot,
                        "Week": int(week),
                        "Year": int(year),
                        "Conference": conference,
                        "Points": _player_points(matchup, player_id, starter_index),
                        "TeamPoints": matchup.get("points"),
                    }
                )

    return rows


def get_weekly_starters(
    league_ids_by_year: dict[int, dict[str, str]] | None = None,
    weeks: Iterable[int] = range(1, 19),
) -> pd.DataFrame:
    """Load every weekly Sleeper matchup player, marking starters and bench."""
    league_ids_by_year = league_ids_by_year or LEAGUE_IDS_BY_YEAR
    players = get_players()
    schools, *_ = load_branding_data()
    rows = []

    for year, leagues in league_ids_by_year.items():
        for conference, league_id in leagues.items():
            rows.extend(
                _weekly_roster_rows_for_league(
                    league_id=str(league_id),
                    year=year,
                    conference=conference,
                    players=players,
                    schools=schools,
                    weeks=weeks,
                )
            )

    columns = [
        "Team",
        "SleeperTeamName",
        "RosterID",
        "LeagueID",
        "Position",
        "Player",
        "PlayerID",
        "RosterSpot",
        "Week",
        "Year",
        "Conference",
        "Points",
        "TeamPoints",
    ]
    return pd.DataFrame(rows, columns=columns).sort_values(
        ["Year", "Conference", "Week", "Team", "Position", "Player"],
        na_position="last",
    ).reset_index(drop=True)


def _draft_label(draft: dict[str, Any]) -> str:
    metadata = draft.get("metadata") or {}
    searchable = " ".join(
        str(value) for value in [draft.get("type"), *metadata.values()] if value
    ).lower()
    if "startup" in searchable or "start-up" in searchable or "start up" in searchable:
        return "Start-Up"
    return "Rookie"


def _draft_player_name(
    pick: dict[str, Any],
    player_lookup: dict[str, dict[str, Any]],
) -> str:
    metadata = pick.get("metadata") or {}
    full_name = metadata.get("full_name")
    if full_name:
        return str(full_name).strip()

    first_name = str(metadata.get("first_name") or "").strip()
    last_name = str(metadata.get("last_name") or "").strip()
    metadata_name = f"{first_name} {last_name}".strip()
    if metadata_name:
        return metadata_name

    player_id = str(pick.get("player_id") or "")
    return str(player_lookup.get(player_id, {}).get("player_name") or player_id)


def get_draft_results(
    league_ids_by_year: dict[int, dict[str, str]] | None = None,
) -> pd.DataFrame:
    """Load every available Sleeper draft pick into a sheet-ready dataframe."""
    league_ids_by_year = league_ids_by_year or LEAGUE_IDS_BY_YEAR
    players = get_players()
    player_lookup = players.set_index("player_id").to_dict("index")
    schools, *_ = load_branding_data()
    rows: list[dict[str, Any]] = []

    for year, leagues in league_ids_by_year.items():
        for conference, league_id in leagues.items():
            try:
                drafts = _get_json(f"/league/{league_id}/drafts") or []
                roster_lookup = _roster_lookup(league_id, conference, schools)
            except requests.HTTPError as exc:
                if exc.response is not None and exc.response.status_code == 404:
                    print(f"Skipping {year} {conference}: league was not found.")
                    continue
                raise

            for draft in drafts:
                draft_id = str(draft.get("draft_id") or "")
                if not draft_id:
                    continue

                try:
                    picks = _get_json(f"/draft/{draft_id}/picks") or []
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 404:
                        print(f"Skipping unavailable draft {draft_id}.")
                        continue
                    raise

                metadata = draft.get("metadata") or {}
                draft_name = metadata.get("name") or metadata.get("description") or ""
                draft_type = _draft_label(draft)

                for pick in picks:
                    roster_id = pick.get("roster_id")
                    roster_id_int = int(roster_id) if roster_id is not None else None
                    team_info = roster_lookup.get(roster_id_int, {})
                    pick_metadata = pick.get("metadata") or {}
                    player_id = str(pick.get("player_id") or "")
                    player = player_lookup.get(player_id, {})

                    rows.append(
                        {
                            "Year": int(year),
                            "Conference": _clean_conference(conference),
                            "Type": draft_type,
                            "Round": pick.get("round"),
                            "Pick": pick.get("draft_slot"),
                            "Team": team_info.get("Team") or f"Roster {roster_id}",
                            "Player": _draft_player_name(pick, player_lookup),
                            "PlayerID": player_id,
                            "Position": pick_metadata.get("position") or player.get("position"),
                            "NFLTeam": pick_metadata.get("team") or player.get("nfl_team"),
                            "OverallPick": pick.get("pick_no"),
                            "RosterID": roster_id,
                            "PickedBy": pick.get("picked_by"),
                            "DraftID": draft_id,
                            "LeagueID": str(league_id),
                            "DraftName": draft_name,
                            "SleeperDraftType": draft.get("type"),
                        }
                    )

    columns = [
        "Year",
        "Conference",
        "Type",
        "Round",
        "Pick",
        "Team",
        "Player",
        "PlayerID",
        "Position",
        "NFLTeam",
        "OverallPick",
        "RosterID",
        "PickedBy",
        "DraftID",
        "LeagueID",
        "DraftName",
        "SleeperDraftType",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    results = pd.DataFrame(rows, columns=columns)
    conference_order = [
        _clean_conference(conference)
        for leagues in league_ids_by_year.values()
        for conference in leagues
    ]
    conference_order = list(dict.fromkeys(conference_order))
    results["_ConferenceOrder"] = pd.Categorical(
        results["Conference"], categories=conference_order, ordered=True
    )
    results["_TypeOrder"] = results["Type"].map({"Rookie": 0, "Start-Up": 1}).fillna(2)
    return (
        results.sort_values(
            ["Year", "_ConferenceOrder", "_TypeOrder", "Round", "Pick", "OverallPick"],
            na_position="last",
        )
        .drop(columns=["_ConferenceOrder", "_TypeOrder"])
        .reset_index(drop=True)
    )


def run_export(export: str = "drafts") -> None:
    """Write a historical export CSV; defaults to draft results."""
    if export == "starters":
        starters = get_weekly_starters()
        starters.to_csv("weekly_starters.csv", index=False)
        print(starters.head())
        print(f"Wrote {len(starters):,} rows to weekly_starters.csv")
    elif export == "drafts":
        draft_results = get_draft_results()
        draft_results.to_csv("draft_results.csv", index=False)
        print(draft_results.head())
        print(f"Wrote {len(draft_results):,} rows to draft_results.csv")
    else:
        raise ValueError("export must be either 'drafts' or 'starters'")


if __name__ == "__main__":
    requested_export = next(
        (argument for argument in sys.argv[1:] if argument in {"drafts", "starters"}),
        "drafts",
    )
    run_export(requested_export)
