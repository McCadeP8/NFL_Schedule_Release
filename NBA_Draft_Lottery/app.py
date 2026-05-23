import html
import random
import time

import streamlit as st


st.set_page_config(
    page_title="NBA Draft Lottery Simulator",
    page_icon="\U0001F3B0",
    layout="wide",
)


TEAMS = [
    {
        "name": "Wizards",
        "abbr": "WAS",
        "balls": 2,
        "primary": "#002B5C",
        "secondary": "#E31837",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/was.png",
    },
    {
        "name": "Pacers",
        "abbr": "IND",
        "balls": 2,
        "primary": "#002D62",
        "secondary": "#FDBB30",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/ind.png",
    },
    {
        "name": "Nets",
        "abbr": "BKN",
        "balls": 2,
        "primary": "#000000",
        "secondary": "#777777",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/bkn.png",
    },
    {
        "name": "Jazz",
        "abbr": "UTA",
        "balls": 3,
        "primary": "#753BBD",
        "secondary": "#FFFFFF",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/utah.png",
    },
    {
        "name": "Kings",
        "abbr": "SAC",
        "balls": 3,
        "primary": "#5A2D81",
        "secondary": "#63727A",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/sac.png",
    },
    {
        "name": "Grizzlies",
        "abbr": "MEM",
        "balls": 3,
        "primary": "#5D76A9",
        "secondary": "#12173F",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mem.png",
    },
    {
        "name": "Mavericks",
        "abbr": "DAL",
        "balls": 3,
        "primary": "#00538C",
        "secondary": "#B8C4CA",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/dal.png",
    },
    {
        "name": "Pelicans",
        "abbr": "NOP",
        "balls": 3,
        "primary": "#0C2340",
        "secondary": "#C8102E",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/no.png",
    },
    {
        "name": "Bulls",
        "abbr": "CHI",
        "balls": 3,
        "primary": "#CE1141",
        "secondary": "#000000",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/chi.png",
    },
    {
        "name": "Bucks",
        "abbr": "MIL",
        "balls": 3,
        "primary": "#00471B",
        "secondary": "#EEE1C6",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mil.png",
    },
    {
        "name": "Warriors",
        "abbr": "GSW",
        "balls": 2,
        "primary": "#1D428A",
        "secondary": "#FFC72C",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/gs.png",
    },
    {
        "name": "Clippers",
        "abbr": "LAC",
        "balls": 2,
        "primary": "#C8102E",
        "secondary": "#1D428A",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/lac.png",
    },
    {
        "name": "Heat",
        "abbr": "MIA",
        "balls": 2,
        "primary": "#98002E",
        "secondary": "#F9A01B",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mia.png",
    },
    {
        "name": "Hornets",
        "abbr": "CHA",
        "balls": 2,
        "primary": "#1D1160",
        "secondary": "#00788C",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/cha.png",
    },
    {
        "name": "Suns",
        "abbr": "PHX",
        "balls": 1,
        "primary": "#1D1160",
        "secondary": "#E56020",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/phx.png",
    },
    {
        "name": "Magic",
        "abbr": "ORL",
        "balls": 1,
        "primary": "#0077C0",
        "secondary": "#C4CED4",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/orl.png",
    },
]


TEAM_BY_NAME = {team["name"]: team for team in TEAMS}
EXTRA_TEAMS = {
    "Hawks": {
        "name": "Hawks",
        "abbr": "ATL",
        "primary": "#E03A3E",
        "secondary": "#C1D32F",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/atl.png",
    },
    "Thunder": {
        "name": "Thunder",
        "abbr": "OKC",
        "primary": "#007AC1",
        "secondary": "#EF3B24",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/okc.png",
    },
    "Rockets": {
        "name": "Rockets",
        "abbr": "HOU",
        "primary": "#CE1141",
        "secondary": "#000000",
        "logo": "https://a.espncdn.com/i/teamlogos/nba/500/hou.png",
    },
}
DISPLAY_TEAM_BY_NAME = {**TEAM_BY_NAME, **EXTRA_TEAMS}
TOTAL_BALLS = sum(team["balls"] for team in TEAMS)
BOTTOM_PROTECTED_TEAMS = {"Wizards", "Pacers", "Nets"}
BOTTOM_PROTECTED_SLOTS = [12, 11, 10]
TOP_FIVE_SLOTS = {1, 2, 3, 4, 5}
AUTO_PULL_SECONDS = 5
FINAL_BALL_CLEAR_SECONDS = 2
OLD_LOTTERY_AVG_PICK = [
    3.6627,
    3.8629,
    4.0631,
    4.4381,
    4.9634,
    5.5324,
    6.2177,
    7.0412,
    8.0236,
    9.1893,
    10.3468,
    11.4008,
    12.5289,
    13.7265,
    15.0,
    16.0,
]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def make_ball_pool() -> list[dict[str, object]]:
    pool = []
    ball_number = 1
    for team in TEAMS:
        for team_ball in range(1, team["balls"] + 1):
            pool.append(
                {
                    "id": ball_number,
                    "team_ball": team_ball,
                    "team": team["name"],
                }
            )
            ball_number += 1
    return pool


def reset_lottery() -> None:
    st.session_state.draw_queue = make_ball_pool()
    random.shuffle(st.session_state.draw_queue)
    st.session_state.pulls = []
    st.session_state.auto_pull = False
    st.session_state.next_auto_pull_at = None
    st.session_state.latest_cleared = False
    st.session_state.final_ball_clear_at = None


