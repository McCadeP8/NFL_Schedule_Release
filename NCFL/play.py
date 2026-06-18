from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests

import data as data_module
from data import SLEEPER_API_BASE_URL, get_players, load_all_rosters, load_branding_data


EXPORT_DIRECTORY = Path(data_module.__file__).resolve().parent
NFLVERSE_PLAYERS_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
)


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
CONFERENCE_EXPORT_ALIASES = {
    "G6": "6IX",
    "F12": "The 12",
}
STARTER_COLUMNS = [
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


def _get_json(endpoint: str) -> Any:
    response = requests.get(f"{SLEEPER_API_BASE_URL}{endpoint}", timeout=30)
    response.raise_for_status()
    return response.json()


def _clean_conference(conference: str) -> str:
    return CONFERENCE_ALIASES.get(conference, conference)


def _export_conference(conference: str) -> str:
    return CONFERENCE_EXPORT_ALIASES.get(conference, conference)


def _requested_values(values: Iterable[Any] | None) -> set[str]:
    return {str(value).strip().casefold() for value in values or [] if str(value).strip()}


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
    years: Iterable[int] | None = None,
    conferences: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Load every weekly Sleeper matchup player, marking starters and bench."""
    league_ids_by_year = league_ids_by_year or LEAGUE_IDS_BY_YEAR
    requested_years = {int(year) for year in years or []}
    requested_conferences = _requested_values(
        _export_conference(conference) for conference in conferences or []
    )
    weeks = [int(week) for week in weeks]
    players = get_players()
    schools, *_ = load_branding_data()
    rows = []

    for year, leagues in league_ids_by_year.items():
        if requested_years and year not in requested_years:
            continue
        for conference, league_id in leagues.items():
            if requested_conferences and conference.casefold() not in requested_conferences:
                continue
            print(
                f"Fetching {year} {conference} from Sleeper league {league_id} "
                f"for weeks {min(weeks)}-{max(weeks)}..."
            )
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

    return pd.DataFrame(rows, columns=STARTER_COLUMNS).sort_values(
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


def get_all_app_players() -> pd.DataFrame:
    """Return one alphabetized Player column containing everyone shown in the app."""
    schools, _, _, _, _, drafts, starters, *_ = load_branding_data()
    rosters = load_all_rosters(schools)
    player_sources = []

    for frame, column in [
        (rosters, "player_name"),
        (starters, "Player"),
        (drafts, "Player"),
    ]:
        if not frame.empty and column in frame.columns:
            player_sources.append(frame[column])

    if not player_sources:
        return pd.DataFrame(columns=["Player"])

    players = pd.concat(player_sources, ignore_index=True).dropna().astype(str).str.strip()
    players = players.loc[
        players.ne("")
        & ~players.str.casefold().isin({"nan", "none", "tbd"})
    ]
    result = pd.DataFrame({"Player": players})
    result["_player_key"] = result["Player"].str.casefold()
    return (
        result.drop_duplicates("_player_key")
        .sort_values("_player_key")
        .drop(columns="_player_key")
        .reset_index(drop=True)
    )


def _player_match_key(value: object) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


def _first_existing_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str:
    normalized = {
        str(column).casefold().replace("-", "_").replace(" ", "_"): column
        for column in frame.columns
    }
    for candidate in candidates:
        key = candidate.casefold().replace("-", "_").replace(" ", "_")
        if key in normalized:
            return str(normalized[key])
    return ""


def get_all_app_player_images() -> pd.DataFrame:
    """Match every app player to verified nflverse/PFR identifiers and headshots."""
    schools, _, _, _, _, drafts, starters, *_ = load_branding_data()
    rosters = load_all_rosters(schools)
    source_frames = []

    for frame, name_column, id_column, source in [
        (rosters, "player_name", "player_id", "Current Roster"),
        (starters, "Player", "PlayerID", "Historical Roster"),
        (drafts, "Player", "PlayerID", "Draft"),
    ]:
        if frame.empty or name_column not in frame.columns:
            continue
        source_frame = pd.DataFrame({"Player": frame[name_column]})
        source_frame["SleeperID"] = (
            frame[id_column].astype("string")
            if id_column in frame.columns
            else pd.Series(pd.NA, index=frame.index, dtype="string")
        )
        source_frame["Source"] = source
        source_frames.append(source_frame)

    if not source_frames:
        return pd.DataFrame(
            columns=[
                "Player", "SleeperID", "PFRID", "HeadshotURL",
                "PFRHeadshotURL", "MatchMethod", "NeedsReview",
            ]
        )

    app_players = pd.concat(source_frames, ignore_index=True)
    app_players["Player"] = app_players["Player"].astype("string").str.strip()
    app_players["SleeperID"] = app_players["SleeperID"].astype("string").str.strip()
    app_players = app_players.loc[
        app_players["Player"].notna()
        & app_players["Player"].ne("")
        & ~app_players["Player"].str.casefold().isin({"nan", "none", "tbd"})
    ].copy()
    app_players["_name_key"] = app_players["Player"].map(_player_match_key)
    app_players = (
        app_players.sort_values(["_name_key", "SleeperID"], na_position="last")
        .drop_duplicates("_name_key")
    )

    nflverse = pd.read_csv(NFLVERSE_PLAYERS_URL, dtype="string")
    name_column = _first_existing_column(
        nflverse, ["display_name", "full_name", "player_name", "name"]
    )
    sleeper_column = _first_existing_column(
        nflverse, ["sleeper_id", "sleeper_player_id", "sleeper"]
    )
    pfr_column = _first_existing_column(
        nflverse, ["pfr_id", "pfr_player_id", "pfr"]
    )
    headshot_column = _first_existing_column(
        nflverse, ["headshot", "headshot_url", "image_url", "image"]
    )
    if not name_column:
        raise ValueError(
            "The nflverse player file has no recognized player-name column. "
            f"Available columns: {', '.join(map(str, nflverse.columns))}"
        )

    nflverse["_name_key"] = nflverse[name_column].map(_player_match_key)
    if sleeper_column:
        nflverse["_sleeper_id"] = nflverse[sleeper_column].astype("string").str.strip()
        id_lookup = (
            nflverse.dropna(subset=["_sleeper_id"])
            .drop_duplicates("_sleeper_id")
            .set_index("_sleeper_id")
        )
    else:
        id_lookup = pd.DataFrame()
        print(
            "nflverse players.csv does not currently include a Sleeper ID column; "
            "using unambiguous player-name matches."
        )
    unique_names = nflverse.loc[
        ~nflverse["_name_key"].duplicated(keep=False)
    ].drop_duplicates("_name_key").set_index("_name_key")

    rows = []
    for _, app_player in app_players.iterrows():
        sleeper_id = app_player["SleeperID"]
        match = None
        match_method = ""
        if not id_lookup.empty and pd.notna(sleeper_id) and sleeper_id in id_lookup.index:
            match = id_lookup.loc[sleeper_id]
            match_method = "Sleeper ID"
        elif app_player["_name_key"] in unique_names.index:
            match = unique_names.loc[app_player["_name_key"]]
            match_method = "Unique Name"

        pfr_value = match.get(pfr_column) if match is not None and pfr_column else pd.NA
        headshot_value = (
            match.get(headshot_column)
            if match is not None and headshot_column
            else pd.NA
        )
        pfr_id = "" if pd.isna(pfr_value) else str(pfr_value).strip()
        headshot = "" if pd.isna(headshot_value) else str(headshot_value).strip()
        if pfr_id.lower() in {"nan", "none", "<na>"}:
            pfr_id = ""
        if headshot.lower() in {"nan", "none", "<na>"}:
            headshot = ""
        rows.append(
            {
                "Player": app_player["Player"],
                "SleeperID": "" if pd.isna(sleeper_id) else sleeper_id,
                "PFRID": pfr_id,
                "HeadshotURL": headshot,
                "PFRHeadshotURL": (
                    f"https://www.pro-football-reference.com/req/20230307/images/headshots/{pfr_id}_2025.jpg"
                    if pfr_id
                    else ""
                ),
                "MatchMethod": match_method,
                "NeedsReview": not bool(match_method and (headshot or pfr_id)),
            }
        )

    return pd.DataFrame(rows).sort_values("Player", key=lambda values: values.str.casefold()).reset_index(drop=True)


def _write_export(frame: pd.DataFrame, filename: str, description: str) -> None:
    output_path = EXPORT_DIRECTORY / filename
    frame.to_csv(output_path, index=False)
    print(f"Wrote {len(frame):,} {description} to {output_path}")


def _merge_weekly_starters(
    new_rows: pd.DataFrame,
    years: Iterable[int] | None = None,
    conferences: Iterable[str] | None = None,
    weeks: Iterable[int] | None = None,
) -> pd.DataFrame:
    output_path = EXPORT_DIRECTORY / "weekly_starters.csv"
    if not output_path.exists():
        return new_rows

    existing = pd.read_csv(output_path)
    for column in STARTER_COLUMNS:
        if column not in existing.columns:
            existing[column] = pd.NA
        if column not in new_rows.columns:
            new_rows[column] = pd.NA
    existing = existing[STARTER_COLUMNS].copy()
    new_rows = new_rows[STARTER_COLUMNS].copy()

    if new_rows.empty:
        return existing

    replace_years = {int(year) for year in years or new_rows["Year"].dropna().astype(int).unique()}
    replace_conferences = {
        _export_conference(str(conference)).casefold()
        for conference in (conferences or new_rows["Conference"].dropna().astype(str).unique())
    }
    replace_weeks = {int(week) for week in weeks or new_rows["Week"].dropna().astype(int).unique()}

    existing["Year"] = pd.to_numeric(existing["Year"], errors="coerce")
    existing["Week"] = pd.to_numeric(existing["Week"], errors="coerce")
    keep_mask = ~(
        existing["Year"].isin(replace_years)
        & existing["Conference"].astype(str).str.casefold().isin(replace_conferences)
        & existing["Week"].isin(replace_weeks)
    )
    merged = pd.concat([existing.loc[keep_mask], new_rows], ignore_index=True)
    return merged.sort_values(
        ["Year", "Conference", "Week", "Team", "Position", "Player"],
        na_position="last",
    ).reset_index(drop=True)


def run_export(
    export: str = "images",
    years: Iterable[int] | None = None,
    conferences: Iterable[str] | None = None,
    weeks: Iterable[int] | None = None,
    merge: bool = False,
) -> None:
    """Write an NCFL export CSV beside data.py; defaults to player images."""
    if export == "starters":
        starters = get_weekly_starters(
            years=years,
            conferences=conferences,
            weeks=weeks or range(1, 19),
        )
        if merge:
            starters = _merge_weekly_starters(
                starters,
                years=years,
                conferences=conferences,
                weeks=weeks,
            )
        print(starters.head())
        _write_export(starters, "weekly_starters.csv", "rows")
    elif export == "drafts":
        draft_results = get_draft_results()
        print(draft_results.head())
        _write_export(draft_results, "draft_results.csv", "rows")
    elif export == "players":
        app_players = get_all_app_players()
        print(app_players.head())
        _write_export(app_players, "all_app_players.csv", "unique players")
    elif export == "images":
        player_images = get_all_app_player_images()
        print(player_images.head())
        _write_export(player_images, "all_app_player_images.csv", "player image rows")
    else:
        raise ValueError("export must be 'drafts', 'starters', 'players', or 'images'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export NCFL helper CSVs used by the Streamlit app."
    )
    parser.add_argument(
        "export",
        nargs="?",
        default="images",
        choices=["drafts", "starters", "players", "images"],
    )
    parser.add_argument(
        "--year",
        dest="years",
        action="append",
        type=int,
        help="Only export this season. Can be repeated.",
    )
    parser.add_argument(
        "--conference",
        dest="conferences",
        action="append",
        help="Only export this conference, for example MW. Can be repeated.",
    )
    parser.add_argument(
        "--week",
        dest="weeks",
        action="append",
        type=int,
        help="Only export this week. Can be repeated.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="For starters, replace the selected year/conference/week slice in weekly_starters.csv.",
    )
    args = parser.parse_args()
    run_export(
        args.export,
        years=args.years,
        conferences=args.conferences,
        weeks=args.weeks,
        merge=args.merge,
    )
