import math
import streamlit as st
import pandas as pd
import pydeck as pdk
from data import get_games

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NFL Schedule Hub",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

Games, Team_Info, Other_Locations = get_games()

# Keep only seasons currently in scope from GameID (e.g., "2026_001").
if 'GameID' in Games.columns:
    _gid = Games['GameID'].astype(str).str.strip()
    _season_mask = _gid.str[:4].isin(['2025', '2026'])
    Games = Games[_season_mask].copy()
    Games['_season'] = _gid.str[:4]
else:
    Games = Games.copy()
    Games['_season'] = ''

# Normalize schedule placeholders for 2026 data still missing week/date.
Games['Week'] = pd.to_numeric(Games.get('Week'), errors='coerce').astype('Int64')
_is_2026 = Games['_season'] == '2026'
_date_blank = Games.get('Date').isna() | (Games.get('Date').astype(str).str.strip() == '')
Games.loc[_is_2026 & _date_blank, 'Date'] = 'TBA'

# Normalize known abbreviation collisions so team colors stay consistent.

# Keep a source copy; we will scope Games by selected season for the full app.
ALL_GAMES = Games.copy()

def _clean_text(v):
    s = str(v or '').strip()
    return '' if s.lower() in ('', 'nan', 'none') else s

def _safe_float(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except Exception:
        return None

# Canonical venue/geo source now comes from Other_Locations.
TEAM_STAD_MAP = {}
TEAM_CITY_MAP = {}
TEAM_LAT_MAP = {}
TEAM_LON_MAP = {}
TEAM_TZ_MAP = {}
INTL_DATA = {}
NEUTRAL_LOCATION_SET = set()

_known_teams = set(Team_Info['Team'].astype(str).str.strip())
_known_abbs = set(Team_Info['Abb'].astype(str).str.strip()) if 'Abb' in Team_Info.columns else set()

_ol_by_team = {}
_ol_by_abb = {}
_ol_by_loc = {}
if Other_Locations is not None and len(Other_Locations) > 0:
    for _, r in Other_Locations.iterrows():
        loc = _clean_text(r.get('Location', ''))
        stad = _clean_text(r.get('Stadium Name', ''))
        lat = _safe_float(r.get('Lattitude', r.get('Latitude', None)))
        lon = _safe_float(r.get('Longitude', None))
        tz = _clean_text(r.get('Time Zone', ''))
        team_hint = _clean_text(
            r.get('Team', r.get('Franchise', r.get('Club', r.get('Home', ''))))
        )
        abb_hint = _clean_text(
            r.get('Abb', r.get('Abbreviation', r.get('Abv', '')))
        )
        entry = {'city': loc, 'stad': stad, 'lat': lat, 'lon': lon, 'tz': tz}

        if team_hint:
            _ol_by_team[team_hint] = entry
        if abb_hint:
            _ol_by_abb[abb_hint] = entry
        if loc:
            _ol_by_loc[loc] = entry
            INTL_DATA[loc] = entry

        associated = (team_hint in _known_teams) or (team_hint in _known_abbs) or (abb_hint in _known_abbs)
        if loc and not associated:
            NEUTRAL_LOCATION_SET.add(loc)

for _, tr in Team_Info.iterrows():
    t = _clean_text(tr.get('Team', ''))
    if not t:
        continue
    abb = _clean_text(tr.get('Abb', ''))
    loc_hint = _clean_text(tr.get('Location', ''))
    picked = _ol_by_team.get(t) or _ol_by_abb.get(abb) or _ol_by_loc.get(loc_hint) or {}
    TEAM_STAD_MAP[t] = _clean_text(picked.get('stad', ''))
    TEAM_CITY_MAP[t] = _clean_text(picked.get('city', loc_hint))
    TEAM_LAT_MAP[t] = picked.get('lat', None)
    TEAM_LON_MAP[t] = picked.get('lon', None)
    TEAM_TZ_MAP[t] = _clean_text(picked.get('tz', ''))

# ── CSS ───────────────────────────────────────────────────────────────────────
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@400;500;600;700;800&family=Barlow:wght@300;400;500;600&family=Rajdhani:wght@500;600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Barlow', sans-serif;
  background-color: #f4f6fa;
  color: #1a2030;
}
.stApp { background: #f4f6fa; }
#MainMenu, footer, header { visibility: hidden; }
.block-container {
  padding-top: 0 !important;
  padding-left: 2.5rem !important;
  padding-right: 2.5rem !important;
  max-width: 1760px !important;
}

/* Masthead */
.masthead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28px 0 24px;
  border-bottom: 2px solid #e2e6ef;
  background: #f4f6fa;
}
.masthead-left { display: flex; align-items: center; gap: 20px; }
.nfl-logo {
  width: 60px; height: 60px; object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(200,16,46,0.25));
}
.masthead-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size:78px; letter-spacing: 4px;
  line-height: 1; color: #111827; margin: 0;
}
.masthead-sub {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:15px; font-weight: 800;
  letter-spacing: 5px; text-transform: uppercase;
  color: #c8102e; margin-bottom: 5px;
}
.season-tag {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:18px; font-weight: 700;
  letter-spacing: 3px; text-transform: uppercase;
  color: #6b7a99; background: #ffffff;
  border: 1px solid #dde2ed;
  padding: 8px 18px; border-radius: 4px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  background: #f4f6fa;
  border-bottom: 2px solid #e2e6ef;
  gap: 0; padding: 0;
}
.stTabs [data-baseweb="tab"] {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:20px; font-weight: 700;
  letter-spacing: 2.5px; text-transform: uppercase;
  color: #9aa5be; background: transparent;
  border: none; border-bottom: 2px solid transparent;
  padding: 16px 26px; margin: 0;
  transition: color 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover { color: #4a5a78; }
.stTabs [aria-selected="true"] {
  color: #111827 !important;
  border-bottom: 2px solid #c8102e !important;
  background: transparent !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-panel"] { padding: 0; background: #f4f6fa; }

/* Input labels */
div[data-testid="stWidgetLabel"],
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] span,
label[data-testid="stWidgetLabel"],
label[data-testid="stWidgetLabel"] p,
label[data-testid="stWidgetLabel"] span {
  color: #1a2030 !important;
  opacity: 1 !important;
}

/* Conference header */
.conf-header {
  display: flex; align-items: center;
  gap: 16px; margin: 20px 0 8px;
}
.conf-header.first { margin-top: 8px; }
.conf-header-line { flex: 1; height: 1px; background: #dde2ed; }
.conf-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:15px; font-weight: 800;
  letter-spacing: 6px; text-transform: uppercase;
  color: #b0baca; white-space: nowrap;
}

/* Legend */
.legend-bar {
  margin-top: 18px; margin-bottom: 8px;
  display: flex; flex-wrap: wrap;
  align-items: center; justify-content: center; gap: 0;
  background: #ffffff;
  border: 1px solid #e2e6ef; border-radius: 6px;
  padding: 10px 18px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.legend-title {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:14px; font-weight: 800;
  letter-spacing: 5px; text-transform: uppercase;
  color: #b0baca; padding-right: 18px; margin-right: 4px;
  border-right: 1px solid #e2e6ef;
}
.legend-item {
  display: flex; align-items: center; justify-content: center;
  gap: 7px; padding: 4px 14px;
  border-right: 1px solid #e2e6ef;
}
.legend-item:last-child { border-right: none; }
.legend-swatch { width: 26px; height: 14px; border-radius: 3px; flex-shrink: 0; }
.legend-text {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:15px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: #8a96b0; white-space: nowrap;
}
.legend-code {
  font-family: 'Rajdhani', sans-serif;
  font-size:20px; font-weight: 700; color: #4a5a78;
}

/* Under Construction */
.uc-wrapper {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 55vh; padding: 60px 20px; text-align: center;
}
.uc-icon { font-size:84px; margin-bottom: 24px; animation: pulse 3s ease-in-out infinite; }
@keyframes pulse { 0%,100%{transform:scale(1);opacity:1;} 50%{transform:scale(1.05);opacity:0.6;} }
.uc-label {
  font-family: 'Barlow Condensed', sans-serif;
  font-size:15px; font-weight: 800;
  letter-spacing: 6px; text-transform: uppercase;
  color: #c8102e; margin-bottom: 12px;
}
.uc-title {
  font-family: 'Bebas Neue', sans-serif;
  font-size:102px; letter-spacing: 5px;
  color: #1a2030; line-height: 1; margin-bottom: 16px;
}
.uc-sub {
  font-family: 'Barlow', sans-serif;
  font-size:22px; font-weight: 400;
  color: #9aa5be; max-width: 360px; line-height: 1.8;
}
</style>
""")

# ── Masthead ──────────────────────────────────────────────────────────────────
NFL_LOGO = "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/NFL.png"
TBD_LOGO = "https://pbs.twimg.com/media/HGxbwo2aEAA_HeG?format=jpg&name=large"
st.html(f"""
<div class="masthead">
  <div class="masthead-left">
    <img class="nfl-logo" src="{NFL_LOGO}" alt="NFL">
    <div>
      <div class="masthead-sub">Schedule Hub</div>
      <div class="masthead-title">NFL SCHEDULE</div>
    </div>
  </div>
</div>
""")

season_choices = sorted(
    [s for s in ALL_GAMES['_season'].dropna().astype(str).unique().tolist() if s in ('2025', '2026')]
)
if not season_choices:
    season_choices = ['2025', '2026']
default_season = '2026' if '2026' in season_choices else season_choices[-1]
season_col, _ = st.columns([1.2, 5.8])
with season_col:
    selected_season = st.selectbox(
        "Select Season",
        season_choices,
        index=season_choices.index(default_season),
        key="global_season_select",
    )

Games = ALL_GAMES[ALL_GAMES['_season'].astype(str) == str(selected_season)].copy()

# ── Config ────────────────────────────────────────────────────────────────────
DAY_CFG = {
    'wednesday': {'bg': '#002244', 'fg': '#69be28', 'border': 'none', 'label': 'Wednesday'},
    'thursday': {'bg': '#d95f00', 'fg': '#ffffff', 'border': 'none', 'label': 'Thursday'},
    'friday':   {'bg': '#1a8c42', 'fg': '#ffffff', 'border': 'none', 'label': 'Friday'},
    'saturday': {'bg': '#6d28d9', 'fg': '#ffffff', 'border': 'none', 'label': 'Saturday'},
    'sunday':   {'bg': '#60a5fa', 'fg': '#ffffff', 'border': 'none', 'label': 'Sunday'},
    'snf':      {'bg': '#1e3a8a', 'fg': '#ffffff', 'border': 'none', 'label': 'Sunday Night'},
    'monday':   {'bg': '#dc2626', 'fg': '#ffffff', 'border': 'none', 'label': 'Monday'},
}
WEEKS   = list(range(1, 19))
ROW_BG  = '#ffffff'
ALT_BG  = '#f8fafc'
HEAD_BG = '#f4f6fa'

def is_snf_game(row):
    for col in ('Primetime Flag', 'Primetime'):
        raw = str(row.get(col, '') or '').strip().upper()
        if raw and raw not in ('NAN', 'NONE') and 'SNF' in raw:
            return True
    return False

def get_forced_venue(row):
    game_type = str(row.get('Game Type', '') or '').strip().lower()
    if 'super bowl' in game_type:
        return ("SoFi Stadium", 'Inglewood, California')
    dt = pd.to_datetime(row.get('Date', None), errors='coerce')
    if pd.notna(dt) and dt.month == 2 and dt.day == 14:
        return ("SoFi Stadium", 'Inglewood, California')
    return None

def get_day_type(row):
    if is_snf_game(row):
        return 'snf'
    try:
        day = pd.to_datetime(row['Date']).day_name()
        return {'Wednesday': 'wednesday', 'Thursday': 'thursday', 'Friday': 'friday',
                'Saturday': 'saturday', 'Monday': 'monday'}.get(day, 'sunday')
    except Exception:
        return 'sunday'

def build_cells(Games, Team_Info, Other_Locations):
    abb_lookup = dict(zip(Team_Info['Team'], Team_Info['Abb']))
    cells = {}
    for _, g in Games.iterrows():
        try:
            week = int(g['Week'])
        except Exception:
            continue
        if week not in WEEKS:
            continue
        home     = g['Home']
        away     = g['Away']
        game_loc = _clean_text(g.get('Location', ''))
        intl_val = g.get('International', False)
        is_intl  = bool(intl_val) if not isinstance(intl_val, float) else False
        day_type = get_day_type(g)
        home_abb = abb_lookup.get(home, str(home)[:3].upper())
        away_abb = abb_lookup.get(away, str(away)[:3].upper())
        if is_intl:
            cells[(home, week)] = {'text': f'n{away_abb}', 'day_type': day_type}
            cells[(away, week)] = {'text': f'n{home_abb}', 'day_type': day_type}
        else:
            cells[(home, week)] = {'text': away_abb,       'day_type': day_type}
            cells[(away, week)] = {'text': f'@{home_abb}', 'day_type': day_type}
    return cells

def make_legend():
    items_html = ''
    for key, cfg in DAY_CFG.items():
        items_html += f"""
        <div class="legend-item">
          <div class="legend-swatch" style="background:{cfg['bg']};"></div>
          <span class="legend-text">{cfg['label']}</span>
        </div>"""
    items_html += """
    <div class="legend-item">
      <span class="legend-code">ABV</span>
      <span class="legend-text">Home</span>
    </div>
    <div class="legend-item">
      <span class="legend-code">@ABV</span>
      <span class="legend-text">Away</span>
    </div>
    <div class="legend-item">
      <span class="legend-code">nABV</span>
      <span class="legend-text">Intl</span>
    </div>
    <div class="legend-item">
      <span style="font-size:26px; color:#c8d2e0; line-height:1; font-family:Georgia,serif;">&#8212;</span>
      <span class="legend-text">Bye</span>
    </div>"""
    return f'<div class="legend-bar"><div class="legend-title">Legend</div>{items_html}</div>'


def make_division_table(division_label, division_teams, cells, row_offset=0):
    F_COND = "font-family:'Barlow Condensed',sans-serif;"
    F_CELL = "font-family:'Rajdhani',sans-serif;"

    col_tags = "".join('<col style="width:52px;">' for _ in WEEKS)
    html = (
        f'<div style="overflow-x:auto; margin-bottom:4px; background:#ffffff;'
        f'border-radius:6px; border:1px solid #e2e6ef; box-shadow:0 1px 4px rgba(0,0,0,0.05);">'
        f'<table style="border-collapse:collapse; width:100%; table-layout:fixed;">'
        f'<colgroup><col style="width:140px;">{col_tags}</colgroup>'
        f'<thead><tr style="background:{HEAD_BG};">'
        f'<th style="{F_COND} padding:12px 14px 12px 18px; text-align:right;'
        f'color:#9aa5be; font-size:15px; font-weight:800; letter-spacing:3px;'
        f'text-transform:uppercase; background:{HEAD_BG}; position:sticky; left:0; z-index:3;'
        f'border-bottom:1px solid #e2e6ef; white-space:nowrap; vertical-align:middle;">'
        f'{division_label}</th>'
    )
    for w in WEEKS:
        html += (
            f'<th style="{F_COND} padding:12px 0; text-align:center; color:#b0baca;'
            f'font-size:16px; font-weight:700; letter-spacing:0.5px; background:{HEAD_BG};'
            f'border-bottom:1px solid #e2e6ef; white-space:nowrap; vertical-align:middle;">'
            f'Wk{w}</th>'
        )
    html += '</tr></thead><tbody>'

    def clean_color(val, fallback):
        v = str(val).strip() if val is not None else ''
        if not v or v.lower() in ('nan', 'none', ''):
            return fallback
        return v if v.startswith('#') else '#' + v

    total_rows = len(division_teams)
    for i, (_, tr) in enumerate(division_teams.iterrows()):
        team    = tr['Team']
        city    = str(tr.get('City', tr.get('Abb', team))).strip()
        c1      = clean_color(tr.get('Color1'), '#c8102e')
        bye_wk  = tr.get('Bye', None)
        row_bg  = ROW_BG if i % 2 == 0 else ALT_BG
        is_last = (i == total_rows - 1)
        row_border = "border-bottom:none;" if is_last else "border-bottom:1px solid #f0f2f7;"

        try:
            bye_int = int(bye_wk) if bye_wk is not None and str(bye_wk).strip() not in ('', 'nan') else None
        except (ValueError, TypeError):
            bye_int = None

        html += f'<tr style="{row_border}">'
        html += (
            f'<td style="padding:0; background:{row_bg}; position:sticky; left:0; z-index:2;'
            f'border-right:1px solid #e2e6ef;">'
            f'<div style="display:flex; align-items:stretch; height:48px;">'
            f'<div style="flex:1; display:flex; align-items:center; justify-content:flex-end; padding-right:10px;">'
            f'<span style="{F_COND} font-size:18px; font-weight:700; letter-spacing:1.5px;'
            f'text-transform:uppercase; color:#2a3550; white-space:nowrap;">{city}</span>'
            f'</div>'
            f'<div style="width:4px; background:{c1}; flex-shrink:0;"></div>'
            f'</div></td>'
        )

        for w in WEEKS:
            if bye_int == w:
                html += (
                    f'<td style="padding:0; text-align:center; background:{row_bg};">'
                    f'<span style="color:#d0d8e8; font-size:22px; line-height:48px;'
                    f'font-family:Georgia,serif;">&#8212;</span></td>'
                )
            elif (team, w) in cells:
                cell   = cells[(team, w)]
                cfg    = DAY_CFG[cell['day_type']]
                border = 'none'
                raw    = cell['text']
                if raw.startswith('@'):
                    prefix = f'<span style="color:{cfg["fg"]}; opacity:0.6; font-size:14px; {F_COND}">@</span>'
                    abbrev = raw[1:]
                elif raw.startswith('n'):
                    prefix = f'<span style="color:{cfg["fg"]}; opacity:0.6; font-size:14px; {F_COND}">n</span>'
                    abbrev = raw[1:]
                else:
                    prefix = ''
                    abbrev = raw
                html += (
                    f'<td style="padding:3px 2px; text-align:center; background:{row_bg};">'
                    f'<span style="{F_CELL} display:inline-flex; align-items:center; justify-content:center;'
                    f'background:{cfg["bg"]}; color:{cfg["fg"]}; border:{border};'
                    f'padding:6px 8px; border-radius:4px; font-size:18px; font-weight:700;'
                    f'letter-spacing:0.3px; white-space:nowrap; height:36px; gap:1px; line-height:1;">'
                    f'{prefix}{abbrev}</span></td>'
                )
            else:
                html += f'<td style="background:{row_bg};"></td>'

        html += '</tr>'

    html += '</tbody></table></div>'
    return html


tabs = st.tabs(["🌐 League View", "🏈 Team View"])

with tabs[0]:

    sub_tabs2 = st.tabs(["📋 Full Schedule", "🗓️ Weekly Schedule", "🌙 Primetime Schedule", "✈️ Travel", "📊 Analytics"])
    lv_abb_map = dict(zip(Team_Info['Team'], Team_Info['Abb']))
    lv_logo_map = {
        t: (str(l or '').strip().strip('_').strip('`') or TBD_LOGO)
        for t, l in zip(Team_Info['Team'], Team_Info['Logo'])
    }
    lv_stad_map = dict(TEAM_STAD_MAP)
    lv_city_map = dict(TEAM_CITY_MAP)
    lv_clr_map = {}
    for _, row in Team_Info.iterrows():
        t = row['Team']
        c = str(row.get('Color1', '') or '').strip().strip('`').strip("'\"")
        if not c or c.lower() in ('nan', 'none'):
            c = '#c8102e'
        lv_clr_map[t] = c if c.startswith('#') else f'#{c}'
    lv_intl_locs = set(NEUTRAL_LOCATION_SET)
    lv_intl_stad = {k: _clean_text(v.get('stad', '')) for k, v in INTL_DATA.items()}

    with sub_tabs2[0]:
        try:
            cells        = build_cells(Games, Team_Info, Other_Locations)
            sorted_teams = Team_Info.sort_values(['Conference', 'Division', 'Team'])

            st.html(make_legend())

            row_counter = 0
            last_conf   = None

            for (conf, div), group in sorted_teams.groupby(['Conference', 'Division'], sort=False):
                if conf != last_conf:
                    last_conf = conf
                    header_class = "conf-header first" if row_counter == 0 else "conf-header"
                    st.html(
                        f'<div class="{header_class}">'
                        f'<span class="conf-label">{conf}</span>'
                        f'<div class="conf-header-line"></div></div>'
                    )

                st.html(make_division_table(div, group, cells, row_counter))
                row_counter += len(group)

        except Exception as e:
            st.error(f"Error building schedule: {e}")
            st.exception(e)

    with sub_tabs2[1]:
        wk_col, _ = st.columns([1.2, 4.8])
        with wk_col:
            selected_week = st.selectbox(
                "Select Week",
                list(range(1, 23)),
                index=0,
                format_func=lambda w: f"Week {w}",
                key="lv_week_select",
            )

        week_games = Games[
            pd.to_numeric(Games['Week'], errors='coerce') == selected_week
        ].copy()

        if len(week_games) == 0:
            st.info(f"No games currently listed for Week {selected_week}.")
        else:
            week_games = week_games.sort_values('Date').reset_index(drop=True)
            rows_html = f"""
<tr style="background:#eef2f8;border-top:1px solid #dde2ed;border-bottom:1px solid #dde2ed;">
  <td style="width:5px;padding:0;background:#1a2030;"></td>
  <td colspan="4" style="padding:8px 14px;font-family:'Barlow Condensed',sans-serif;
       font-size:12px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#64748b;">
    Week {selected_week}
  </td>
</tr>"""
            for _, g in week_games.iterrows():
                home = g['Home']
                away = g['Away']
                home_abb = lv_abb_map.get(home, str(home)[:3].upper())
                away_abb = lv_abb_map.get(away, str(away)[:3].upper())
                home_logo = lv_logo_map.get(home, TBD_LOGO)
                away_logo = lv_logo_map.get(away, TBD_LOGO)
                home_clr = lv_clr_map.get(home, '#374151')
                away_clr = lv_clr_map.get(away, '#374151')
                accent_clr = home_clr

                dk = get_day_type(g)
                day_bg = DAY_CFG.get(dk, DAY_CFG['sunday'])['bg']
                day_fg = DAY_CFG.get(dk, DAY_CFG['sunday'])['fg']

                loc = str(g.get('Location', '') or '').strip()
                intl_val = g.get('International', False)
                is_intl = bool(intl_val) if not isinstance(intl_val, float) else False
                venue_override = get_forced_venue(g)
                if venue_override:
                    stad, loc_disp = venue_override
                    is_intl = False
                elif is_intl:
                    stad = lv_intl_stad.get(loc, '')
                    loc_disp = loc
                else:
                    stad = lv_stad_map.get(home, '')
                    loc_disp = lv_city_map.get(home, loc)
                if not loc_disp:
                    loc_disp = loc if loc else 'TBD'

                time_et = str(g.get('Time (ET)', '') or '').strip()
                if time_et.lower() in ('', 'nan'):
                    time_et = 'TBD'
                tv = str(g.get('TV Network', '') or '').strip()
                if tv.lower() in ('', 'nan'):
                    tv = ''

                game_type = str(g.get('Game Type', '') or '').strip()
                if game_type.lower() in ('', 'nan', 'none'):
                    game_type = 'Regular Season'

                try:
                    dt = pd.to_datetime(g['Date'])
                    dow = dt.strftime('%a').upper()
                    date_d = dt.strftime('%b') + ' ' + str(dt.day)
                except Exception:
                    dow = '—'
                    date_d = str(g.get('Date', ''))

                intl_tag = (
                    '<span style="background:#7c3aed;color:#fff;font-family:\'Barlow Condensed\','
                    'sans-serif;font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;'
                    'padding:2px 6px;border-radius:3px;margin-left:8px;vertical-align:middle;">INTL</span>'
                ) if is_intl else ''
                tv_badge = (
                    f'<span style="background:#f1f5f9;color:#475569;font-family:\'Barlow Condensed\','
                    f'sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;padding:3px 10px;'
                    f'border-radius:3px;border:1px solid #dde2ed;white-space:nowrap;">{tv}</span>'
                ) if tv else ''
                gtype_badge = (
                    f'<span style="display:inline-block;background:#eef2f8;color:#475569;'
                    f'font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:700;'
                    f'letter-spacing:1.6px;text-transform:uppercase;padding:2px 8px;border-radius:3px;'
                    f'border:1px solid #dde2ed;margin-top:3px;">{game_type}</span>'
                )
                location_html = (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:700;color:#2a3550;line-height:1.2;">{stad}</div>'
                    f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{loc_disp}</div>'
                ) if stad else (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:600;color:#4a5a78;">{loc_disp}</div>'
                )

                rows_html += f"""
<tr style="background:#ffffff;border-bottom:1px solid #f0f2f7;transition:background 0.15s;">
  <td style="width:5px;padding:0;background:{accent_clr};"></td>
  <td style="padding:12px 16px;vertical-align:middle;white-space:nowrap;width:130px;">
    <div style="display:inline-block;padding:2px 8px;border-radius:3px;margin-bottom:4px;
         background:{day_bg};color:{day_fg};font-family:'Barlow Condensed',sans-serif;
         font-size:12px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;">{dow}</div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;
         color:#1a2030;letter-spacing:0.3px;line-height:1.2;">{date_d}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{time_et} ET</div>
  </td>
  <td style="padding:12px 16px;vertical-align:middle;min-width:320px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="width:42px;height:42px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <img src="{away_logo}" style="max-width:42px;max-height:42px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
      <div style="font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:700;color:{away_clr};letter-spacing:1px;">
        {away_abb}
      </div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:800;color:#64748b;letter-spacing:1.8px;">
        @
      </div>
      <div style="font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:700;color:{home_clr};letter-spacing:1px;">
        {home_abb}
      </div>
      <div style="width:42px;height:42px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <img src="{home_logo}" style="max-width:42px;max-height:42px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
    </div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;color:#1a2030;line-height:1.2;">
      {away} @ {home}{intl_tag}
    </div>
    {gtype_badge}
  </td>
  <td style="padding:12px 20px;vertical-align:middle;min-width:220px;">
    {location_html}
  </td>
  <td style="padding:12px 16px;vertical-align:middle;text-align:right;white-space:nowrap;width:110px;">
    {tv_badge}
  </td>
</tr>"""

            st.html(f"""
<div style="margin-top:18px;overflow-x:auto;border-radius:10px;
     border:1px solid #e2e6ef;box-shadow:0 2px 12px rgba(0,0,0,0.08);background:#fff;">
  <table style="border-collapse:collapse;width:100%;min-width:900px;">
    <thead>
      <tr style="background:#f4f6fa;border-bottom:2px solid #e2e6ef;">
        <th style="width:5px;background:#f4f6fa;"></th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">DATE &amp; TIME</th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">MATCHUP</th>
        <th style="padding:10px 20px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">LOCATION / STADIUM</th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:right;">TV</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>""")

    with sub_tabs2[2]:
        pt_col, _ = st.columns([2.2, 3.8])
        with pt_col:
            primetime_choice = st.selectbox(
                "Select Primetime Window",
                ["Thursday Games", "Friday Games", "SNF Games", "Monday Games"],
                key="lv_primetime_select",
            )

        primetime_key = {
            "Thursday Games": "thursday",
            "Friday Games": "friday",
            "SNF Games": "snf",
            "Monday Games": "monday",
        }[primetime_choice]

        primetime_games = Games[Games.apply(lambda r: get_day_type(r) == primetime_key, axis=1)].copy()

        if len(primetime_games) == 0:
            st.info(f"No games currently listed for {primetime_choice}.")
        else:
            primetime_games = primetime_games.sort_values(['Week', 'Date']).reset_index(drop=True)
            rows_html = ''
            current_week = None

            for _, g in primetime_games.iterrows():
                wk_raw = g.get('Week', '')
                try:
                    wk_val = int(wk_raw)
                except Exception:
                    wk_val = 'TBA'

                if wk_val != current_week:
                    current_week = wk_val
                    rows_html += f"""
<tr style="background:#eef2f8;border-top:1px solid #dde2ed;border-bottom:1px solid #dde2ed;">
  <td style="width:5px;padding:0;background:#1a2030;"></td>
  <td colspan="4" style="padding:8px 14px;font-family:'Barlow Condensed',sans-serif;
       font-size:12px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#64748b;">
    Week {wk_val}
  </td>
</tr>"""

                home = g['Home']
                away = g['Away']
                home_abb = lv_abb_map.get(home, str(home)[:3].upper())
                away_abb = lv_abb_map.get(away, str(away)[:3].upper())
                home_logo = lv_logo_map.get(home, TBD_LOGO)
                away_logo = lv_logo_map.get(away, TBD_LOGO)
                home_clr = lv_clr_map.get(home, '#374151')
                away_clr = lv_clr_map.get(away, '#374151')
                accent_clr = home_clr

                dk = get_day_type(g)
                day_bg = DAY_CFG.get(dk, DAY_CFG['sunday'])['bg']
                day_fg = DAY_CFG.get(dk, DAY_CFG['sunday'])['fg']

                loc = str(g.get('Location', '') or '').strip()
                intl_val = g.get('International', False)
                is_intl = bool(intl_val) if not isinstance(intl_val, float) else False
                venue_override = get_forced_venue(g)
                if venue_override:
                    stad, loc_disp = venue_override
                    is_intl = False
                elif is_intl:
                    stad = lv_intl_stad.get(loc, '')
                    loc_disp = loc
                else:
                    stad = lv_stad_map.get(home, '')
                    loc_disp = lv_city_map.get(home, loc)
                if not loc_disp:
                    loc_disp = loc if loc else 'TBD'

                time_et = str(g.get('Time (ET)', '') or '').strip()
                if time_et.lower() in ('', 'nan'):
                    time_et = 'TBD'
                tv = str(g.get('TV Network', '') or '').strip()
                if tv.lower() in ('', 'nan'):
                    tv = ''

                game_type = str(g.get('Game Type', '') or '').strip()
                if game_type.lower() in ('', 'nan', 'none'):
                    game_type = 'Regular Season'

                try:
                    dt = pd.to_datetime(g['Date'])
                    dow = dt.strftime('%a').upper()
                    date_d = dt.strftime('%b') + ' ' + str(dt.day)
                except Exception:
                    dow = '—'
                    date_d = str(g.get('Date', ''))

                intl_tag = (
                    '<span style="background:#7c3aed;color:#fff;font-family:\'Barlow Condensed\','
                    'sans-serif;font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;'
                    'padding:2px 6px;border-radius:3px;margin-left:8px;vertical-align:middle;">INTL</span>'
                ) if is_intl else ''
                tv_badge = (
                    f'<span style="background:#f1f5f9;color:#475569;font-family:\'Barlow Condensed\','
                    f'sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;padding:3px 10px;'
                    f'border-radius:3px;border:1px solid #dde2ed;white-space:nowrap;">{tv}</span>'
                ) if tv else ''
                gtype_badge = (
                    f'<span style="display:inline-block;background:#eef2f8;color:#475569;'
                    f'font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:700;'
                    f'letter-spacing:1.6px;text-transform:uppercase;padding:2px 8px;border-radius:3px;'
                    f'border:1px solid #dde2ed;margin-top:3px;">{game_type}</span>'
                )
                location_html = (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:700;color:#2a3550;line-height:1.2;">{stad}</div>'
                    f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{loc_disp}</div>'
                ) if stad else (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:600;color:#4a5a78;">{loc_disp}</div>'
                )

                rows_html += f"""
<tr style="background:#ffffff;border-bottom:1px solid #f0f2f7;transition:background 0.15s;">
  <td style="width:5px;padding:0;background:{accent_clr};"></td>
  <td style="padding:12px 16px;vertical-align:middle;white-space:nowrap;width:130px;">
    <div style="display:inline-block;padding:2px 8px;border-radius:3px;margin-bottom:4px;
         background:{day_bg};color:{day_fg};font-family:'Barlow Condensed',sans-serif;
         font-size:12px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;">{dow}</div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;
         color:#1a2030;letter-spacing:0.3px;line-height:1.2;">{date_d}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{time_et} ET</div>
  </td>
  <td style="padding:12px 16px;vertical-align:middle;min-width:320px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <div style="width:42px;height:42px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <img src="{away_logo}" style="max-width:42px;max-height:42px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
      <div style="font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:700;color:{away_clr};letter-spacing:1px;">
        {away_abb}
      </div>
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:800;color:#64748b;letter-spacing:1.8px;">
        @
      </div>
      <div style="font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:700;color:{home_clr};letter-spacing:1px;">
        {home_abb}
      </div>
      <div style="width:42px;height:42px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
        <img src="{home_logo}" style="max-width:42px;max-height:42px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
    </div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;color:#1a2030;line-height:1.2;">
      {away} @ {home}{intl_tag}
    </div>
    {gtype_badge}
  </td>
  <td style="padding:12px 20px;vertical-align:middle;min-width:220px;">
    {location_html}
  </td>
  <td style="padding:12px 16px;vertical-align:middle;text-align:right;white-space:nowrap;width:110px;">
    {tv_badge}
  </td>
</tr>"""

            st.html(f"""
<div style="margin-top:18px;overflow-x:auto;border-radius:10px;
     border:1px solid #e2e6ef;box-shadow:0 2px 12px rgba(0,0,0,0.08);background:#fff;">
  <table style="border-collapse:collapse;width:100%;min-width:900px;">
    <thead>
      <tr style="background:#f4f6fa;border-bottom:2px solid #e2e6ef;">
        <th style="width:5px;background:#f4f6fa;"></th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">DATE &amp; TIME</th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">MATCHUP</th>
        <th style="padding:10px 20px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">LOCATION / STADIUM</th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:right;">TV</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>""")

    with sub_tabs2[3]:
        st.write("League travel view coming soon")

    with sub_tabs2[4]:
        st.write("Analytics goes here")

with tabs[1]:

    def tv_strip_clr(val, fallback='#c8102e'):
        v = str(val or '').strip().strip('`').strip("'\"")
        if not v or v.lower() in ('nan', 'none', ''):
            return fallback
        return v if v.startswith('#') else f'#{v}'

    def tv_lum(h):
        try:
            h = h.lstrip('#')
            r = int(h[0:2], 16) / 255
            g = int(h[2:4], 16) / 255
            b = int(h[4:6], 16) / 255
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        except Exception:
            return 0.3

    def tv_fg(h):
        return '#ffffff' if tv_lum(h) < 0.45 else '#111827'

    def tv_clean_url(val):
        return str(val or '').strip().strip('_').strip('`')

    def tv_haversine(lat1, lon1, lat2, lon2):
        R = 3958.8
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    def tv_valid_coord(val):
        if val is None:
            return False
        try:
            f = float(val)
            return not math.isnan(f)
        except Exception:
            return False

    SCHED_DAY_CFG = {
        'wednesday': ('#002244', '#69be28'),
        'thursday': ('#d95f00', '#ffffff'),
        'friday':   ('#1a8c42', '#ffffff'),
        'saturday': ('#6d28d9', '#ffffff'),
        'sunday':   ('#60a5fa', '#ffffff'),
        'snf':      ('#1e3a8a', '#ffffff'),
        'monday':   ('#dc2626', '#ffffff'),
    }

    def tv_day_key(g):
        if is_snf_game(g):
            return 'snf'
        try:
            day = pd.to_datetime(g['Date']).strftime('%A')
            return {'Wednesday': 'wednesday', 'Thursday': 'thursday', 'Friday': 'friday',
                    'Saturday': 'saturday', 'Monday': 'monday'}.get(day, 'sunday')
        except Exception:
            return 'sunday'

    # ── Build lookup tables ───────────────────────────────────────────────────
    abb_map  = dict(zip(Team_Info['Team'], Team_Info['Abb']))
    logo_map = {t: (tv_clean_url(l) or TBD_LOGO) for t, l in zip(Team_Info['Team'], Team_Info['Logo'])}  # noqa: E741
    wm_map   = {t: tv_clean_url(w) for t, w in zip(Team_Info['Team'], Team_Info['Wordmark'])}
    clr1_map = {t: tv_strip_clr(c) for t, c in zip(Team_Info['Team'], Team_Info['Color1'])}
    stad_map = dict(TEAM_STAD_MAP)
    city_map = dict(TEAM_CITY_MAP)
    lat_map  = dict(TEAM_LAT_MAP)
    lon_map  = dict(TEAM_LON_MAP)
    tz_map   = dict(TEAM_TZ_MAP)
    intl_data = dict(INTL_DATA)

    # ── Team selector ─────────────────────────────────────────────────────────
    team_list = Team_Info.sort_values('Team')['Team'].tolist()

    pick_col, _ = st.columns([2, 5])
    with pick_col:
        selected_team = st.selectbox(
            "Select Team",
            team_list,
            key="tv_team_select",
        )

    tr   = Team_Info[Team_Info['Team'] == selected_team].iloc[0]
    c1   = tv_strip_clr(tr['Color1'])
    c2   = tv_strip_clr(tr['Color2'], '#1a2030')
    logo = tv_clean_url(tr['Logo']) or TBD_LOGO
    wm   = tv_clean_url(tr['Wordmark'])
    abb  = str(tr.get('Abb', '')).strip()
    city = str(tr.get('City', '')).strip()
    nick = str(tr.get('Nickname', '')).strip()
    team_name = str(tr.get('Team', selected_team)).strip()
    conf = str(tr.get('Conference', '')).strip()
    div  = str(tr.get('Division', '')).strip()
    fg1  = tv_fg(c1)
    fg2  = tv_fg(c2)

    bye_wk = tr.get('Bye', None)
    try:
        bye_int = int(bye_wk) if bye_wk and str(bye_wk).strip() not in ('', 'nan') else None
    except Exception:
        bye_int = None

    ou    = tr.get('Vegas O/U', '—')
    wins  = tr.get('2025 Wins', '—')
    tot   = tr.get('Total', '—')
    tot_r = tr.get('Total Rank', '—')
    off   = tr.get('Offense', '—')
    off_r = tr.get('Offensive Rank', '—')
    deff  = tr.get('Defense', '—')
    def_r = tr.get('Defensive Rank', '—')
    st_dvoa = tr.get('Special Teams', '—')
    st_r    = tr.get('Special Teams Rank', '—')

    wm_filter = 'brightness(0) invert(1)' if tv_lum(c1) < 0.35 else ''

    divider = f'<div style="width:1px;height:38px;background:{fg1};opacity:0.2;flex-shrink:0;"></div>'

    stat_block = lambda label, val, sub='': f'''
      <div style="text-align:center;min-width:60px;">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;
            letter-spacing:4px;text-transform:uppercase;color:{fg1};opacity:0.55;margin-bottom:1px;">{label}</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:34px;color:{fg1};line-height:1;">{val}
          {"" if not sub else f'<span style="font-size:17px;opacity:0.6;">{sub}</span>'}
        </div>
      </div>'''  # noqa: E731

    bye_block = f'''
      {divider}
      <div style="text-align:center;min-width:60px;">
        <div style="font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;
             letter-spacing:4px;text-transform:uppercase;color:{fg1};opacity:0.55;margin-bottom:1px;">BYE</div>
        <div style="font-family:\'Bebas Neue\',sans-serif;font-size:34px;color:{fg1};line-height:1;">WK {bye_int}</div>
      </div>''' if bye_int else ''

    # ── Team Banner ───────────────────────────────────────────────────────────
    st.html(f"""
<div style="background:linear-gradient(130deg, {c1} 0%, {c2} 100%);
     border-radius:12px; padding:26px 36px; margin:20px 0 6px;
     display:flex; align-items:center; gap:28px;
     box-shadow: 0 8px 40px rgba(0,0,0,0.22);">
  <img src="{logo}"
       style="height:100px;width:100px;object-fit:contain;flex-shrink:0;
              filter:drop-shadow(0 3px 18px rgba(0,0,0,0.45));"
       onerror="this.onerror=null;this.src='{TBD_LOGO}';">
  <div style="flex:1;min-width:0;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:800;
         letter-spacing:5px;text-transform:uppercase;color:{fg1};opacity:0.55;margin-bottom:2px;">
      {conf} &nbsp;·&nbsp; {div}
    </div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:62px;letter-spacing:3px;
         color:{fg1};line-height:0.95;margin-bottom:14px;">
      {team_name.upper()}
    </div>
    <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center;">
      {stat_block('2026 O/U', ou)}
      {divider}
      {stat_block('2025 Record', wins)}
      {divider}
      {stat_block('2025 DVOA', tot, f'#{tot_r}')}
      {divider}
      {stat_block('2025 O. DVOA', off, f'#{off_r}')}
      {divider}
      {stat_block('2025 D. DVOA', deff, f'#{def_r}')}
      {divider}
      {stat_block('2025 S.T. DVOA', st_dvoa, f'#{st_r}')}
      {bye_block}
    </div>
  </div>
  <img src="{wm}"
       style="height:52px;max-width:200px;object-fit:contain;opacity:0.9;flex-shrink:0;
              filter:{wm_filter};"
       onerror="this.style.display='none'">
</div>""")

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    sub_tabs = st.tabs(["📅  Schedule", "📊  Analytics", "✈️  Travel"])

    # ═══════════════════ SCHEDULE TAB ═══════════════════════════════════════
    with sub_tabs[0]:
        team_games = Games[
            (Games['Home'] == selected_team) | (Games['Away'] == selected_team)
        ].copy().sort_values('Week').reset_index(drop=True)

        team_week_num = pd.to_numeric(team_games['Week'], errors='coerce')
        tba_week_mode = str(selected_season) == '2026'
        if tba_week_mode:
            team_games['_game_type_norm'] = team_games.get('Game Type', '').astype(str).str.strip()
            team_games.loc[
                team_games['_game_type_norm'].str.lower().isin(['', 'nan', 'none']),
                '_game_type_norm'
            ] = 'Regular Season'
            team_games['_is_non_reg'] = (
                team_games['_game_type_norm'].str.lower() != 'regular season'
            ).astype(int)
            playoff_order = {
                'wildcard weekend': 1,
                'divisional round': 2,
                'conference championship': 3,
                'super bowl lxi': 4,
            }
            team_games['_post_order'] = team_games['_game_type_norm'].str.lower().map(playoff_order).fillna(99)
            team_games['_ha_sort'] = team_games.apply(
                lambda r: 0 if r['Home'] == selected_team else 1, axis=1
            )
            team_games['_opp_sort'] = team_games.apply(
                lambda r: str(r['Away'] if r['Home'] == selected_team else r['Home']), axis=1
            )
            team_games = team_games.sort_values(
                ['_is_non_reg', '_post_order', '_game_type_norm', '_ha_sort', '_opp_sort']
            ).reset_index(drop=True)
            wk_iter = [None]
        else:
            max_wk_val = pd.to_numeric(Games['Week'], errors='coerce').max()
            max_wk = max(int(max_wk_val), 18) if pd.notna(max_wk_val) else 18
            wk_iter = range(1, max_wk + 1)
        rows_html = ''
        current_game_type = None

        for wk in wk_iter:
            wk_rows = team_games if tba_week_mode else team_games[team_week_num == wk]

            if len(wk_rows) == 0:
                if (not tba_week_mode) and bye_int is not None and wk == bye_int:
                    rows_html += f"""
<tr style="background:#f8fafc;border-bottom:1px solid #edf0f7;">
  <td style="width:5px;background:#e2e6ef;"></td>
  <td style="padding:10px 8px 10px 12px;text-align:center;vertical-align:middle;">
    <div style="width:34px;height:34px;border-radius:50%;background:#e2e6ef;color:#b0baca;
         display:inline-flex;align-items:center;justify-content:center;
         font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:800;">{wk}</div>
  </td>
  <td colspan="5" style="padding:12px 16px;vertical-align:middle;">
    <span style="font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:800;
         letter-spacing:5px;text-transform:uppercase;color:#c8d2e0;">— BYE WEEK —</span>
  </td>
</tr>"""
                continue

            for _, g in wk_rows.iterrows():
                game_type = str(g.get('Game Type', '') or '').strip()
                if game_type.lower() in ('', 'nan', 'none'):
                    game_type = 'Regular Season'
                is_non_reg = game_type.lower() != 'regular season'
                if (
                    (not tba_week_mode and game_type != current_game_type)
                    or (tba_week_mode and is_non_reg and game_type != current_game_type)
                ):
                    current_game_type = game_type
                    rows_html += f"""
<tr style="background:#eef2f8;border-top:1px solid #dde2ed;border-bottom:1px solid #dde2ed;">
  <td style="width:5px;padding:0;background:{c1};"></td>
  <td colspan="6" style="padding:8px 14px;font-family:'Barlow Condensed',sans-serif;
       font-size:12px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#64748b;">
    {game_type}
  </td>
</tr>"""

                is_home  = g['Home'] == selected_team
                opponent = g['Away'] if is_home else g['Home']

                intl_val = g.get('International', False)
                is_intl  = bool(intl_val) if not isinstance(intl_val, float) else False

                game_loc = str(g.get('Location', '') or '').strip()
                time_et  = str(g.get('Time (ET)', '') or '').strip()
                if time_et.lower() in ('nan', ''):
                    time_et = 'TBD'
                tv = str(g.get('TV Network', '') or '').strip()
                if tv.lower() in ('nan', ''):
                    tv = ''

                dk = tv_day_key(g)
                day_bg, day_fg_col = SCHED_DAY_CFG[dk]

                try:
                    dt     = pd.to_datetime(g['Date'])
                    dow    = dt.strftime('%a').upper()
                    date_d = dt.strftime('%b') + ' ' + str(dt.day)
                except Exception:
                    dow    = '—'
                    date_d = str(g.get('Date', ''))

                # Location / stadium resolution
                venue_override = get_forced_venue(g)
                is_super_bowl_neutral = venue_override is not None
                if venue_override:
                    stad, loc_disp = venue_override
                    is_intl = False
                elif is_intl:
                    idata    = intl_data.get(game_loc, {})
                    stad     = idata.get('stad', '')
                    loc_disp = game_loc
                elif is_home:
                    stad     = stad_map.get(selected_team, '')
                    loc_disp = city_map.get(selected_team, '')
                else:
                    stad     = stad_map.get(opponent, '')
                    loc_disp = city_map.get(opponent, game_loc)

                if not loc_disp:
                    loc_disp = game_loc

                # H/A/N badge
                if is_intl or is_super_bowl_neutral:
                    ha_bg = '#7c3aed'
                    ha_fg_col = '#fff' 
                    ha_lbl = 'NEUTRAL'
                elif is_home:
                    ha_bg = c1
                    ha_fg_col = fg1 
                    ha_lbl = 'HOME'
                else:
                    ha_bg = '#475569' 
                    ha_fg_col = '#fff'
                    ha_lbl = 'AWAY'

                opp_logo = logo_map.get(opponent, TBD_LOGO)
                opp_clr  = clr1_map.get(opponent, '#888888')
                opp_abb  = abb_map.get(opponent, '')

                intl_tag = (
                    '<span style="background:#7c3aed;color:#fff;font-family:\'Barlow Condensed\','
                    'sans-serif;font-size:10px;font-weight:800;letter-spacing:2px;text-transform:'
                    'uppercase;padding:2px 6px;border-radius:3px;margin-left:8px;vertical-align:middle;">INTL</span>'
                ) if is_intl else ''

                tv_badge = (
                    f'<span style="background:#f1f5f9;color:#475569;font-family:\'Barlow Condensed\','
                    f'sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;padding:3px 10px;'
                    f'border-radius:3px;border:1px solid #dde2ed;white-space:nowrap;">{tv}</span>'
                ) if tv else ''

                location_html = (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:700;color:#2a3550;line-height:1.2;">{stad}</div>'
                    f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{loc_disp}</div>'
                ) if stad else (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:600;color:#4a5a78;">{loc_disp}</div>'
                )
                wk_num = pd.to_numeric(g.get('Week'), errors='coerce')
                wk_badge = str(int(wk_num)) if pd.notna(wk_num) else 'TBA'

                rows_html += f"""
<tr style="background:#ffffff;border-bottom:1px solid #f0f2f7;transition:background 0.15s;">
  <td style="width:5px;padding:0;background:{opp_clr};"></td>
  <td style="padding:12px 8px 12px 12px;text-align:center;vertical-align:middle;width:54px;">
    <div style="width:36px;height:36px;border-radius:50%;background:{c1};color:{fg1};
         display:inline-flex;align-items:center;justify-content:center;
         font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:800;">{wk_badge}</div>
  </td>
  <td style="padding:12px 16px;vertical-align:middle;white-space:nowrap;width:130px;">
    <div style="display:inline-block;padding:2px 8px;border-radius:3px;margin-bottom:4px;
         background:{day_bg};color:{day_fg_col};font-family:'Barlow Condensed',sans-serif;
         font-size:12px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;">{dow}</div>
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;
         color:#1a2030;letter-spacing:0.3px;line-height:1.2;">{date_d}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{time_et} ET</div>
  </td>
  <td style="padding:12px 8px;vertical-align:middle;text-align:center;width:84px;">
    <span style="display:inline-block;padding:5px 10px;border-radius:5px;
         background:{ha_bg};color:{ha_fg_col};font-family:'Barlow Condensed',sans-serif;
         font-size:12px;font-weight:800;letter-spacing:2px;text-transform:uppercase;
         white-space:nowrap;">{ha_lbl}</span>
  </td>
  <td style="padding:12px 20px 12px 8px;vertical-align:middle;min-width:230px;">
    <div style="display:flex;align-items:center;gap:14px;">
      <div style="width:50px;height:50px;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
        <img src="{opp_logo}" style="max-width:50px;max-height:50px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
      <div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:20px;font-weight:700;
             color:#1a2030;letter-spacing:0.3px;line-height:1.2;">{opponent}{intl_tag}</div>
        <div style="font-family:'Rajdhani',sans-serif;font-size:14px;font-weight:600;
             color:{opp_clr};letter-spacing:1.5px;">{opp_abb}</div>
      </div>
    </div>
  </td>
  <td style="padding:12px 20px;vertical-align:middle;min-width:200px;">
    {location_html}
  </td>
  <td style="padding:12px 16px 12px 0;vertical-align:middle;text-align:right;
       white-space:nowrap;width:110px;">
    {tv_badge}
  </td>
</tr>"""

        st.html(f"""
<div style="margin-top:18px;overflow-x:auto;border-radius:10px;
     border:1px solid #e2e6ef;box-shadow:0 2px 12px rgba(0,0,0,0.08);background:#fff;">
  <table style="border-collapse:collapse;width:100%;min-width:780px;">
    <thead>
      <tr style="background:#f4f6fa;border-bottom:2px solid #e2e6ef;">
        <th style="width:5px;background:#f4f6fa;"></th>
        <th style="padding:10px 8px 10px 12px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:center;">WK</th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">DATE &amp; TIME</th>
        <th style="padding:10px 8px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:center;"></th>
        <th style="padding:10px 8px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">OPPONENT</th>
        <th style="padding:10px 20px;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:left;">LOCATION / STADIUM</th>
        <th style="padding:10px 16px 10px 0;font-family:'Barlow Condensed',sans-serif;
             font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
             color:#b0baca;text-align:right;">TV</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
</div>""")

    # ═══════════════════ ANALYTICS TAB ══════════════════════════════════════
    with sub_tabs[1]:
        st.html(f"""
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
     min-height:52vh;padding:60px 20px;text-align:center;">
  <div style="font-size:78px;margin-bottom:22px;animation:pulse 3s ease-in-out infinite;">📊</div>
  <div style="font-family:'Barlow Condensed',sans-serif;font-size:13px;font-weight:800;
       letter-spacing:6px;text-transform:uppercase;color:{c1};margin-bottom:10px;">Coming Soon</div>
  <div style="font-family:'Bebas Neue',sans-serif;font-size:92px;letter-spacing:5px;
       color:#1a2030;line-height:1;margin-bottom:14px;">ANALYTICS</div>
  <div style="font-family:'Barlow',sans-serif;font-size:20px;font-weight:400;
       color:#9aa5be;max-width:380px;line-height:1.8;">
    Advanced metrics, performance trends, and deep team analytics are on the way.</div>
</div>""")

    # ═══════════════════ TRAVEL TAB ══════════════════════════════════════════
    with sub_tabs[2]:
        team_games_all = Games[
            (Games['Home'] == selected_team) | (Games['Away'] == selected_team)
        ].copy()
        team_games_all['_week_num'] = pd.to_numeric(team_games_all['Week'], errors='coerce')
        team_games_all['_date_num'] = pd.to_datetime(team_games_all['Date'], errors='coerce')
        team_games_all = team_games_all.sort_values(['_week_num', '_date_num']).reset_index(drop=True)

        home_base = {
            'name': selected_team,
            'city': city_map.get(selected_team, ''),
            'stadium': stad_map.get(selected_team, ''),
            'lat': lat_map.get(selected_team),
            'lon': lon_map.get(selected_team),
            'tz': tz_map.get(selected_team, ''),
        }

        tz_offsets = {
            'PT': -8, 'PST': -8, 'PDT': -7, 'MT': -7, 'MST': -7, 'MDT': -6,
            'CT': -6, 'CST': -6, 'CDT': -5, 'ET': -5, 'EST': -5, 'EDT': -4,
            'GMT': 0, 'BST': 1, 'CET': 1,
        }

        def tz_offset(tz_raw):
            t = str(tz_raw or '').upper()
            for k, v in tz_offsets.items():
                if k in t:
                    return v
            return None

        def place_key(p):
            if tv_valid_coord(p.get('lat')) and tv_valid_coord(p.get('lon')):
                return f"{round(float(p['lat']), 2)}|{round(float(p['lon']), 2)}"
            return f"{p.get('city', '')}|{p.get('stadium', '')}"

        def resolve_stop(g):
            is_home = g['Home'] == selected_team
            opponent = g['Away'] if is_home else g['Home']
            game_loc = str(g.get('Location', '') or '').strip()
            intl_val = g.get('International', False)
            is_intl = bool(intl_val) if not isinstance(intl_val, float) else False
            override = get_forced_venue(g)

            if override:
                return {
                    'opponent': opponent, 'is_intl': False, 'travel_required': True,
                    'city': override[1], 'stadium': override[0], 'lat': lat_map.get('San Francisco 49ers'),
                    'lon': lon_map.get('San Francisco 49ers'), 'tz': 'PT',
                }
            if is_intl:
                idata = intl_data.get(game_loc, {})
                return {
                    'opponent': opponent, 'is_intl': True, 'travel_required': True,
                    'city': game_loc, 'stadium': idata.get('stad', ''),
                    'lat': idata.get('lat'), 'lon': idata.get('lon'), 'tz': idata.get('tz', ''),
                }
            if is_home:
                return {
                    'opponent': opponent, 'is_intl': False, 'travel_required': False,
                    'city': city_map.get(selected_team, ''), 'stadium': stad_map.get(selected_team, ''),
                    'lat': lat_map.get(selected_team), 'lon': lon_map.get(selected_team),
                    'tz': tz_map.get(selected_team, ''),
                }
            return {
                'opponent': opponent, 'is_intl': False, 'travel_required': True,
                'city': city_map.get(opponent, game_loc), 'stadium': stad_map.get(opponent, ''),
                'lat': lat_map.get(opponent), 'lon': lon_map.get(opponent), 'tz': tz_map.get(opponent, ''),
            }

        def should_stay(cur_stop, next_stop):
            if not (cur_stop['travel_required'] and next_stop['travel_required']):
                return False
            if selected_team == 'Jacksonville Jaguars' and cur_stop['is_intl'] and next_stop['is_intl']:
                cur_city = str(cur_stop.get('city', '')).lower()
                nxt_city = str(next_stop.get('city', '')).lower()
                return ('london' in cur_city) and ('london' in nxt_city)
            return False

        legs = []
        current = dict(home_base)

        def add_leg(src, dst, kind, note):
            if place_key(src) == place_key(dst):
                return
            miles = None
            if tv_valid_coord(src.get('lat')) and tv_valid_coord(src.get('lon')) and tv_valid_coord(dst.get('lat')) and tv_valid_coord(dst.get('lon')):
                miles = tv_haversine(float(src['lat']), float(src['lon']), float(dst['lat']), float(dst['lon']))
            legs.append({
                'from': src.get('city') or src.get('name') or 'Unknown',
                'to': dst.get('city') or dst.get('name') or 'Unknown',
                'miles': miles, 'kind': kind, 'note': note,
                'src_lat': src.get('lat'), 'src_lon': src.get('lon'),
                'dst_lat': dst.get('lat'), 'dst_lon': dst.get('lon'),
            })

        seq = []
        for _, g in team_games_all.iterrows():
            wk_num = pd.to_numeric(g.get('Week'), errors='coerce')
            wk_lbl = f"Wk {int(wk_num)}" if pd.notna(wk_num) else 'Wk TBA'
            seq.append({'week_label': wk_lbl, 'stop': resolve_stop(g)})

        for i, game in enumerate(seq):
            stop = game['stop']
            note_base = f"{game['week_label']} vs {stop['opponent']}"
            if stop['travel_required']:
                add_leg(current, stop, 'outbound', f"To game: {note_base}")
                current = dict(stop)
            elif place_key(current) != place_key(home_base):
                add_leg(current, home_base, 'return', f"Return home before: {note_base}")
                current = dict(home_base)

            if i == len(seq) - 1:
                if place_key(current) != place_key(home_base):
                    add_leg(current, home_base, 'return', "Return home after season")
                break

            nxt = seq[i + 1]['stop']
            if stop['travel_required'] and should_stay(stop, nxt):
                current = dict(stop)
            elif place_key(current) != place_key(home_base):
                add_leg(current, home_base, 'return', f"Return home after: {note_base}")
                current = dict(home_base)

        flights = len(legs)
        total_miles = int(sum(l['miles'] for l in legs if l['miles'] is not None))

        def stat_card(label, value, sub='', accent=c1):
            return f'''
      <div style="background:#fff;border:1px solid #e2e6ef;border-radius:10px;
          padding:18px 22px;box-shadow:0 1px 6px rgba(0,0,0,0.07);
          flex:1;min-width:140px;text-align:center;border-top:4px solid {accent};">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:800;
            letter-spacing:4px;text-transform:uppercase;color:#b0baca;margin-bottom:4px;">{label}</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:48px;color:{accent};line-height:1;">{value}</div>
        {f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:2px;">{sub}</div>' if sub else ''}
      </div>'''

        cards_html = '<div style="display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap;">'
        cards_html += stat_card('Flights', flights)
        cards_html += stat_card('Total Miles', f'{total_miles:,}')
        cards_html += '</div>'
        st.html(cards_html)

        arc_rows = []
        for l in legs:
            if not (tv_valid_coord(l['src_lat']) and tv_valid_coord(l['src_lon']) and tv_valid_coord(l['dst_lat']) and tv_valid_coord(l['dst_lon'])):
                continue
            arc_rows.append({
                'from': l['from'], 'to': l['to'], 'note': l['note'], 'miles': l['miles'] or 0,
                'src_lon': float(l['src_lon']), 'src_lat': float(l['src_lat']),
                'dst_lon': float(l['dst_lon']), 'dst_lat': float(l['dst_lat']),
                'color': [37, 99, 235, 180] if l['kind'] == 'outbound' else [220, 38, 38, 160],
            })

        arc_df = pd.DataFrame(arc_rows) if arc_rows else pd.DataFrame()
        node_rows = []
        if tv_valid_coord(home_base.get('lat')) and tv_valid_coord(home_base.get('lon')):
            node_rows.append({
                'name': home_base.get('city') or selected_team,
                'lon': float(home_base['lon']), 'lat': float(home_base['lat']),
                'size': 18000, 'color': [200, 16, 46, 210],
            })
        for g in seq:
            s = g['stop']
            if tv_valid_coord(s.get('lat')) and tv_valid_coord(s.get('lon')):
                node_rows.append({
                    'name': s.get('city') or s.get('opponent') or 'Stop',
                    'lon': float(s['lon']),
                    'lat': float(s['lat']),
                    'size': 9000,
                    'color': [30, 64, 175, 180],
                })
        node_df = pd.DataFrame(node_rows).drop_duplicates(subset=['lon', 'lat']) if node_rows else pd.DataFrame()

        layers = []
        if len(arc_df) > 0:
            layers.append(
                pdk.Layer(
                    "ArcLayer",
                    data=arc_df,
                    get_source_position='[src_lon, src_lat]',
                    get_target_position='[dst_lon, dst_lat]',
                    get_source_color='color',
                    get_target_color='color',
                    auto_highlight=True,
                    pickable=True,
                    get_width=3,
                )
            )
        if len(node_df) > 0:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=node_df,
                    get_position='[lon, lat]',
                    get_fill_color='color',
                    get_radius='size',
                    pickable=True,
                )
            )

        if layers:
            st.pydeck_chart(
                pdk.Deck(
                    map_style=pdk.map_styles.LIGHT,
                    initial_view_state=pdk.ViewState(latitude=39.5, longitude=-98.35, zoom=3.2, pitch=25),
                    layers=layers,
                    tooltip={'text': '{from} -> {to}\n{note}\n{miles} miles'},
                ),
                use_container_width=True
            )
        else:
            st.info("Not enough coordinate data to draw travel routes yet.")

        leg_rows_html = ''
        for i, l in enumerate(legs):
            row_bg = '#ffffff' if i % 2 == 0 else '#f8fafc'
            miles = f"{int(l['miles']):,} mi" if l['miles'] is not None else 'TBD'
            kind = 'OUT' if l['kind'] == 'outbound' else 'RET'
            kind_bg = '#dbeafe' if l['kind'] == 'outbound' else '#fee2e2'
            kind_fg = '#1e3a8a' if l['kind'] == 'outbound' else '#991b1b'
            leg_rows_html += f"""
<tr style="background:{row_bg};border-bottom:1px solid #edf0f7;">
  <td style="padding:10px 12px;">
    <span style="background:{kind_bg};color:{kind_fg};padding:2px 8px;border-radius:4px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:1px;">{kind}</span>
  </td>
  <td style="padding:10px 14px;font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:700;color:#1a2030;">{l['from']} -> {l['to']}</td>
  <td style="padding:10px 14px;font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:700;color:#1a2030;text-align:right;">{miles}</td>
  <td style="padding:10px 14px;font-family:'Barlow',sans-serif;font-size:12px;color:#64748b;">{l['note']}</td>
</tr>"""

        st.html(f"""
<div style="margin-top:16px;overflow-x:auto;border-radius:10px;border:1px solid #e2e6ef;
     box-shadow:0 2px 10px rgba(0,0,0,0.08);background:#fff;">
  <table style="border-collapse:collapse;width:100%;min-width:760px;">
    <thead>
      <tr style="background:#f4f6fa;border-bottom:2px solid #e2e6ef;">
        <th style="padding:10px 12px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:left;">Leg</th>
        <th style="padding:10px 14px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:left;">Route</th>
        <th style="padding:10px 14px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:right;">Miles</th>
        <th style="padding:10px 14px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:left;">Detail</th>
      </tr>
    </thead>
    <tbody>
      {leg_rows_html}
    </tbody>
  </table>
</div>""")

        st.stop()

        away_games = Games[
            (Games['Away'] == selected_team) |
            ((Games['Home'] == selected_team) & (Games['International'] == True))  # noqa: E712
        ].copy().sort_values('Week').reset_index(drop=True)

        home_lat = lat_map.get(selected_team)
        home_lon = lon_map.get(selected_team)
        has_home_coords = tv_valid_coord(home_lat) and tv_valid_coord(home_lon)

        total_miles  = 0
        max_trip     = 0
        max_trip_opp = ''
        long_haul    = 0
        tz_changes   = 0
        home_tz      = tz_map.get(selected_team, '')
        n_dist       = 0

        travel_rows = ''

        for idx, g in away_games.iterrows():
            intl_val = g.get('International', False)
            is_intl  = bool(intl_val) if not isinstance(intl_val, float) else False
            try:
                week = int(g['Week'])
            except Exception:
                week = 'TBA'
            game_loc = str(g.get('Location', '') or '').strip()

            opponent = g['Home'] if g['Away'] == selected_team else g['Away']

            try:
                dt     = pd.to_datetime(g['Date'])
                date_d = dt.strftime('%a, %b') + ' ' + str(dt.day)
            except Exception:
                date_d = str(g.get('Date', ''))

            time_et = str(g.get('Time (ET)', '') or '').strip()
            if time_et.lower() in ('nan', ''):
                time_et = 'TBD'

            dest_lat, dest_lon, dest_tz, stad_dest, loc_disp = None, None, '', '', game_loc
            venue_override = get_forced_venue(g)

            if venue_override:
                stad_dest, loc_disp = venue_override
                dest_tz = 'PT'
            elif is_intl:
                idata     = intl_data.get(game_loc, {})
                dest_lat  = idata.get('lat')
                dest_lon  = idata.get('lon')
                dest_tz   = idata.get('tz', '')
                stad_dest = idata.get('stad', '')
                loc_disp  = game_loc
            else:
                dest_lat  = lat_map.get(opponent)
                dest_lon  = lon_map.get(opponent)
                dest_tz   = tz_map.get(opponent, '')
                stad_dest = stad_map.get(opponent, '')
                loc_disp  = city_map.get(opponent, game_loc)

            if not loc_disp:
                loc_disp = game_loc

            # Distance
            dist_str = '—'
            dist_num = None
            if has_home_coords and tv_valid_coord(dest_lat) and tv_valid_coord(dest_lon):
                try:
                    dist_num = tv_haversine(
                        float(home_lat), float(home_lon),
                        float(dest_lat), float(dest_lon)
                    )
                    dist_str = f'{dist_num:,} mi'
                    total_miles += dist_num
                    n_dist += 1
                    if dist_num > max_trip:
                        max_trip = dist_num
                        max_trip_opp = opponent
                    if dist_num > 1500:
                        long_haul += 1
                except Exception:
                    pass

            # Timezone badge
            tz_badge = ''
            if dest_tz and home_tz and dest_tz.strip() not in ('', 'nan') and dest_tz != home_tz:
                tz_changes += 1
                tz_badge = (
                    '<span style="background:#fef3c7;color:#92400e;font-family:\'Barlow Condensed\','
                    'sans-serif;font-size:10px;font-weight:800;letter-spacing:1px;padding:2px 6px;'
                    'border-radius:3px;margin-left:6px;white-space:nowrap;">TZ&nbsp;SHIFT</span>'
                )

            intl_badge_t = (
                '<span style="background:#7c3aed;color:#fff;font-family:\'Barlow Condensed\','
                'sans-serif;font-size:10px;font-weight:800;letter-spacing:2px;padding:2px 6px;'
                'border-radius:3px;margin-left:6px;">INTL</span>'
            ) if is_intl else ''

            dist_color = (
                '#dc2626' if (dist_num and dist_num > 2500)
                else '#d97706' if (dist_num and dist_num > 1500)
                else '#1a2030'
            )

            opp_logo = logo_map.get(opponent, TBD_LOGO)
            opp_clr  = clr1_map.get(opponent, '#888')
            row_bg   = '#ffffff' if idx % 2 == 0 else '#f8fafc'

            tz_disp = dest_tz if dest_tz and dest_tz.lower() not in ('nan', '') else '—'

            travel_rows += f"""
<tr style="background:{row_bg};border-bottom:1px solid #f0f2f7;">
  <td style="width:4px;padding:0;background:{opp_clr};"></td>
  <td style="padding:10px 8px 10px 12px;text-align:center;vertical-align:middle;width:52px;">
    <div style="width:32px;height:32px;border-radius:50%;background:{c1};color:{fg1};
         display:inline-flex;align-items:center;justify-content:center;
         font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:800;">{week}</div>
  </td>
  <td style="padding:10px 16px;vertical-align:middle;white-space:nowrap;width:130px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:16px;font-weight:700;
         color:#1a2030;">{date_d}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:12px;color:#9aa5be;">{time_et} ET</div>
  </td>
  <td style="padding:10px 16px;vertical-align:middle;min-width:210px;">
    <div style="display:flex;align-items:center;gap:12px;">
      <div style="width:42px;height:42px;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
        <img src="{opp_logo}" style="max-width:42px;max-height:42px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
      <div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:700;
             color:#1a2030;">{opponent}{intl_badge_t}</div>
        <div style="font-family:'Barlow',sans-serif;font-size:12px;color:#9aa5be;">{loc_disp}</div>
      </div>
    </div>
  </td>
  <td style="padding:10px 16px;vertical-align:middle;min-width:180px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:15px;font-weight:600;
         color:#2a3550;">{stad_dest or '—'}</div>
  </td>
  <td style="padding:10px 16px;vertical-align:middle;text-align:center;width:120px;">
    <div style="font-family:'Rajdhani',sans-serif;font-size:21px;font-weight:700;
         color:{dist_color};">{dist_str}</div>
  </td>
  <td style="padding:10px 16px;vertical-align:middle;width:160px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:600;
         color:#475569;display:flex;align-items:center;flex-wrap:wrap;gap:4px;">
      {tz_disp}{tz_badge}
    </div>
  </td>
</tr>"""

    def stat_card(label, value, sub='', accent=c1):
        return f'''
      <div style="background:#fff;border:1px solid #e2e6ef;border-radius:10px;
          padding:18px 22px;box-shadow:0 1px 6px rgba(0,0,0,0.07);
          flex:1;min-width:120px;text-align:center;border-top:4px solid {accent};">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:800;
            letter-spacing:4px;text-transform:uppercase;color:#b0baca;margin-bottom:4px;">{label}</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:48px;color:{accent};line-height:1;">{value}</div>
        {f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:2px;">{sub}</div>' if sub else ''}
      </div>'''

        cards_html = '<div style="display:flex;gap:14px;margin-bottom:22px;flex-wrap:wrap;">'
        cards_html += stat_card('Road Games', len(away_games))
        if n_dist > 0:
            cards_html += stat_card('Est. Miles', f'{total_miles:,}')
            cards_html += stat_card('Longest Trip', f'{max_trip:,}', f'vs {max_trip_opp}')
            cards_html += stat_card('Long-Haul >1500mi', long_haul)
        cards_html += stat_card('TZ Changes', tz_changes)
        if n_dist == 0:
            cards_html += '''
  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:10px;
       padding:18px 22px;box-shadow:0 1px 6px rgba(0,0,0,0.07);flex:2;min-width:220px;
       display:flex;align-items:center;gap:12px;border-top:4px solid #e2e6ef;">
    <span style="font-size:24px;">📍</span>
    <div style="font-family:'Barlow',sans-serif;font-size:13px;color:#9aa5be;line-height:1.6;">
      Stadium coordinates not yet available — distance estimates will appear once location data is loaded.</div>
  </div>'''
        cards_html += '</div>'

        st.html(f"""
<div style="margin-top:22px;">
  {cards_html}
  <div style="overflow-x:auto;border-radius:10px;border:1px solid #e2e6ef;
       box-shadow:0 2px 10px rgba(0,0,0,0.08);background:#fff;">
    <table style="border-collapse:collapse;width:100%;min-width:720px;">
      <thead>
        <tr style="background:#f4f6fa;border-bottom:2px solid #e2e6ef;">
          <th style="width:4px;background:#f4f6fa;"></th>
          <th style="padding:10px 8px 10px 12px;font-family:'Barlow Condensed',sans-serif;
               font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
               color:#b0baca;text-align:center;">WK</th>
          <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
               font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
               color:#b0baca;text-align:left;">DATE</th>
          <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
               font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
               color:#b0baca;text-align:left;">OPPONENT</th>
          <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
               font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
               color:#b0baca;text-align:left;">STADIUM</th>
          <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
               font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
               color:#b0baca;text-align:center;">DISTANCE</th>
          <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;
               font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;
               color:#b0baca;text-align:left;">TIME ZONE</th>
        </tr>
      </thead>
      <tbody>
        {travel_rows}
      </tbody>
    </table>
  </div>
</div>""")