def ensure_state() -> None:
    if "draw_queue" not in st.session_state or "pulls" not in st.session_state:
        reset_lottery()
    if "auto_pull" not in st.session_state:
        st.session_state.auto_pull = False
    if "next_auto_pull_at" not in st.session_state:
        st.session_state.next_auto_pull_at = None
    if "latest_cleared" not in st.session_state:
        st.session_state.latest_cleared = False
    if "final_ball_clear_at" not in st.session_state:
        st.session_state.final_ball_clear_at = None
    if "auto_pull_seconds" not in st.session_state:
        st.session_state.auto_pull_seconds = AUTO_PULL_SECONDS
    if "last_year_pick" not in st.session_state:
        st.session_state.last_year_pick = "Wizards"
    if "top_five_ineligible" not in st.session_state:
        st.session_state.top_five_ineligible = ["Jazz"]


def auto_pull_seconds() -> int:
    return int(st.session_state.get("auto_pull_seconds", AUTO_PULL_SECONDS))


def remaining_counts() -> dict[str, int]:
    counts = {team["name"]: 0 for team in TEAMS}
    for ball in st.session_state.draw_queue:
        counts[str(ball["team"])] += 1
    return counts


def pull_ball() -> None:
    if not st.session_state.draw_queue:
        st.session_state.auto_pull = False
        st.session_state.next_auto_pull_at = None
        return
    ball = st.session_state.draw_queue.pop(0)
    st.session_state.pulls.append(ball)
    st.session_state.latest_cleared = False
    st.session_state.final_ball_clear_at = None
    if not st.session_state.draw_queue:
        st.session_state.auto_pull = False
        st.session_state.next_auto_pull_at = None
        st.session_state.final_ball_clear_at = time.time() + FINAL_BALL_CLEAR_SECONDS


def start_auto_pull() -> None:
    st.session_state.auto_pull = True
    if st.session_state.draw_queue:
        st.session_state.next_auto_pull_at = time.time() + auto_pull_seconds()
    else:
        st.session_state.auto_pull = False
        st.session_state.next_auto_pull_at = None


def stop_auto_pull() -> None:
    st.session_state.auto_pull = False
    st.session_state.next_auto_pull_at = None


def back_one_ball() -> None:
    if not st.session_state.pulls:
        return
    ball = st.session_state.pulls.pop()
    st.session_state.draw_queue.append(ball)
    random.shuffle(st.session_state.draw_queue)
    if len(st.session_state.draw_queue) > 1 and st.session_state.draw_queue[0]["id"] == ball["id"]:
        st.session_state.draw_queue.append(st.session_state.draw_queue.pop(0))
    st.session_state.auto_pull = False
    st.session_state.next_auto_pull_at = None
    st.session_state.latest_cleared = False
    st.session_state.final_ball_clear_at = None


def exhausted_teams() -> list[str]:
    counts = {team["name"]: team["balls"] for team in TEAMS}
    exhausted = []
    for ball in st.session_state.pulls:
        team_name = str(ball["team"])
        counts[team_name] -= 1
        if counts[team_name] == 0:
            exhausted.append(team_name)
    return exhausted


def selected_last_year_pick() -> str:
    return str(st.session_state.get("last_year_pick", "None"))


def selected_top_five_ineligible() -> set[str]:
    return set(st.session_state.get("top_five_ineligible", []))


def pick_allowed(
    team_name: str,
    pick_number: int,
    last_year_pick: str | None = None,
    top_five_ineligible: set[str] | None = None,
) -> bool:
    last_year_pick = selected_last_year_pick() if last_year_pick is None else last_year_pick
    top_five_ineligible = (
        selected_top_five_ineligible() if top_five_ineligible is None else top_five_ineligible
    )
    if team_name == last_year_pick and pick_number == 1:
        return False
    if team_name in top_five_ineligible and pick_number <= 5:
        return False
    if team_name in BOTTOM_PROTECTED_TEAMS and pick_number > 12:
        return False
    return True


def draft_picks_from_exhaustion_order(
    exhausted: list[str],
    defer_pick_one: bool,
    last_year_pick: str | None = None,
    top_five_ineligible: set[str] | None = None,
) -> dict[int, str]:
    team_order = [team["name"] for team in TEAMS]

    def solve_candidate_slots(candidate_order: list[str]) -> dict[int, str]:
        candidates = tuple(dict.fromkeys(candidate_order))
        all_picks = tuple(range(16, 0, -1))
        memo: dict[tuple[int, tuple[int, ...]], dict[int, str] | None] = {}

        def solve(index: int, available_picks: tuple[int, ...]) -> dict[int, str] | None:
            key = (index, available_picks)
            if key in memo:
                return memo[key]
            if index == len(candidates):
                memo[key] = {}
                return {}

            team_name = candidates[index]
            for pick_number in available_picks:
                if not pick_allowed(team_name, pick_number, last_year_pick, top_five_ineligible):
                    continue
                next_available = tuple(pick for pick in available_picks if pick != pick_number)
                solved_rest = solve(index + 1, next_available)
                if solved_rest is None:
                    continue
                result = dict(solved_rest)
                result[pick_number] = team_name
                memo[key] = result
                return result

            memo[key] = None
            return None

        return solve(0, all_picks) or {}

    candidate_order = list(exhausted)
    picks = solve_candidate_slots(candidate_order)

    changed = True
    while changed:
        changed = False
        assigned = set(picks.values())
        unassigned = [team_name for team_name in team_order if team_name not in assigned]
        open_picks = [pick for pick in range(16, 0, -1) if pick not in picks]

        forced_team = None
        forced_pick = None

        blocked_teams = [
            team_name
            for team_name in unassigned
            if not any(pick_allowed(team_name, pick, last_year_pick, top_five_ineligible) for pick in open_picks)
        ]
        if blocked_teams:
            for team_name in blocked_teams:
                if team_name not in candidate_order:
                    candidate_order.append(team_name)
            picks = solve_candidate_slots(candidate_order)
            changed = True
            continue

        singleton_teams_by_pick: dict[int, list[str]] = {}
        for team_name in unassigned:
            legal_picks = [
                pick
                for pick in open_picks
                if pick_allowed(team_name, pick, last_year_pick, top_five_ineligible)
            ]
            if len(legal_picks) == 1:
                singleton_teams_by_pick.setdefault(legal_picks[0], []).append(team_name)

        for pick_number, team_names in singleton_teams_by_pick.items():
            if pick_number == 1 and defer_pick_one:
                continue
            if len(team_names) == 1:
                forced_team = team_names[0]
                forced_pick = pick_number
                break

        if forced_team is None:
            for pick_number in open_picks:
                if pick_number == 1 and defer_pick_one:
                    continue
                legal_teams = [
                    team_name
                    for team_name in unassigned
                    if pick_allowed(team_name, pick_number, last_year_pick, top_five_ineligible)
                ]
                if len(legal_teams) == 1:
                    forced_team = legal_teams[0]
                    forced_pick = pick_number
                    break

        if forced_team is not None and forced_pick is not None:
            candidate_order.append(forced_team)
            picks = solve_candidate_slots(candidate_order)
            changed = True

    return picks


