from __future__ import annotations

from io import StringIO
from typing import Any, Optional, Tuple

import pandas as pd
import requests


SLEEPER_API_BASE_URL = "https://api.sleeper.app/v1"

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
    "F12": "1349457011871354880",
}

CONFERENCE_LOGOS = {
    "ACC": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/acc.png",
    "B1G": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/big_ten.png",
    "Big 12": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/big_12.png",
    "SEC": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/sec.png",
    "Pac-12": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/pac_12.png",
    "G6": "https://pbs.twimg.com/media/HIuYl74bcAAQ-gW?format=jpg&name=large",
    "MW": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/mountain_west.png",
    "AAC": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/american.png",
    "MAC": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/mac.png",
    "C-USA": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/conference_usa.png",
    "SBC": "https://a.espncdn.com/i/teamlogos/ncaa_conf/500/sun_belt.png",
    "F12": "https://pbs.twimg.com/media/HIubVFzaMAAuABt?format=jpg&name=large",
}

CONFERENCE_ALIASES = {
    "FCS": "F12",
}

POSITIONS = ["QB", "RB", "WR", "TE"]


def _get_json(endpoint: str) -> Any:
    response = requests.get(f"{SLEEPER_API_BASE_URL}{endpoint}", timeout=30)
    response.raise_for_status()
    return response.json()


def get_players() -> pd.DataFrame:
    players = _get_json("/players/nfl")
    rows = []

    for player_id, player in players.items():
        rows.append(
            {
                "player_id": player_id,
                "player_name": player.get("full_name"),
                "position": player.get("position"),
                "nfl_team": player.get("team"),
                "injury_status": player.get("injury_status"),
            }
        )

    return pd.DataFrame(rows)


def get_rosters(league_id: Any) -> list[dict[str, Any]]:
    return _get_json(f"/league/{league_id}/rosters")


def get_roster(
    league_id: Any,
    players: Optional[pd.DataFrame] = None,
    league_name: Optional[str] = None,
) -> pd.DataFrame:
    rosters = get_rosters(league_id)
    if players is None:
        players = get_players()

    rows = []
    for roster in rosters:
        metadata = roster.get("metadata") or {}
        starters = set(roster.get("starters") or [])
        reserve = set(roster.get("reserve") or [])
        taxi = set(roster.get("taxi") or [])

        for player_id in roster.get("players") or []:
            if player_id in starters:
                roster_spot = "Starter"
            elif player_id in reserve:
                roster_spot = "Reserve"
            elif player_id in taxi:
                roster_spot = "Taxi"
            else:
                roster_spot = "Bench"

            rows.append(
                {
                    "league_id": str(roster.get("league_id")),
                    "league_name": league_name,
                    "roster_id": roster.get("roster_id"),
                    "owner_id": roster.get("owner_id"),
                    "sleeper_team_name": metadata.get("team_name"),
                    "player_id": player_id,
                    "roster_spot": roster_spot,
                }
            )

    roster_df = pd.DataFrame(rows)
    if roster_df.empty:
        return roster_df

    return roster_df.merge(players, on="player_id", how="left")


def _read_csv_url(url: str) -> pd.DataFrame:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return pd.read_csv(StringIO(response.text))


def _normalize_conference(value: object) -> str:
    conference = str(value).strip()
    return CONFERENCE_ALIASES.get(conference, conference)


def _is_image_url(value: object) -> bool:
    url = str(value).strip().lower()
    if not url or url == "nan":
        return False
    if "sports.core.api.espn.com" in url:
        return False
    return any(
        token in url
        for token in (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            "format=jpg",
            "format=png",
            "pbs.twimg.com/media",
        )
    )


def _fallback_conferences(schools: pd.DataFrame) -> pd.DataFrame:
    school_conferences = set(
        schools["Conference"].dropna().map(_normalize_conference).astype(str)
    )
    conferences = [name for name in LEAGUES if name in school_conferences]
    return pd.DataFrame(
        {
            "Conference": conferences,
            "Code": conferences,
            "Logo": [CONFERENCE_LOGOS.get(conference, "") for conference in conferences],
        }
    )


