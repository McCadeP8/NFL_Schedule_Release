"""Fallback shift source: the NHL's official HTML time-on-ice reports.

The stats API occasionally returns an empty shift chart for completed games.
The TH (home) / TV (visitor) HTML reports carry the same shifts, so they are
converted into the shiftcharts payload shape consumed by ``normalize_shifts``.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import requests

REPORT_URL = "https://www.nhl.com/scores/htmlreports/{season}/{prefix}{game_suffix}.HTM"
_HEADING = re.compile(r'class="playerHeading[^"]*"[^>]*>(\d+)\s+([^<]*)</td>')
_ROW = re.compile(
    r"<tr class=\"\s*(?:odd|even)Color\">(.*?)</tr>", re.DOTALL
)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)


def _fetch(url: str, cache_path: Path, refresh: bool, timeout: int = 45) -> str:
    if cache_path.exists() and not refresh:
        return cache_path.read_text(encoding="utf-8")
    response = requests.get(
        url, timeout=timeout, headers={"User-Agent": "NHL-State-Lab/0.1 (public analytics project)"}
    )
    response.raise_for_status()
    text = response.content.decode("utf-8", errors="replace")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    return text


def _period(value: str) -> int:
    value = value.strip().upper()
    if value.isdigit():
        return int(value)
    return 4 if value.startswith("OT") else 0


def parse_report(text: str) -> list[dict[str, Any]]:
    """Return (sweater, period, shift_number, start, end) rows from one team report."""
    rows: list[dict[str, Any]] = []
    headings = list(_HEADING.finditer(text))
    for index, heading in enumerate(headings):
        sweater = int(heading.group(1))
        stop = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        block = text[heading.end():stop]
        for row in _ROW.finditer(block):
            cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in _CELL.findall(row.group(1))]
            if len(cells) < 5 or not cells[0].isdigit() or "/" not in cells[2] or "/" not in cells[3]:
                continue
            rows.append(
                {
                    "sweater": sweater,
                    "shiftNumber": int(cells[0]),
                    "period": _period(cells[1]),
                    "startTime": cells[2].split("/")[0].strip(),
                    "endTime": cells[3].split("/")[0].strip(),
                }
            )
    return rows


def html_shift_payload(
    game: dict[str, Any], pbp: dict[str, Any], cache_dir: Path, refresh: bool = False
) -> dict[str, Any]:
    """Build a shiftcharts-style payload ({"data": [...]}) from the HTML reports."""
    game_id = str(game["game_id"])
    season = f"{game_id[:4]}{int(game_id[:4]) + 1}"
    by_sweater = {
        (spot.get("teamId"), int(spot.get("sweaterNumber"))): int(spot["playerId"])
        for spot in pbp.get("rosterSpots", [])
        if spot.get("sweaterNumber") is not None and spot.get("playerId") is not None
    }
    data = []
    for prefix, team_id, team in (
        ("TH", game["home_id"], game["home_team"]),
        ("TV", game["away_id"], game["away_team"]),
    ):
        url = REPORT_URL.format(season=season, prefix=prefix, game_suffix=game_id[4:])
        text = _fetch(url, cache_dir / f"{game_id}_{prefix}.htm", refresh)
        for row in parse_report(text):
            player_id = by_sweater.get((team_id, row.pop("sweater")))
            if player_id is None:
                continue
            data.append({**row, "playerId": player_id, "teamId": team_id, "teamAbbrev": team})
    return {"data": data, "total": len(data), "source": "html_toi_report"}