def draft_picks() -> dict[int, str]:
    return draft_picks_from_exhaustion_order(
        exhausted_teams(),
        defer_pick_one=bool(st.session_state.draw_queue),
        last_year_pick=selected_last_year_pick(),
        top_five_ineligible=selected_top_five_ineligible(),
    )


def protected_pick_display(picks: dict[int, str], pick_number: int, original_team: str) -> tuple[str, str, str]:
    pelicans_pick = next((pick for pick, team in picks.items() if team == "Pelicans"), None)
    bucks_pick = next((pick for pick, team in picks.items() if team == "Bucks"), None)

    if original_team in {"Pelicans", "Bucks"}:
        if pelicans_pick and bucks_pick:
            better_pick = min(pelicans_pick, bucks_pick)
            worse_pick = max(pelicans_pick, bucks_pick)
            if pick_number == better_pick:
                if original_team == "Bucks":
                    return "Pelicans", "from MIL", "pelicans_better"
                return "Pelicans", "", "pelicans_better"
            if pick_number == worse_pick and pick_number > 4:
                return "Hawks", f"from {TEAM_BY_NAME[original_team]['abbr']}", "hawks_worse"
            if pick_number == worse_pick:
                if original_team == "Bucks":
                    return "Pelicans", "from MIL", "pelicans_better"
                return "Pelicans", "", "pelicans_better"
        elif original_team == "Bucks" and pick_number > 4:
            return "Hawks", "from MIL", "hawks_worse"
        elif original_team == "Bucks":
            return "Pelicans", "from MIL", "pelicans_better"
        elif original_team == "Pelicans" and pick_number > 4:
            return "Hawks", "from NOP", "hawks_worse"
        elif original_team == "Pelicans":
            return "Pelicans", "", "pelicans_better"

    if original_team == "Clippers":
        return "Thunder", "from LAC", "clippers_thunder"
    if original_team == "Heat" and pick_number > 14:
        return "Hornets", "from MIA", "heat_hornets"
    if original_team == "Jazz":
        return "Grizzlies", "from UTA", "jazz_grizzlies"
    if original_team == "Mavericks" and pick_number > 2:
        return "Hornets", "from DAL", "mavs_hornets"
    if original_team == "Nets":
        return "Rockets", "from BKN", "nets_rockets"
    if original_team == "Suns":
        return "Rockets", "from PHX", "suns_rockets"

    return original_team, "", ""


def inject_css() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@400;600;700;800;900&display=swap');

:root {
  --bg: #0D1117;
  --panel: #1C1F26;
  --text: #F0F3F5;
  --muted: #8EA1B8;
  --border: #3E92CC;
  --light: #6FB1FC;
  --lighter: #C3DDFD;
}

.stApp {
  background:
    radial-gradient(circle at 15% 0%, rgba(62, 146, 204, 0.18), transparent 28%),
    linear-gradient(180deg, #0D1117 0%, #111827 48%, #0D1117 100%);
  color: var(--text);
  font-family: 'Barlow Semi Condensed', sans-serif;
}

.block-container {
  max-width: 98vw;
  padding-left: 1rem;
  padding-right: 1rem;
  padding-top: 46px;
  padding-bottom: 20px;
}

h1, h2, h3, p, div, span, button {
  font-family: 'Barlow Semi Condensed', sans-serif !important;
}

.lottery-title {
  text-align: center;
  color: var(--lighter);
  font-size: clamp(30px, 3.4vw, 48px);
  font-weight: 900;
  line-height: 0.95;
  text-transform: uppercase;
  border-bottom: 3px solid var(--border);
  padding-bottom: 8px;
  margin: 0 0 4px;
}

.lottery-subtitle {
  text-align: center;
  color: var(--light);
  font-size: 16px;
  font-weight: 600;
  margin: 0 auto 6px;
  max-width: 880px;
}

.score-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 8px 0 10px;
}

.left-rail {
  border: 1px solid rgba(62, 146, 204, 0.75);
  border-radius: 8px;
  background: rgba(28, 31, 38, 0.52);
  padding: 8px 10px 10px;
}

.score-card {
  background: rgba(28, 31, 38, 0.94);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
}

.score-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.score-value {
  color: var(--text);
  font-size: 28px;
  font-weight: 900;
  line-height: 1;
}

.control-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin: 4px 0 22px;
}

div[data-testid="stButton"] button {
  background: #1C1F26 !important;
  color: #F0F3F5 !important;
  border: 2px solid #3E92CC !important;
  border-radius: 8px !important;
  font-family: 'Barlow Semi Condensed', sans-serif !important;
  font-size: 20px !important;
  font-weight: 900 !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
  min-height: 44px !important;
}

div[data-testid="stButton"] button:hover {
  background: #263343 !important;
  color: #ffffff !important;
  border-color: #6FB1FC !important;
}

