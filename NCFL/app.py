from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from data import LEAGUES, POSITIONS, load_all_rosters, load_branding_data


LEAGUE_NAME = "NCAA/NFL Crossover"
LEAGUE_LOGO = "https://upload.wikimedia.org/wikipedia/en/c/cf/NCAA_football_icon_logo.svg"
LEAGUE_ROSTER_ORDER = [
    "ACC",
    "B1G",
    "Big 12",
    "SEC",
    "Pac-12",
    "G6",
    "MW",
    "AAC",
    "MAC",
    "C-USA",
    "SBC",
    "F12",
]
ROSTER_STATUS_ORDER = {"Starter": 0, "Bench": 1, "Taxi": 2, "Reserve": 3}
POSITION_LABELS = {
    "QB": "Quarterback",
    "RB": "Running Back",
    "WR": "Wide Receiver",
    "TE": "Tight End",
}


def clean_text(value: object, fallback: str = "") -> str:
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    if text.lower() in {"", "nan", "none"}:
        return fallback
    return text


def esc(value: object, fallback: str = "") -> str:
    return html.escape(clean_text(value, fallback))


def first_value(frame: pd.DataFrame, column: str, fallback: str = "") -> str:
    if frame.empty or column not in frame.columns:
        return fallback
    values = frame[column].dropna().astype(str).str.strip()
    values = values.loc[~values.str.lower().isin(["", "nan", "none"])]
    return values.iloc[0] if len(values) else fallback


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
  justify-content: space-between;
  gap: 24px;
  padding: 36px 0 24px;
  border-bottom: 2px solid #e2e6ef;
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
  color: #4a5a78;
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
  min-width: 1180px;
}
.roster-table th {
  min-width: 138px;
  background: #f8fafc;
  border-bottom: 2px solid #e2e6ef;
  border-right: 1px solid #e8ecf3;
  padding: 10px 8px;
  vertical-align: bottom;
}
.team-head {
  border-top: 5px solid var(--team-color);
}
.team-head img {
  max-width: 112px;
  max-height: 44px;
  object-fit: contain;
}
.roster-table td {
  border-right: 1px solid #edf0f7;
  border-bottom: 1px solid #edf0f7;
  padding: 7px 10px;
  font-family: 'Barlow', sans-serif;
  font-size: 13px;
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
  min-width: 1120px;
}
.league-matrix .player-col {
  min-width: 230px;
  text-align: left;
}
.league-matrix .taken-col {
  min-width: 66px;
  text-align: center;
}
.taken-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 26px;
  border-radius: 5px;
  font-family: 'Rajdhani', sans-serif;
  font-size: 16px;
  font-weight: 800;
  color: #fff;
}
.conf-head img {
  width: 108px;
  height: 68px;
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
  max-width: 34px;
  max-height: 34px;
  object-fit: contain;
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
</style>
"""
    )


def masthead() -> None:
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
  <div class="mast-chip">12 Conferences</div>
</div>
"""
    )


def conference_logo(conferences: pd.DataFrame, conference: str) -> str:
    match = conferences.loc[conferences["Conference"].astype(str).eq(str(conference))]
    return first_value(match, "Logo", LEAGUE_LOGO)


def conference_code(conferences: pd.DataFrame, conference: str) -> str:
    match = conferences.loc[conferences["Conference"].astype(str).eq(str(conference))]
    return first_value(match, "Code", conference)