def get_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    schools_url = "https://docs.google.com/spreadsheets/d/19bH4vYzaV7pbuQ2bcdz3HAaOWGb-BBJhQ9EgBp7YvoY/export?format=csv&gid=0"
    conferences_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=1436567589"
    schools = _read_csv_url(schools_url)

    try:
        conferences = _read_csv_url(conferences_url)
        if "Conference" not in conferences.columns:
            conferences = _fallback_conferences(schools)
    except requests.HTTPError:
        conferences = _fallback_conferences(schools)

    conferences = conferences.copy()
    for column in ("Conference", "Code", "Logo"):
        if column not in conferences.columns:
            conferences[column] = ""
    conferences["Conference"] = conferences["Conference"].map(_normalize_conference)
    conferences["Code"] = conferences["Code"].map(_normalize_conference)
    conferences["Logo"] = conferences.apply(
        lambda row: row["Logo"]
        if _is_image_url(row["Logo"])
        else CONFERENCE_LOGOS.get(str(row["Conference"]).strip())
        or CONFERENCE_LOGOS.get(str(row["Code"]).strip(), ""),
        axis=1,
    )

    existing = set(conferences["Conference"].dropna().astype(str))
    missing = [conference for conference in LEAGUES if conference not in existing]
    if missing:
        conferences = pd.concat(
            [
                conferences,
                pd.DataFrame(
                    {
                        "Conference": missing,
                        "Code": missing,
                        "Logo": [CONFERENCE_LOGOS.get(conference, "") for conference in missing],
                    }
                ),
            ],
            ignore_index=True,
        )

    return schools, conferences


def enrich_rosters(rosters: pd.DataFrame, schools: pd.DataFrame) -> pd.DataFrame:
    schools = schools.copy()
    schools["TeamID"] = pd.to_numeric(schools["TeamID"], errors="coerce")
    schools["Conference"] = schools["Conference"].map(_normalize_conference)
    schools = schools.rename(
        columns={
            "School": "school",
            "Logo": "team_logo",
            "Conference": "conference",
            "Color": "team_color",
            "Color2": "team_color2",
            "Wordmark": "team_wordmark",
        }
    )

    enriched = rosters.merge(
        schools,
        left_on=["league_name", "roster_id"],
        right_on=["conference", "TeamID"],
        how="left",
    )
    enriched["team_name"] = enriched["school"].fillna(enriched["sleeper_team_name"])
    enriched["team_name"] = enriched["team_name"].fillna(
        "Roster " + enriched["roster_id"].astype(str)
    )
    enriched["team_color"] = enriched["team_color"].fillna("#1a2030")
    enriched["team_color2"] = enriched["team_color2"].fillna("#c8102e")

    return enriched.sort_values(
        ["league_name", "team_name", "position", "player_name"],
        na_position="last",
    ).reset_index(drop=True)


def load_all_rosters() -> pd.DataFrame:
    players = get_players()
    schools, _ = get_data()
    league_rosters = []

    for league_name, league_id in LEAGUES.items():
        league_rosters.append(
            get_roster(
                league_id=league_id,
                players=players,
                league_name=league_name,
            )
        )

    return enrich_rosters(pd.concat(league_rosters, ignore_index=True), schools)


def load_branding_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    return get_data()


def position_table(rosters: pd.DataFrame, position: str) -> pd.DataFrame:
    filtered = rosters.loc[rosters["position"].eq(position)].copy()
    if filtered.empty:
        return pd.DataFrame()

    filtered["player_label"] = filtered["player_name"].fillna(filtered["player_id"])
    team_players = {}

    for team_name, team_roster in filtered.groupby("team_name"):
        team_players[team_name] = sorted(team_roster["player_label"].dropna())

    return pd.DataFrame.from_dict(team_players, orient="index").transpose().fillna("")