div[data-testid="stButton"] button[kind="primary"] {
  min-height: 54px !important;
  background: linear-gradient(135deg, #F9C74F 0%, #F3722C 45%, #F94144 100%) !important;
  color: #0D1117 !important;
  border: 3px solid #ffffff !important;
  box-shadow: 0 0 0 3px rgba(62, 146, 204, 0.55), 0 10px 26px rgba(249, 199, 79, 0.25) !important;
  font-size: 24px !important;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.35) !important;
}

div[data-testid="stButton"] button[kind="primary"]:hover {
  background: linear-gradient(135deg, #FFE169 0%, #FF8C42 46%, #FF4D6D 100%) !important;
  color: #0D1117 !important;
  transform: translateY(-1px);
}

.section-kicker {
  color: var(--light);
  font-size: 13px;
  font-weight: 900;
  letter-spacing: 3px;
  margin: 9px 0 6px;
  text-transform: uppercase;
}

.settings-note {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  margin: -3px 0 4px;
}

.latest-stage {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) 132px minmax(220px, 0.72fr);
  gap: 10px;
  align-items: stretch;
  margin: 8px 0 10px;
}

.latest-card {
  position: relative;
  min-height: 150px;
  overflow: hidden;
  border: 2px solid var(--border);
  border-radius: 8px;
  background:
    radial-gradient(circle at 50% 36%, rgba(255,255,255,0.18), transparent 34%),
    linear-gradient(145deg, color-mix(in srgb, var(--latest-color) 62%, #0D1117), #111827 64%);
}

.latest-card-empty {
  display: grid;
  place-items: center;
  min-height: 150px;
  border: 2px dashed rgba(62, 146, 204, 0.8);
  border-radius: 8px;
  background: rgba(28, 31, 38, 0.82);
  color: var(--muted);
  font-size: 22px;
  font-weight: 900;
  letter-spacing: 2px;
  text-align: center;
  text-transform: uppercase;
}

.latest-label {
  position: absolute;
  top: 10px;
  left: 12px;
  color: rgba(255,255,255,0.78);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 3px;
  text-transform: uppercase;
}

.latest-team-name {
  position: absolute;
  left: 14px;
  bottom: 12px;
  color: #ffffff;
  font-size: clamp(26px, 3.4vw, 46px);
  font-weight: 900;
  line-height: 0.88;
  text-transform: uppercase;
}

.latest-ball {
  position: absolute;
  top: 50%;
  right: clamp(14px, 3vw, 42px);
  width: 104px;
  height: 104px;
  transform: translateY(-50%);
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at 32% 25%, #ffffff 0 20%, #f8fafc 42%, #d7e2ef 100%);
  border: 4px solid #ffffff;
}

.latest-ball img {
  width: 72px;
  height: 72px;
  object-fit: contain;
}

.latest-meta-panel {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.latest-meta {
  background: rgba(28, 31, 38, 0.94);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
}

.latest-meta-label {
  color: var(--muted);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.latest-meta-value {
  color: var(--text);
  font-size: 30px;
  font-weight: 900;
  line-height: 1;
  margin-top: 4px;
}

.countdown-panel {
  display: grid;
  align-content: center;
  border: 1px solid #F9C74F;
  border-radius: 8px;
  background: rgba(249, 199, 79, 0.12);
  color: #F9C74F;
  margin: 0;
  min-height: 150px;
  padding: 12px;
  text-align: center;
}

.countdown-top {
  display: grid;
  gap: 6px;
}

.countdown-label {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.countdown-value {
  color: #ffffff;
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
}

.countdown-idle {
  color: rgba(255,255,255,0.72);
  font-size: 24px;
}

.draw-board {
  background: rgba(28, 31, 38, 0.92);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-top: 12px;
  padding: 8px;
  min-height: 78px;
}

.draw-row {
  display: flex;
  gap: 7px;
  overflow-x: auto;
  padding: 2px 2px 6px;
}

.empty-draw {
  color: var(--muted);
  display: grid;
  min-height: 48px;
  place-items: center;
  font-size: 15px;
  font-weight: 700;
}

.pulled-ball {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: 1fr;
  place-items: center;
  background: #0D1117;
  border: 1px solid rgba(62, 146, 204, 0.72);
  border-radius: 8px;
  padding: 6px;
}

.ping-ball {
  width: 48px;
  height: 48px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at 32% 28%, #ffffff 0 22%, #f7fafc 44%, #dbe4ef 100%);
  border: 2px solid #ffffff;
  color: #0D1117;
}

.ping-ball img {
  width: 35px;
  height: 35px;
  object-fit: contain;
}

.team-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-flow: column;
  grid-template-rows: repeat(8, minmax(0, 1fr));
  gap: 5px;
  margin: 5px 0 0;
}

.team-tile {
  --team-color: #3E92CC;
  --team-color2: #6FB1FC;
  position: relative;
  min-height: 42px;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 8px;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--team-color) 58%, #0D1117), #1C1F26 72%),
    #1C1F26;
}

.team-tile.is-empty {
  opacity: 0.42;
  filter: saturate(0.62);
}

.team-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px 6px 46px;
}

.team-name {
  color: #ffffff;
  font-size: 14px;
  font-weight: 900;
  line-height: 0.95;
  max-width: 76px;
  text-transform: uppercase;
}

.team-abbr {
  color: rgba(255, 255, 255, 0.72);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 2px;
  margin-top: 4px;
}

.ball-count {
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: #ffffff;
  border: 2px solid rgba(255, 255, 255, 0.9);
  color: #0D1117;
  font-size: 19px;
  font-weight: 900;
}

.team-badges {
  display: flex;
  align-items: center;
  gap: 5px;
}

.odds-count {
  min-width: 52px;
  border: 2px solid rgba(255,255,255,0.72);
  border-radius: 999px;
  background: #05070b;
  color: #ffffff;
  font-size: 13px;
  font-weight: 900;
  line-height: 1;
  padding: 6px 7px;
  text-align: center;
}

.team-logo-band {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 40px;
  height: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.94);
  border-right: 4px solid var(--team-color2);
  border-top: 0;
}

.team-logo-band img {
  max-width: 29px;
  max-height: 29px;
  object-fit: contain;
}

.draft-board {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 8px;
}

.draft-column {
  overflow: hidden;
  border: 2px solid #3E92CC;
  border-radius: 8px;
  background: #071018;
}

.draft-header {
  background: linear-gradient(180deg, #326DA8, #1D3557);
  border-bottom: 2px solid #C3DDFD;
  color: #ffffff;
  font-size: 17px;
  font-weight: 900;
  letter-spacing: 2px;
  padding: 7px 12px;
  text-align: center;
  text-transform: uppercase;
}

.pick-row {
  display: grid;
  grid-template-columns: 50px 46px 1fr;
  align-items: center;
  min-height: 38px;
  border-bottom: 1px solid rgba(62, 146, 204, 0.55);
  background: linear-gradient(90deg, rgba(28,31,38,0.96), rgba(13,17,23,0.96));
}

.pick-row:last-child {
  border-bottom: 0;
}

.pick-number {
  display: grid;
  place-items: center;
  height: 100%;
  background: #0D1117;
  border-right: 1px solid rgba(195, 221, 253, 0.4);
  color: #F9C74F;
  font-size: 22px;
  font-weight: 900;
}

.pick-logo {
  display: grid;
  place-items: center;
}

.pick-logo img {
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.pick-team {
  color: #F0F3F5;
  font-size: 17px;
  font-weight: 900;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.pick-tag {
  display: inline-block;
  margin-left: 6px;
  transform: translateY(-2px);
  border: 1px solid rgba(249, 199, 79, 0.72);
  border-radius: 4px;
  color: #F9C74F;
  font-size: 8px;
  font-weight: 900;
  letter-spacing: 1px;
  padding: 1px 4px;
  vertical-align: middle;
}

.pick-footnote {
  color: #F9C74F;
  font-size: 11px;
  font-weight: 900;
  margin-left: 3px;
  vertical-align: super;
}

.pick-empty {
  color: #6b7a99;
}

.protections-footnote {
  border-top: 1px solid rgba(62, 146, 204, 0.55);
  color: #8EA1B8;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.35;
  margin-top: 10px;
  padding-top: 8px;
}

.protections-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 4px 18px;
  margin-top: 6px;
}

.protection-item {
  color: #8EA1B8;
}

.protection-item sup {
  color: #F9C74F;
  font-weight: 900;
}

.protections-footnote strong {
  color: #C3DDFD;
  font-weight: 900;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.odds-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(62, 146, 204, 0.7);
  border-radius: 8px;
  background: rgba(28, 31, 38, 0.82);
  margin-top: 10px;
}

.odds-table {
  width: 100%;
  min-width: 980px;
  border-collapse: collapse;
}

.odds-table th {
  background: #1D3557;
  border-bottom: 1px solid #3E92CC;
  color: #C3DDFD;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1px;
  padding: 7px 6px;
  text-align: center;
  text-transform: uppercase;
}

.odds-table td {
  border-bottom: 1px solid rgba(62, 146, 204, 0.22);
  color: #F0F3F5;
  font-size: 12px;
  font-weight: 800;
  padding: 6px;
  text-align: center;
}

.odds-table tr:last-child td {
  border-bottom: 0;
}

.odds-team-cell {
  min-width: 120px;
  text-align: left !important;
}

.odds-rank-cell {
  color: #C3DDFD !important;
  font-size: 13px !important;
  font-weight: 900 !important;
  min-width: 34px;
}

.odds-team {
  display: flex;
  align-items: center;
  gap: 7px;
}

.odds-team img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.odds-avg,
.odds-diff {
  color: #F9C74F !important;
  font-size: 13px !important;
}

.odds-diff.positive {
  color: #F94144 !important;
}

.odds-diff.negative {
  color: #43AA8B !important;
}

.odds-zero {
  color: rgba(240,243,245,0.32) !important;
}

.odds-footnote {
  color: #C3DDFD;
  font-size: 10px;
  font-weight: 900;
  margin-left: 3px;
  vertical-align: super;
}

@media (max-width: 1100px) {
  .latest-stage { grid-template-columns: 1fr; }
}

@media (max-width: 680px) {
  .score-strip { grid-template-columns: 1fr; }
  .team-grid { grid-template-columns: 1fr; }
  .team-tile { min-height: 112px; }
  .team-top { padding: 8px; }
  .team-logo-band {
    position: absolute;
    left: 0;
    right: 0;
    top: auto;
    bottom: 0;
    width: auto;
    height: 48px;
    border-right: 0;
    border-top: 4px solid var(--team-color2);
  }
  .latest-meta-panel { grid-template-columns: 1fr; }
  .draft-board { grid-template-columns: 1fr; }
  .latest-ball { width: 138px; height: 138px; right: 18px; }
  .latest-ball img { width: 98px; height: 98px; }
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_score_strip() -> None:
    remaining = len(st.session_state.draw_queue)
    pulled = len(st.session_state.pulls)
    active_teams = sum(1 for count in remaining_counts().values() if count > 0)
    st.markdown(
        f"""
<div class="score-strip">
  <div class="score-card">
    <div class="score-label">Balls Remaining</div>
    <div class="score-value">{remaining}</div>
  </div>
  <div class="score-card">
    <div class="score-label">Balls Pulled</div>
    <div class="score-value">{pulled}</div>
  </div>
  <div class="score-card">
    <div class="score-label">Teams Still Live</div>
    <div class="score-value">{active_teams}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_lottery_settings() -> None:
    st.markdown(
        """
<div class="section-kicker">Lottery Rules</div>
""",
        unsafe_allow_html=True,
    )
    team_names = [team["name"] for team in TEAMS]
    last_pick_col, ineligible_col = st.columns(2, gap="small")
    with last_pick_col:
        st.selectbox(
            "Last Year's #1 Pick",
            ["None", *team_names],
            key="last_year_pick",
        )
    with ineligible_col:
        st.multiselect(
            "Ineligible Top 5 Pick",
            team_names,
            key="top_five_ineligible",
            max_selections=5,
        )


def render_draw_row() -> None:
    old_pulls = st.session_state.pulls if st.session_state.latest_cleared else st.session_state.pulls[:-1]
    if not old_pulls:
        body = '<div class="empty-draw">Older pulled balls will slide in here after the next draw.</div>'
    else:
        items = []
        for ball in reversed(old_pulls):
            team = TEAM_BY_NAME[str(ball["team"])]
            items.append(
                f"""
<div class="pulled-ball" title="{esc(team['name'])} ball {ball['team_ball']}">
  <div class="ping-ball">
    <img src="{esc(team['logo'])}" alt="{esc(team['name'])}">
  </div>
</div>
"""
            )
        body = f'<div class="draw-row">{"".join(items)}</div>'

    st.markdown(
        f"""
<div class="draw-board">{body}</div>
""",
        unsafe_allow_html=True,
    )


def auto_countdown_html() -> str:
    if not st.session_state.auto_pull or not st.session_state.draw_queue:
        return """
<div class="countdown-panel">
  <div class="countdown-top">
    <div class="countdown-label">Next Auto Pull</div>
    <div class="countdown-idle">--</div>
  </div>
</div>
"""

    next_pull_at = st.session_state.next_auto_pull_at or time.time()
    seconds_left = max(0, int(next_pull_at - time.time()) + 1)
    return f"""
<div class="countdown-panel">
  <div class="countdown-top">
    <div class="countdown-label">Next Auto Pull</div>
    <div class="countdown-value">{seconds_left}s</div>
  </div>
</div>
"""


def render_latest_ball() -> None:
    if not st.session_state.pulls or st.session_state.latest_cleared:
        latest_html = """
<div class="latest-card-empty">Ready for the first pull</div>
"""
    else:
        latest = st.session_state.pulls[-1]
        team = TEAM_BY_NAME[str(latest["team"])]
        latest_html = f"""
<div class="latest-card" style="--latest-color:{esc(team['primary'])};">
  <div class="latest-label">Last Drawn Ball</div>
  <div class="latest-ball">
    <img src="{esc(team['logo'])}" alt="{esc(team['name'])}">
  </div>
  <div class="latest-team-name">{esc(team['name'])}</div>
</div>
"""

    picks = draft_picks()
    current_pick = len(picks)
    latest_pick = "Pending"
    if st.session_state.pulls and not st.session_state.latest_cleared:
        latest_team = str(st.session_state.pulls[-1]["team"])
        placed_pick = next((pick for pick, team in picks.items() if team == latest_team), None)
        if placed_pick:
            latest_pick = f"Pick {placed_pick}"
        else:
            latest_remaining = remaining_counts().get(latest_team, 0)
            latest_pick = f"{latest_remaining} left"

    st.markdown(
        f"""
<div class="section-kicker">Lottery Machine</div>
<div class="latest-stage">
  {latest_html}
  {auto_countdown_html()}
  <div class="latest-meta-panel">
    <div class="latest-meta">
      <div class="latest-meta-label">Current Pick Slots Filled</div>
      <div class="latest-meta-value">{current_pick}/16</div>
    </div>
    <div class="latest-meta">
      <div class="latest-meta-label">Latest Result</div>
      <div class="latest-meta-value">{esc(latest_pick)}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_team_tiles() -> None:
    counts = remaining_counts()
    first_pick_denominator = sum(
        counts[team["name"]]
        for team in TEAMS
        if counts[team["name"]] > 0 and pick_allowed(team["name"], 1)
    )
    cards = []
    for team in TEAMS:
        count = counts[team["name"]]
        if first_pick_denominator and count > 0 and pick_allowed(team["name"], 1):
            first_pick_pct = f"{(count / first_pick_denominator) * 100:.2f}%"
        else:
            first_pick_pct = "0.00%"
        empty_class = " is-empty" if count == 0 else ""
        cards.append(
            f"""
<div class="team-tile{empty_class}" style="--team-color:{esc(team['primary'])}; --team-color2:{esc(team['secondary'])};">
  <div class="team-top">
    <div>
      <div class="team-name">{esc(team['name'])}</div>
      <div class="team-abbr">{esc(team['abbr'])}</div>
    </div>
    <div class="team-badges">
      <div class="odds-count">{first_pick_pct}</div>
      <div class="ball-count">{count}</div>
    </div>
  </div>
  <div class="team-logo-band">
    <img src="{esc(team['logo'])}" alt="{esc(team['name'])}">
  </div>
</div>
"""
        )

    st.markdown(
        f"""
<div class="section-kicker">Lottery Teams</div>
<div class="team-grid">{"".join(cards)}</div>
""",
        unsafe_allow_html=True,
    )


def render_draft_board() -> None:
    picks = draft_picks()

    def pick_row(pick_number: int) -> str:
        team_name = picks.get(pick_number, "")
        if team_name:
            display_team_name, from_label, footnote_key = protected_pick_display(picks, pick_number, team_name)
            team = DISPLAY_TEAM_BY_NAME[display_team_name]
            logo = f'<img src="{esc(team["logo"])}" alt="{esc(team["name"])}">'
            footnote_numbers = {
                "hawks_worse": "1",
                "pelicans_better": "2",
                "clippers_thunder": "3",
                "heat_hornets": "4",
                "jazz_grizzlies": "5",
                "mavs_hornets": "6",
                "nets_rockets": "7",
                "suns_rockets": "8",
            }
            footnote_html = (
                f'<sup class="pick-footnote">{footnote_numbers[footnote_key]}</sup>'
                if footnote_key
                else ""
            )
            name = f"{esc(team['name'])}{footnote_html}"
            empty_class = ""
            tags = []
            if from_label:
                tags.append(from_label)
            if team_name in BOTTOM_PROTECTED_TEAMS:
                tags.append("12 FLOOR")
            if team_name == selected_last_year_pick():
                tags.append("NO REPEAT #1")
            if team_name in selected_top_five_ineligible():
                tags.append("TOP 5 INELIGIBLE")
            tag_html = "".join(f'<span class="pick-tag">{esc(tag)}</span>' for tag in tags)
        else:
            logo = ""
            name = "Awaiting draw"
            empty_class = " pick-empty"
            tag_html = ""
        return f"""
<div class="pick-row">
  <div class="pick-number">{pick_number}</div>
  <div class="pick-logo">{logo}</div>
  <div class="pick-team{empty_class}">{name}{tag_html}</div>
</div>
"""

    left = "".join(pick_row(i) for i in range(1, 9))
    right = "".join(pick_row(i) for i in range(9, 17))
    st.markdown(
        f"""
<div class="section-kicker">Draft Order</div>
<div class="draft-board">
  <div class="draft-column">
    <div class="draft-header">Picks 1-8</div>
    {left}
  </div>
  <div class="draft-column">
    <div class="draft-header">Picks 9-16</div>
    {right}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_pick_protections_note() -> None:
    st.html(
        """
<div class="protections-footnote">
  <strong>Pick Protections:</strong>
  <div class="protections-list">
    <div class="protection-item"><sup>1</sup> Atlanta receives the worse of New Orleans and Milwaukee if that pick lands outside the top 4.</div>
    <div class="protection-item"><sup>2</sup> New Orleans receives the better of its own pick and Milwaukee's pick.</div>
    <div class="protection-item"><sup>3</sup> Oklahoma City receives the Clippers pick.</div>
    <div class="protection-item"><sup>4</sup> Charlotte receives Miami's pick only if it lands outside the top 14.</div>
    <div class="protection-item"><sup>5</sup> Memphis receives Utah's pick.</div>
    <div class="protection-item"><sup>6</sup> Charlotte receives Dallas' pick if it lands outside the top 2.</div>
    <div class="protection-item"><sup>7</sup> Houston receives Brooklyn's pick.</div>
    <div class="protection-item"><sup>8</sup> Houston receives Phoenix's pick.</div>
  </div>
</div>
"""
    )


def team_protection_footnotes(team_name: str) -> str:
    footnotes_by_team = {
        "Pelicans": ["1", "2"],
        "Bucks": ["1", "2"],
        "Clippers": ["3"],
        "Heat": ["4"],
        "Jazz": ["5"],
        "Mavericks": ["6"],
        "Nets": ["7"],
        "Suns": ["8"],
    }
    return "".join(
        f'<sup class="odds-footnote">{number}</sup>'
        for number in footnotes_by_team.get(team_name, [])
    )


@st.cache_data(show_spinner=False)
def lottery_odds_table_data(
    last_year_pick: str,
    top_five_ineligible: tuple[str, ...],
    simulations: int = 100_000,
) -> list[dict[str, object]]:
    rng = random.Random(20260522)
    counts_by_team = {team["name"]: [0] * 17 for team in TEAMS}
    total_pick_by_team = {team["name"]: 0 for team in TEAMS}
    ineligible_set = set(top_five_ineligible)

    for _ in range(simulations):
        draw = make_ball_pool()
        rng.shuffle(draw)
        remaining = {team["name"]: team["balls"] for team in TEAMS}
        exhausted = []
        for ball in draw:
            team_name = str(ball["team"])
            remaining[team_name] -= 1
            if remaining[team_name] == 0:
                exhausted.append(team_name)

        picks = draft_picks_from_exhaustion_order(
            exhausted,
            defer_pick_one=False,
            last_year_pick=last_year_pick,
            top_five_ineligible=ineligible_set,
        )
        for pick_number, team_name in picks.items():
            counts_by_team[team_name][pick_number] += 1
            total_pick_by_team[team_name] += pick_number

    rows = []
    for index, team in enumerate(TEAMS):
        team_name = team["name"]
        rows.append(
            {
                "team": team_name,
                "logo": team["logo"],
                "old_avg": OLD_LOTTERY_AVG_PICK[index],
                "profile": (
                    team["balls"],
                    team_name == last_year_pick,
                    team_name in ineligible_set,
                    team_name in BOTTOM_PROTECTED_TEAMS,
                ),
                "odds": [
                    (counts_by_team[team_name][pick] / simulations) * 100
                    for pick in range(1, 17)
                ],
                "avg": total_pick_by_team[team_name] / simulations,
            }
        )

    profiles = {}
    for row_number, row in enumerate(rows, start=1):
        profiles.setdefault(row["profile"], []).append(row)

    for profile_rows in profiles.values():
        if len(profile_rows) <= 1:
            continue
        averaged_odds = [
            sum(float(row["odds"][index]) for row in profile_rows) / len(profile_rows)
            for index in range(16)
        ]
        averaged_avg = sum(float(row["avg"]) for row in profile_rows) / len(profile_rows)
        for row in profile_rows:
            row["odds"] = averaged_odds
            row["avg"] = averaged_avg

    balls_profiles = {}
    for row_number, row in enumerate(rows, start=1):
        balls_profiles.setdefault(row["profile"][0], []).append(row)

    for profile_rows in balls_profiles.values():
        if len(profile_rows) <= 1:
            continue
        for pick_index in range(6, 16):
            pick_number = pick_index + 1
            eligible_rows = [
                row
                for row in profile_rows
                if not bool(row["profile"][1])
                and not bool(row["profile"][3])
                and pick_allowed(str(row["team"]), pick_number, last_year_pick, ineligible_set)
            ]
            if len(eligible_rows) <= 1:
                continue
            average_value = sum(float(row["odds"][pick_index]) for row in eligible_rows) / len(eligible_rows)
            for row in eligible_rows:
                row["odds"][pick_index] = average_value

    for row_number, row in enumerate(rows, start=1):
        row["avg"] = sum(
            (pick_index + 1) * float(row["odds"][pick_index]) / 100
            for pick_index in range(16)
        )

    return rows


def render_lottery_odds_table() -> None:
    rows = lottery_odds_table_data(
        selected_last_year_pick(),
        tuple(sorted(selected_top_five_ineligible())),
    )
    header = "".join(f"<th>{pick}</th>" for pick in range(1, 17))
    column_maxes = [
        max(float(row["odds"][pick_index]) for row in rows)
        for pick_index in range(16)
    ]

    def odds_cell(value: float, column_max: float) -> str:
        if value <= 0 or column_max <= 0:
            return '<td class="odds-zero">0.00%</td>'
        intensity = value / column_max
        alpha = 0.08 + (0.56 * intensity)
        red = round(62 + ((67 - 62) * intensity))
        green = round(146 + ((170 - 146) * intensity))
        blue = round(204 + ((139 - 204) * intensity))
        color = "#F0F3F5"
        return (
            f'<td style="background:rgba({red},{green},{blue},{alpha:.2f});'
            f'color:{color};">{value:.2f}%</td>'
        )

    body_rows = []
    for row_number, row in enumerate(rows, start=1):
        team_name = str(row["team"])
        old_avg = float(row["old_avg"])
        new_avg = float(row["avg"])
        diff = new_avg - old_avg
        diff_class = "positive" if diff > 0 else "negative" if diff < 0 else ""
        odds_cells = "".join(
            odds_cell(float(value), column_maxes[index])
            for index, value in enumerate(row["odds"])
        )
        body_rows.append(
            f"""
<tr>
  <td class="odds-rank-cell">{row_number}</td>
  <td class="odds-team-cell">
    <div class="odds-team">
      <img src="{esc(row['logo'])}" alt="{esc(team_name)}">
      <span>{esc(team_name)}{team_protection_footnotes(team_name)}</span>
    </div>
  </td>
  {odds_cells}
  <td class="odds-avg">{old_avg:.2f}</td>
  <td class="odds-avg">{new_avg:.2f}</td>
  <td class="odds-diff {diff_class}">{diff:+.2f}</td>
</tr>
"""
        )

    st.html(
        f"""
<div class="section-kicker">Lottery Odds By Pick</div>
<div class="odds-table-wrap">
  <table class="odds-table">
    <thead>
      <tr>
        <th>#</th>
        <th class="odds-team-cell">Team</th>
        {header}
        <th>Old Avg</th>
        <th>Avg</th>
        <th>Diff</th>
      </tr>
    </thead>
    <tbody>
      {''.join(body_rows)}
    </tbody>
  </table>
</div>
"""
    )


ensure_state()
inject_css()

st.markdown(
    """
<div class="lottery-title">🎰 NBA Draft Lottery Simulator</div>
""",
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([0.35, 0.65], gap="medium")

with left_col:
    render_lottery_settings()
    render_team_tiles()
    render_draw_row()

with right_col:
    render_score_strip()

    pull_one_col, pull_remaining_col, seconds_col, back_col, reset_col = st.columns([0.32, 0.32, 0.10, 0.12, 0.14])
    with pull_one_col:
        st.button(
            "\U0001F3B2 Pull One Ball",
            key="pull_ball",
            type="primary",
            use_container_width=True,
            disabled=len(st.session_state.draw_queue) == 0 or st.session_state.auto_pull,
            on_click=pull_ball,
        )
    with pull_remaining_col:
        auto_button_label = "Stop Auto Pull" if st.session_state.auto_pull else "\U0001F3B2 Pull Remaining Balls"
        auto_button_callback = stop_auto_pull if st.session_state.auto_pull else start_auto_pull
        st.button(
            auto_button_label,
            key="pull_remaining_balls",
            type="primary",
            use_container_width=True,
            disabled=len(st.session_state.draw_queue) == 0 and not st.session_state.auto_pull,
            on_click=auto_button_callback,
        )
    with seconds_col:
        st.number_input(
            "Delay",
            min_value=1,
            max_value=30,
            step=1,
            key="auto_pull_seconds",
            label_visibility="visible",
            disabled=st.session_state.auto_pull,
        )
    with back_col:
        st.button(
            "Back",
            key="back_one_ball",
            use_container_width=True,
            disabled=not st.session_state.pulls,
            on_click=back_one_ball,
        )
    with reset_col:
        st.button("Reset", key="reset_lottery", use_container_width=True, on_click=reset_lottery)

    render_latest_ball()
    render_draft_board()

render_lottery_odds_table()
render_pick_protections_note()

if st.session_state.auto_pull:
    if st.session_state.draw_queue:
        if not st.session_state.next_auto_pull_at:
            st.session_state.next_auto_pull_at = time.time() + auto_pull_seconds()
        if time.time() >= st.session_state.next_auto_pull_at:
            pull_ball()
            if st.session_state.draw_queue:
                st.session_state.next_auto_pull_at = time.time() + auto_pull_seconds()
        else:
            time.sleep(1)
        st.rerun()
    else:
        st.session_state.auto_pull = False
        st.session_state.next_auto_pull_at = None

if st.session_state.final_ball_clear_at and not st.session_state.latest_cleared:
    if time.time() >= st.session_state.final_ball_clear_at:
        st.session_state.latest_cleared = True
        st.session_state.final_ball_clear_at = None
        st.rerun()
    else:
        time.sleep(1)
        st.rerun()