def taken_color(count: int) -> str:
    if count >= 10:
        return "#166534"
    if count >= 7:
        return "#3f8f29"
    if count >= 5:
        return "#d97706"
    if count >= 3:
        return "#dc2626"
    return "#7f1d1d"


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
                cells.append(f"<td>{esc(player[idx]) if idx < len(player) else ''}</td>")
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        st.html(
            f"""
<div class="roster-section">
  <div class="position-label"><span>{POSITION_LABELS.get(position, position)}</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
        )


def render_league_roster_matrix(rosters: pd.DataFrame, conferences: pd.DataFrame) -> None:
    conference_order = [conference for conference in LEAGUE_ROSTER_ORDER if conference in set(rosters["league_name"])]
    conference_logos = {
        conference: conference_logo(conferences, conference)
        for conference in conference_order
    }

    for position in POSITIONS:
        pos_rosters = rosters.loc[rosters["position"].eq(position)].copy()
        if pos_rosters.empty:
            continue

        rows = []
        for player_id, player_rows in pos_rosters.groupby("player_id"):
            player_name = first_value(player_rows, "player_name", str(player_id))
            row = {
                "player_id": player_id,
                "player_name": player_name,
                "taken_count": player_rows["league_name"].nunique(),
            }
            for conference in conference_order:
                match = player_rows.loc[player_rows["league_name"].eq(conference)]
                row[conference] = first_value(match, "team_logo", "")
                row[f"{conference}_team"] = first_value(match, "team_name", "")
            rows.append(row)

        matrix = pd.DataFrame(rows).sort_values(
            ["taken_count", "player_name"],
            ascending=[False, True],
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
        headers.append('<th class="taken-col">#</th>')

        body_rows = []
        for _, row in matrix.iterrows():
            cells = [f'<td class="player-col">{esc(row["player_name"])}</td>']
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
            cells.append(
                f'<td class="taken-col"><span class="taken-pill" style="background:{taken_color(taken_count)};">{taken_count}</span></td>'
            )
            body_rows.append(f"<tr>{''.join(cells)}</tr>")

        st.html(
            f"""
<div class="roster-section">
  <div class="position-label"><span>{POSITION_LABELS.get(position, position)}</span><div></div></div>
  <div class="roster-scroll">
    <table class="roster-table league-matrix">
      <thead><tr>{''.join(headers)}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</div>
"""
        )


def render_team_roster(rosters: pd.DataFrame, team_name: str) -> None:
    team = rosters.loc[rosters["team_name"].eq(team_name)].copy()
    if team.empty:
        st.warning("No roster rows found for this team.")
        return

    color = first_value(team, "team_color", "#1a2030")
    color2 = first_value(team, "team_color2", "#c8102e")
    logo = first_value(team, "team_logo", LEAGUE_LOGO)
    wordmark = first_value(team, "team_wordmark", "")
    conference = first_value(team, "league_name", "")
    hero_image = wordmark or logo

    st.html(
        f"""
<div class="team-hero" style="--team-color:{esc(color)};--team-color2:{esc(color2)};">
  <div>
    <div class="team-hero-sub">{esc(conference)} Roster</div>
    <div class="team-hero-title">{esc(team_name)}</div>
  </div>
  <img class="team-hero-wordmark" src="{esc(hero_image)}" alt="{esc(team_name)}">
  <img class="team-hero-logo" src="{esc(logo)}" alt="{esc(team_name)}">
</div>
"""
    )

    cards = []
    for position in POSITIONS:
        position_team = team.loc[team["position"].eq(position)].copy()
        position_team["status_sort"] = position_team["roster_spot"].map(ROSTER_STATUS_ORDER).fillna(9)
        players = (
            position_team[["player_name", "roster_spot", "nfl_team", "injury_status", "status_sort"]]
            .dropna(subset=["player_name"])
            .sort_values(["status_sort", "player_name"])
            .to_dict("records")
        )
        rows = "".join(
            f"""
<div class="player-row">
  <div class="player-main">
    <div class="player-name">{esc(player["player_name"])}</div>
    {f'<span class="injury-chip">{esc(clean_text(player.get("injury_status"))[:1].upper())}</span>' if clean_text(player.get("injury_status")) else ''}
  </div>
  <div class="player-meta">
    {f'<span class="nfl-chip">{esc(player.get("nfl_team"))}</span>' if clean_text(player.get("nfl_team")) else ''}
    <span>{esc(player["roster_spot"])}</span>
  </div>
</div>
"""
            for player in players
        )
        cards.append(
            f"""
<div class="position-card" style="--team-color:{esc(color)};">
  <div class="position-card-title">{POSITION_LABELS.get(position, position)}</div>
  {rows or '<div class="player-row"><div class="player-name"></div></div>'}
</div>
"""
        )

    st.html(f'<div class="team-roster-grid">{"".join(cards)}</div>')


st.set_page_config(
    page_title=LEAGUE_NAME,
    page_icon=LEAGUE_LOGO,
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()
masthead()

schools, conferences = load_branding_data()
all_rosters = load_all_rosters()

league_tab, conference_tab, team_tab = st.tabs(["League", "Conference", "Team"])

with league_tab:
    rosters_tab = st.tabs(["Rosters"])[0]
    with rosters_tab:
        render_league_roster_matrix(all_rosters, conferences)

with conference_tab:
    conference_options = [name for name in LEAGUES.keys() if name in set(conferences["Conference"].astype(str))]
    if not conference_options:
        conference_options = list(LEAGUES.keys())

    selected_conference = st.selectbox("Conference", conference_options)
    conference_rosters = all_rosters.loc[
        all_rosters["league_name"].eq(selected_conference)
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
    roster_tab = st.tabs(["Rosters"])[0]
    with roster_tab:
        render_roster_matrix(conference_rosters)

with team_tab:
    team_options = (
        all_rosters["team_name"]
        .dropna()
        .astype(str)
        .sort_values()
        .drop_duplicates()
        .tolist()
    )
    selected_team = st.selectbox("Team", team_options)
    team_roster_tab = st.tabs(["Rosters"])[0]
    with team_roster_tab:
        render_team_roster(all_rosters, selected_team)
