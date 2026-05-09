import streamlit as st
import pandas as pd
import numpy as np
from lotteryodds import get_lottery_data, get_pick_probability, df, pick_cols

st.set_page_config(
    page_title="NBA Draft Lottery",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAM_DATA = {
    "Atlanta Hawks": {"abbr": "ATL", "color": "#c8102e", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/atl.png"},
    "Brooklyn Nets": {"abbr": "BKN", "color": "#000000", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/bkn.png"},
    "Charlotte Hornets": {"abbr": "CHA", "color": "#008ca8", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/cha.png"},
    "Chicago Bulls": {"abbr": "CHI", "color": "#ce1141", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/chi.png"},
    "Dallas Mavericks": {"abbr": "DAL", "color": "#0064b1", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/dal.png"},
    "Denver Nuggets": {"abbr": "DEN", "color": "#0e2240", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/den.png"},
    "Golden State Warriors": {"abbr": "GS", "color": "#fdb927", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/gs.png"},
    "Indiana Pacers": {"abbr": "IND", "color": "#0c2340", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/ind.png"},
    "LA Clippers": {"abbr": "LAC", "color": "#12173f", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/lac.png"},
    "Memphis Grizzlies": {"abbr": "MEM", "color": "#5d76a9", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mem.png"},
    "Miami Heat": {"abbr": "MIA", "color": "#98002e", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mia.png"},
    "Milwaukee Bucks": {"abbr": "MIL", "color": "#00471b", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/mil.png"},
    "New Orleans Pelicans": {"abbr": "NO", "color": "#0a2240", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/no.png"},
    "Oklahoma City Thunder": {"abbr": "OKC", "color": "#007ac1", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/okc.png"},
    "Sacramento Kings": {"abbr": "SAC", "color": "#5a2d81", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/sac.png"},
    "Utah Jazz": {"abbr": "UTAH", "color": "#4e008e", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/utah.png"},
    "Washington Wizards": {"abbr": "WSH", "color": "#e31837", "logo": "https://a.espncdn.com/i/teamlogos/nba/500/wsh.png"},
}

TEAM_DISPLAY = {
    "Wizards": "Washington Wizards",
    "Pacers": "Indiana Pacers",
    "Nets": "Brooklyn Nets",
    "Jazz": "Utah Jazz",
    "Kings": "Sacramento Kings",
    "Grizzlies": "Memphis Grizzlies",
    "Pelicans": "New Orleans Pelicans",
    "Mavericks": "Dallas Mavericks",
    "Bulls": "Chicago Bulls",
    "Bucks": "Milwaukee Bucks",
    "Warriors": "Golden State Warriors",
    "Clippers": "LA Clippers",
    "Heat": "Miami Heat",
    "Hornets": "Charlotte Hornets",
    "Hawks": "Atlanta Hawks",
    "Thunder": "Oklahoma City Thunder",
}

st.write("""
<style>
    :root {
        --bg-dark: #0f1419;
        --bg-card: #1a2332;
        --bg-alt: #2d3748;
        --accent: #4ecdc4;
        --text-light: #b0b8c1;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-dark) !important;
    }

    [data-testid="stMainBlockContainer"] {
        background-color: var(--bg-dark) !important;
        padding: 2rem 1rem;
    }

    h1, h2, h3 {
        color: white !important;
    }

    .lottery-table {
        width: 100%;
        border-collapse: collapse;
        background: linear-gradient(135deg, #1a2332 0%, #2d3748 100%);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        margin: 2rem 0;
    }

    .lottery-table thead {
        background: linear-gradient(135deg, #2d3748 0%, #1a2332 100%);
    }

    .lottery-table th {
        color: #4ecdc4;
        padding: 1.2rem 0.8rem;
        text-align: left;
        font-weight: 700;
        font-size: 0.9em;
        border-bottom: 2px solid #4ecdc4;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .lottery-table td {
        padding: 0.9rem 0.8rem;
        border-bottom: 1px solid #374153;
        color: #ffffff;
        font-size: 0.95em;
    }

    .lottery-table tbody tr:hover {
        background-color: rgba(78, 205, 196, 0.08);
    }

    .team-cell {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        font-weight: 600;
    }

    .team-logo {
        width: 40px;
        height: 40px;
        border-radius: 4px;
        object-fit: contain;
    }

    .prob-cell {
        text-align: center;
        font-weight: 700;
        font-family: 'Monaco', 'Courier New', monospace;
        font-size: 0.9em;
    }

    .prob-high {
        background: rgba(76, 175, 80, 0.25);
        color: #4caf50;
    }

    .prob-medium {
        background: rgba(255, 193, 7, 0.25);
        color: #ffc107;
    }

    .prob-low {
        background: rgba(244, 67, 54, 0.25);
        color: #f44336;
    }

    .prob-verylow {
        background: transparent;
        color: #90a4ae;
    }

    .rank-badge {
        display: inline-block;
        background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
        color: #0f1419;
        padding: 0.4rem 0.9rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9em;
    }

    .stat-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }

    .stat-card {
        background: linear-gradient(135deg, #1a2332 0%, #2d3748 100%);
        border: 1px solid #4ecdc4;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(78, 205, 196, 0.08);
        text-align: center;
    }

    .stat-number {
        font-size: 2.2em;
        font-weight: 800;
        color: #4ecdc4;
        margin-bottom: 0.5rem;
    }

    .stat-label {
        color: #b0b8c1;
        font-weight: 500;
    }

    .stat-sub {
        color: #7a8395;
        font-size: 0.85em;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

if "selections" not in st.session_state:
    st.session_state.selections = {}

st.markdown("# 🏀 NBA DRAFT LOTTERY SIMULATOR")
st.markdown("**Lock picks to explore conditional draft scenarios • Real-time probability calculations**")

st.markdown("## 🔒 Lock Picks")

# Get all currently selected teams to filter out duplicates
currently_selected = set(st.session_state.selections.values())

# First row of picks (1-7)
st.markdown("<div style='display: grid; grid-template-columns: repeat(7, 1fr); gap: 1rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)
cols = st.columns(7)
for pick_num in range(1, 8):
    col_idx = pick_num - 1
    with cols[col_idx]:
        st.markdown(f"<div style='text-align: center; color: #4ecdc4; font-weight: 700; font-size: 0.85em; margin-bottom: 0.5rem;'>PICK {pick_num}</div>", unsafe_allow_html=True)

        # Get available teams and filter out already selected ones
        available_teams = sorted(df[f"Pick{pick_num}"].unique().tolist())
        available_teams = [t for t in available_teams if t not in currently_selected or st.session_state.selections.get(pick_num) == t]
        available_teams = ["—"] + available_teams

        current_selection = st.session_state.selections.get(pick_num)
        default_idx = available_teams.index(current_selection) if current_selection in available_teams else 0

        selected = st.selectbox(
            f"Pick {pick_num}",
            available_teams,
            index=default_idx,
            key=f"pick_{pick_num}",
            label_visibility="collapsed"
        )

        if selected != "—":
            st.session_state.selections[pick_num] = selected
        else:
            if pick_num in st.session_state.selections:
                del st.session_state.selections[pick_num]

st.markdown("</div>", unsafe_allow_html=True)

# Second row of picks (8-14)
cols = st.columns(7)
for pick_num in range(8, 15):
    col_idx = pick_num - 8
    with cols[col_idx]:
        st.markdown(f"<div style='text-align: center; color: #4ecdc4; font-weight: 700; font-size: 0.85em; margin-bottom: 0.5rem;'>PICK {pick_num}</div>", unsafe_allow_html=True)

        # Get available teams and filter out already selected ones
        available_teams = sorted(df[f"Pick{pick_num}"].unique().tolist())
        available_teams = [t for t in available_teams if t not in currently_selected or st.session_state.selections.get(pick_num) == t]
        available_teams = ["—"] + available_teams

        current_selection = st.session_state.selections.get(pick_num)
        default_idx = available_teams.index(current_selection) if current_selection in available_teams else 0

        selected = st.selectbox(
            f"Pick {pick_num}",
            available_teams,
            index=default_idx,
            key=f"pick_{pick_num}",
            label_visibility="collapsed"
        )

        if selected != "—":
            st.session_state.selections[pick_num] = selected
        else:
            if pick_num in st.session_state.selections:
                del st.session_state.selections[pick_num]

filtered_data = get_lottery_data(st.session_state.selections if st.session_state.selections else None)

st.markdown("## 🏀 Original 14 Lottery Teams")

original_teams = ["Wizards", "Pacers", "Nets", "Jazz", "Kings", "Grizzlies", "Pelicans", "Mavericks", "Bulls", "Bucks", "Warriors", "Clippers", "Heat", "Hornets"]

# Map original teams to final team names (after transitions)
original_to_final = {
    "Wizards": "Wizards",
    "Pacers": "Pacers",
    "Nets": "Nets",
    "Jazz": "Jazz",
    "Kings": "Kings",
    "Grizzlies": "Grizzlies",
    "Pelicans": "Hawks",  # Pelicans pick goes to Hawks
    "Mavericks": "Mavericks",
    "Bulls": "Bulls",
    "Bucks": "Bucks",
    "Warriors": "Warriors",
    "Clippers": "Thunder",  # Clippers pick goes to Thunder
    "Heat": "Heat",
    "Hornets": "Hornets",
}

# Calculate combo count for each team getting #1 pick
team_combos = {}
for team in original_teams:
    final_team = original_to_final[team]
    count = len(df[df["Pick1"] == final_team])
    team_combos[team] = count

teams_html = "<div style='display: grid; grid-template-columns: repeat(14, 1fr); gap: 0.8rem; margin: 1.5rem 0;'>"

for team in original_teams:
    full_name = TEAM_DISPLAY.get(team, team)
    team_info = TEAM_DATA.get(full_name, {})
    logo_url = team_info.get("logo", "")
    color = team_info.get("color", "#ffffff")
    abbr = team_info.get("abbr", "")

    teams_html += "<div style='background: linear-gradient(135deg, " + color + "33 0%, " + color + "22 100%); border: 2px solid " + color + "; border-radius: 8px; padding: 0.8rem; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 0.4rem; height: 110px; justify-content: center; transition: all 0.3s ease;'>"
    teams_html += "<img src='" + logo_url + "' style='width: 40px; height: 40px; object-fit: contain;' alt='" + abbr + "'>"
    teams_html += "<div style='font-weight: 700; color: #ffffff; font-size: 0.8em; line-height: 1.1;'>" + team + "</div>"
    teams_html += "<div style='font-size: 0.65em; color: #b0b8c1;'>" + abbr + "</div>"
    teams_html += "</div>"

teams_html += "</div>"

st.write(teams_html, unsafe_allow_html=True)

st.markdown("## 📈 Pick Probability Matrix")
st.markdown("*Probability each team receives each pick, based on your locked selections*")

all_teams = sorted(set(
    team for col in pick_cols
    for team in filtered_data[col].unique()
    if team
))

matrix_html = """<table class="lottery-table"><thead><tr><th style="width: 180px;">Team</th>"""

for pick_num in range(1, 15):
    matrix_html += f"""<th style="width: 85px;">Pick {pick_num}</th>"""

matrix_html += """<th style="width: 100px;">Avg Pick</th></tr></thead><tbody>"""

for team in all_teams:
    full_name = TEAM_DISPLAY.get(team, team)
    team_info = TEAM_DATA.get(full_name, {})
    logo_url = team_info.get("logo", "")
    abbr = team_info.get("abbr", "")

    matrix_html += f"""
    <tr>
        <td style="position: sticky; left: 0; background: linear-gradient(135deg, #1a2332 0%, #2d3748 100%); z-index: 10;">
            <div class="team-cell">
                <img src="{logo_url}" class="team-logo" alt="{abbr}">
                <span>{team}</span>
            </div>
        </td>
    """

    avg_pick = 0.0
    total_prob = 0.0
    for pick_num in range(1, 15):
        prob = get_pick_probability(pick_num, team, st.session_state.selections if st.session_state.selections else None)
        prob_pct = prob * 100
        avg_pick += pick_num * prob
        total_prob += prob

        if prob_pct >= 5:
            prob_class = "prob-high"
        elif prob_pct >= 1:
            prob_class = "prob-medium"
        elif prob_pct >= 0.1:
            prob_class = "prob-low"
        else:
            prob_class = "prob-verylow"

        matrix_html += f"""<td class="prob-cell {prob_class}">{prob_pct:.2f}%</td>"""

    # Show average pick only if probabilities sum to ~100%
    if abs(total_prob - 1.0) > 0.01:
        avg_pick_display = "—"
    else:
        avg_pick_display = f"{avg_pick:.2f}"

    matrix_html += f"""<td class="prob-cell" style="background: rgba(78, 205, 196, 0.15); color: #4ecdc4; font-weight: 700;">{avg_pick_display}</td></tr>"""

matrix_html += """</tbody></table>"""

st.write(matrix_html, unsafe_allow_html=True)

st.markdown("## 📊 Scenario Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.write(f"""
    <div class="stat-cards" style="display: block;">
        <div class="stat-card">
            <div class="stat-number">{len(filtered_data):,}</div>
            <div class="stat-label">Total Scenarios</div>
            <div class="stat-sub">{(len(filtered_data) / len(df) * 100):.1f}% of all</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.write(f"""
    <div class="stat-cards" style="display: block;">
        <div class="stat-card">
            <div class="stat-number">{filtered_data['Probability'].sum() * 100:.2f}%</div>
            <div class="stat-label">Combined Probability</div>
            <div class="stat-sub">of outcomes</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg = (filtered_data['Probability'].sum() / len(filtered_data) * 100) if len(filtered_data) > 0 else 0
    st.write(f"""
    <div class="stat-cards" style="display: block;">
        <div class="stat-card">
            <div class="stat-number">{avg:.3f}%</div>
            <div class="stat-label">Avg Scenario Prob</div>
            <div class="stat-sub">per outcome</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.write(f"""
    <div class="stat-cards" style="display: block;">
        <div class="stat-card">
            <div class="stat-number">{len(st.session_state.selections)}</div>
            <div class="stat-label">Locked Picks</div>
            <div class="stat-sub">of 14</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("## 🎯 Most Likely Scenarios")

if len(filtered_data) > 0:
    top_scenarios = filtered_data.head(15).copy()

    # Normalize probabilities if filters are applied
    total_prob = filtered_data["Probability"].sum()
    if len(st.session_state.selections) > 0 and total_prob > 0:
        top_scenarios["Probability"] = top_scenarios["Probability"] / total_prob
        top_scenarios["Pct"] = (top_scenarios["Probability"] * 100).round(6)

    scenario_html = '<table class="lottery-table"><thead><tr><th style="width: 80px;">Rank</th>'

    for pick_num in range(1, 15):
        scenario_html += '<th style="width: 85px;">Pick ' + str(pick_num) + '</th>'

    scenario_html += '<th style="width: 120px;">Probability</th></tr></thead><tbody>'

    for idx, (_, row) in enumerate(top_scenarios.iterrows(), 1):
        scenario_html += '<tr><td><span class="rank-badge">#' + str(idx) + '</span></td>'

        for pick_num in range(1, 15):
            team = row[f'Pick{pick_num}']
            full_name = TEAM_DISPLAY.get(team, team)
            team_info = TEAM_DATA.get(full_name, {})
            logo_url = team_info.get("logo", "")
            abbr = team_info.get("abbr", "")

            scenario_html += '<td style="text-align: center;"><div style="display: flex; flex-direction: column; align-items: center; gap: 0.3rem;"><img src="' + logo_url + '" style="width: 32px; height: 32px; border-radius: 3px; object-fit: contain;" alt="' + abbr + '"><span style="font-size: 0.75em; color: #b0b8c1;">' + abbr + '</span></div></td>'

        prob_pct = row["Pct"]
        scenario_html += '<td style="text-align: center; font-weight: 700; color: #4ecdc4; font-family: Monaco, monospace;">' + f'{prob_pct:.4f}%' + '</td></tr>'

    scenario_html += '</tbody></table>'

    st.markdown(scenario_html, unsafe_allow_html=True)
else:
    st.warning("⚠️ No scenarios match your selections. Try adjusting your locked picks.")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #7a8395; font-size: 0.9em; margin-top: 2rem;">
    <p><strong>Lottery Details:</strong> Based on 24,024 possible scenarios</p>
    <p>Includes pick transitions: Clippers → Thunder | Pacers top-4 protection | Pelicans → Hawks | Hawks/Bucks swap</p>
</div>
""", unsafe_allow_html=True)
