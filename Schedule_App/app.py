import math
import html
import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pydeck as pdk

AppLogo = "https://pbs.twimg.com/media/HIEZ_LdbAAA2GR2?format=png&name=900x900"

TV_LOGO_MAP = {
    'ESPN': 'https://pbs.twimg.com/media/HH7aIPVbAAECaT8?format=png&name=360x360',
    'CBS': 'https://pbs.twimg.com/media/HH7aIPVakAAavgX?format=png&name=360x360',
    'Fox': 'https://pbs.twimg.com/media/HH7aFy1aUAAlk2c?format=png&name=360x360',
    'Prime Video': 'https://pbs.twimg.com/media/HH7aFy4bkAAQm8X?format=png&name=360x360',
    'Netflix': 'https://pbs.twimg.com/media/HH7aIPRbQAAG3Mb?format=png&name=360x360',
    'Youtube': 'https://pbs.twimg.com/media/HH7aFy5acAAS1xR?format=png&name=360x360',
    'NFL Network': 'https://pbs.twimg.com/media/HH7aFy4awAAmYjY?format=png&name=360x360',
    'NBC': 'https://pbs.twimg.com/media/HH7aIPcbUAA8FJK?format=png&name=360x360',
}

@st.cache_data(ttl=300)
def get_games() -> pd.DataFrame:
    csv_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=0"
    df = pd.read_csv(csv_url)
    csv_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=597170352"
    df2 = pd.read_csv(csv_url)
    csv_url = "https://docs.google.com/spreadsheets/d/1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/export?format=csv&gid=223751105"
    df3 = pd.read_csv(csv_url)
    return df, df2, df3

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
Games['Week'] = pd.to_numeric(Games.get('Week'), errors='coerce')
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
  width: 120px; height: 120px; object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(200,16,46,0.25));
}
.app-logo {
  width: 152px; height: 152px; object-fit: contain;
  filter: drop-shadow(0 2px 8px rgba(15,23,42,0.16));
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
      <div class="masthead-title">2026 NFL SCHEDULE</div>
    </div>
  </div>
  <img class="app-logo" src="{AppLogo}" alt="Schedule logo">
</div>
""")

selected_season = '2026'
Games = ALL_GAMES[ALL_GAMES['_season'].astype(str) == str(selected_season)].copy()

ANALYTICS_RELEASE_NOTE = """
<div style="margin:14px 0 4px;padding:10px 14px;border-left:4px solid #c8102e;
     background:#fff;border-top:1px solid #e2e6ef;border-right:1px solid #e2e6ef;
     border-bottom:1px solid #e2e6ef;border-radius:6px;font-family:'Barlow',sans-serif;
     font-size:13px;line-height:1.5;color:#64748b;">
  <strong style="color:#1a2030;">*</strong> These analytics are unstable until all games have been entered. Check back after the full release for the complete breakdown.
</div>
"""

# Manual travel stay-overs: add entries here when a team does not return home
# between two listed game weeks. Example: Jacksonville stays in London between
# its Week 5 and Week 6 international home games.
MANUAL_TRAVEL_STAYOVERS = [
    {'team': 'Jacksonville Jaguars', 'from_week': 5, 'to_week': 6},
]

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

def travel_valid_coord(val):
    if val is None:
        return False
    try:
        f = float(val)
        return not math.isnan(f)
    except Exception:
        return False

def travel_haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def travel_week_num(value):
    wk = pd.to_numeric(value, errors='coerce')
    if pd.notna(wk):
        return float(wk)
    cleaned = str(value or '').strip().lower().replace('week', '').replace('wk', '').strip()
    wk = pd.to_numeric(cleaned, errors='coerce')
    return None if pd.isna(wk) else float(wk)

def manual_travel_stayover(team, from_week, to_week):
    if from_week is None or to_week is None:
        return False
    for item in MANUAL_TRAVEL_STAYOVERS:
        if str(item.get('team', '')).strip() != str(team).strip():
            continue
        try:
            if float(item.get('from_week')) == float(from_week) and float(item.get('to_week')) == float(to_week):
                return True
        except Exception:
            continue
    return False

def manual_travel_stayover_to(team, to_week):
    if to_week is None:
        return False
    for item in MANUAL_TRAVEL_STAYOVERS:
        if str(item.get('team', '')).strip() != str(team).strip():
            continue
        try:
            if float(item.get('to_week')) == float(to_week):
                return True
        except Exception:
            continue
    return False

def build_team_travel(team, games, city_map, stad_map, lat_map, lon_map, tz_map, intl_data, color_map=None):
    team_games = games[(games['Home'] == team) | (games['Away'] == team)].copy()
    team_games['_week_num'] = pd.to_numeric(team_games['Week'], errors='coerce')
    team_games['_date_num'] = pd.to_datetime(team_games['Date'], errors='coerce')
    team_games = team_games.sort_values(['_week_num', '_date_num']).reset_index(drop=True)

    home_base = {
        'name': team,
        'city': city_map.get(team, ''),
        'stadium': stad_map.get(team, ''),
        'lat': lat_map.get(team),
        'lon': lon_map.get(team),
        'tz': tz_map.get(team, ''),
    }

    def place_key(p):
        if travel_valid_coord(p.get('lat')) and travel_valid_coord(p.get('lon')):
            return f"{round(float(p['lat']), 2)}|{round(float(p['lon']), 2)}"
        return f"{p.get('city', '')}|{p.get('stadium', '')}"

    def resolve_stop(g):
        is_home = g['Home'] == team
        opponent = g['Away'] if is_home else g['Home']
        game_loc = str(g.get('Location', '') or '').strip()
        intl_val = g.get('International', False)
        is_intl = bool(intl_val) if not isinstance(intl_val, float) else False
        override = get_forced_venue(g)

        if override:
            return {
                'opponent': opponent, 'is_intl': False, 'travel_required': True,
                'city': override[1], 'stadium': override[0], 'lat': lat_map.get('Los Angeles Rams'),
                'lon': lon_map.get('Los Angeles Rams'), 'tz': 'PT',
            }

        team_city = city_map.get(team, '').lower()
        opp_city = city_map.get(opponent, '').lower()
        game_loc_lower = game_loc.lower() if game_loc else ''
        is_neutral = (game_loc in NEUTRAL_LOCATION_SET) or (is_intl and game_loc) or (game_loc_lower and team_city and opp_city and game_loc_lower != team_city and game_loc_lower != opp_city)

        if is_neutral and game_loc:
            idata = intl_data.get(game_loc, {})
            return {
                'opponent': opponent, 'is_intl': is_intl, 'travel_required': True,
                'city': game_loc, 'stadium': idata.get('stad', ''),
                'lat': idata.get('lat'), 'lon': idata.get('lon'), 'tz': idata.get('tz', ''),
            }
        if is_home:
            return {
                'opponent': opponent, 'is_intl': False, 'travel_required': False,
                'city': city_map.get(team, ''), 'stadium': stad_map.get(team, ''),
                'lat': lat_map.get(team), 'lon': lon_map.get(team), 'tz': tz_map.get(team, ''),
            }
        return {
            'opponent': opponent, 'is_intl': False, 'travel_required': True,
            'city': city_map.get(opponent, game_loc), 'stadium': stad_map.get(opponent, ''),
            'lat': lat_map.get(opponent), 'lon': lon_map.get(opponent), 'tz': tz_map.get(opponent, ''),
        }

    def should_stay(cur_game, next_game):
        cur_stop = cur_game['stop']
        next_stop = next_game['stop']
        if not (cur_stop['travel_required'] and next_stop['travel_required']):
            return False
        return manual_travel_stayover(team, cur_game.get('week_num'), next_game.get('week_num'))

    legs = []
    current = dict(home_base)

    def add_leg(src, dst, kind, note, week_num=None):
        if place_key(src) == place_key(dst):
            return
        if not dst.get('city') or dst.get('city') == '—':
            return
        miles = None
        if (
            travel_valid_coord(src.get('lat')) and travel_valid_coord(src.get('lon')) and
            travel_valid_coord(dst.get('lat')) and travel_valid_coord(dst.get('lon'))
        ):
            miles = travel_haversine(float(src['lat']), float(src['lon']), float(dst['lat']), float(dst['lon']))
        legs.append({
            'team': team,
            'color_hex': (color_map or {}).get(team, '#2563eb'),
            'from': src.get('city') or src.get('name') or 'Unknown',
            'to': dst.get('city') or dst.get('name') or 'Unknown',
            'miles': miles,
            'kind': kind,
            'note': note,
            'week_num': week_num,
            'src_lat': src.get('lat'), 'src_lon': src.get('lon'),
            'dst_lat': dst.get('lat'), 'dst_lon': dst.get('lon'),
        })

    seq = []
    for _, g in team_games.iterrows():
        wk_num = travel_week_num(g.get('Week'))
        if wk_num is not None:
            if wk_num == 18.5:
                wk_lbl = 'Wk TBD'
            else:
                wk_lbl = f"Wk {wk_num if wk_num != int(wk_num) else int(wk_num)}"
        else:
            wk_lbl = 'Wk TBA'
        seq.append({'week_label': wk_lbl, 'week_num': wk_num, 'stop': resolve_stop(g)})

    for i, game in enumerate(seq):
        stop = game['stop']
        note_base = f"{game['week_label']} vs {stop['opponent']}"
        if stop['travel_required']:
            if i > 0 and should_stay(seq[i - 1], game):
                add_leg(current, stop, 'transfer', f"Stay-over transfer: {note_base}", game.get('week_num'))
                current = dict(stop)
            else:
                add_leg(current, stop, 'outbound', f"To game: {note_base}", game.get('week_num'))
                current = dict(stop)
        elif place_key(current) != place_key(home_base):
            add_leg(current, home_base, 'return', f"Return home before: {note_base}", game.get('week_num'))
            current = dict(home_base)

        if i == len(seq) - 1:
            if place_key(current) != place_key(home_base):
                add_leg(current, home_base, 'return', "Return home after season", game.get('week_num'))
            break

        if stop['travel_required'] and should_stay(game, seq[i + 1]):
            current = dict(stop)
        elif place_key(current) != place_key(home_base):
            add_leg(current, home_base, 'return', f"Return home after: {note_base}", game.get('week_num'))
            current = dict(home_base)

    return {
        'home_base': home_base,
        'seq': seq,
        'legs': legs,
        'flights': len(legs),
        'total_miles': int(sum(l['miles'] for l in legs if l['miles'] is not None)),
    }

def travel_map_rows(legs, home_base=None, seq=None, max_arcs=None):
    arc_rows = []
    for l in legs:
        if l.get('kind') not in ('outbound', 'transfer'):
            continue
        if not (
            travel_valid_coord(l.get('src_lat')) and travel_valid_coord(l.get('src_lon')) and
            travel_valid_coord(l.get('dst_lat')) and travel_valid_coord(l.get('dst_lon'))
        ):
            continue
        arc_rows.append({
            'from': l['from'], 'to': l['to'], 'note': l['note'], 'miles': l['miles'] or 0,
            'src_lon': float(l['src_lon']), 'src_lat': float(l['src_lat']),
            'dst_lon': float(l['dst_lon']), 'dst_lat': float(l['dst_lat']),
            'kind': l.get('kind', 'outbound'),
            'color_hex': l.get('color_hex', '#2563eb'),
        })
    if max_arcs:
        arc_rows = sorted(arc_rows, key=lambda r: r['miles'], reverse=True)[:max_arcs]

    node_rows = []
    if home_base and travel_valid_coord(home_base.get('lat')) and travel_valid_coord(home_base.get('lon')):
        node_rows.append({
            'name': home_base.get('city') or home_base.get('name') or 'Home',
            'lon': float(home_base['lon']), 'lat': float(home_base['lat']),
            'home': True,
        })
    for g in seq or []:
        s = g['stop']
        if travel_valid_coord(s.get('lat')) and travel_valid_coord(s.get('lon')):
            node_rows.append({
                'name': s.get('city') or s.get('opponent') or 'Stop',
                'lon': float(s['lon']), 'lat': float(s['lat']),
                'home': False,
            })
    for a in arc_rows:
        node_rows.append({'name': a['from'], 'lon': a['src_lon'], 'lat': a['src_lat'], 'home': False})
        node_rows.append({'name': a['to'], 'lon': a['dst_lon'], 'lat': a['dst_lat'], 'home': False})
    node_df = pd.DataFrame(node_rows).drop_duplicates(subset=['lon', 'lat']) if node_rows else pd.DataFrame()
    return pd.DataFrame(arc_rows) if arc_rows else pd.DataFrame(), node_df

def render_travel_motion_map(arc_df, node_df, key, height=500, initial_view=None):
    if len(arc_df) == 0:
        st.info("Not enough coordinate data to draw travel routes yet.")
        return

    arcs = arc_df.to_dict('records')
    nodes = node_df.to_dict('records') if len(node_df) else []
    map_id = f"travel-map-{''.join(ch if ch.isalnum() else '-' for ch in str(key))}"
    arcs_json = json.dumps(arcs)
    nodes_json = json.dumps(nodes)
    use_fixed_view = 'true' if initial_view is not None else 'false'
    iv_lat, iv_lon, iv_zoom = initial_view if initial_view else (39.5, -98.35, 4)
    components.html(f"""
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  #{map_id} {{
    height: {height}px;
    width: 100%;
    border: 1px solid #d9e0ec;
    border-radius: 10px;
    overflow: hidden;
    background: #dbeafe;
  }}
  #{map_id} .leaflet-control-attribution {{
    font-family: Arial, sans-serif;
    font-size: 10px;
  }}
  #{map_id} .leaflet-tile-pane {{
    filter: saturate(0.78) contrast(0.96) brightness(1.04);
  }}
</style>
<div id="{map_id}"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function() {{
  const arcs = {arcs_json};
  const nodes = {nodes_json};
  const mapEl = document.getElementById("{map_id}");

  function boot() {{
    if (!window.L || !mapEl) {{
      setTimeout(boot, 60);
      return;
    }}

    const map = L.map(mapEl, {{
      zoomControl: true,
      scrollWheelZoom: false,
      attributionControl: true,
      preferCanvas: true
    }});

    L.tileLayer("https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png", {{
      attribution: "&copy; OpenStreetMap &copy; CARTO",
      subdomains: "abcd",
      maxZoom: 18
    }}).addTo(map);

    const bounds = [];
    arcs.forEach(a => bounds.push([a.src_lat, a.src_lon], [a.dst_lat, a.dst_lon]));
    nodes.forEach(n => bounds.push([n.lat, n.lon]));
    if ({use_fixed_view}) {{
      map.setView([{iv_lat}, {iv_lon}], {iv_zoom});
    }} else if (bounds.length) {{
      map.fitBounds(bounds, {{ padding: [28, 28], maxZoom: 5 }});
    }} else {{
      map.setView([39.5, -98.35], 4);
    }}

    const routeLayer = L.svg({{ padding: 0.35 }}).addTo(map);
    const svg = routeLayer.getPane().querySelector("svg");
    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    svg.appendChild(g);

    function curvePoints(a, steps) {{
      const p0 = map.latLngToLayerPoint([a.src_lat, a.src_lon]);
      const p2 = map.latLngToLayerPoint([a.dst_lat, a.dst_lon]);
      const dx = p2.x - p0.x;
      const dy = p2.y - p0.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const lift = Math.min(Math.max(dist * 0.18, 34), 120);
      const p1 = L.point((p0.x + p2.x) / 2 - (dy / dist) * lift, (p0.y + p2.y) / 2 + (dx / dist) * lift);
      const pts = [];
      for (let i = 0; i <= steps; i++) {{
        const t = i / steps;
        const x = (1 - t) * (1 - t) * p0.x + 2 * (1 - t) * t * p1.x + t * t * p2.x;
        const y = (1 - t) * (1 - t) * p0.y + 2 * (1 - t) * t * p1.y + t * t * p2.y;
        pts.push([x, y]);
      }}
      return pts;
    }}

    const movers = [];
    function redraw() {{
      g.innerHTML = "";
      movers.length = 0;

      arcs.forEach((a, i) => {{
        const color = a.color_hex || "#2563eb";
        const pts = curvePoints(a, 36);
        const d = pts.map((p, idx) => `${{idx ? "L" : "M"}} ${{p[0].toFixed(1)}} ${{p[1].toFixed(1)}}`).join(" ");
        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d);
        path.setAttribute("fill", "none");
        path.setAttribute("stroke", color);
        path.setAttribute("stroke-width", "2.4");
        path.setAttribute("stroke-opacity", "0.42");
        path.setAttribute("stroke-linecap", "round");
        g.appendChild(path);

        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        dot.setAttribute("r", "5.2");
        dot.setAttribute("fill", color);
        dot.setAttribute("stroke", "#ffffff");
        dot.setAttribute("stroke-width", "1.5");
        dot.setAttribute("opacity", "0.94");
        g.appendChild(dot);
        movers.push({{ dot, pts, offset: (i % 14) * 0.075 }});
      }});

      nodes.forEach(n => {{
        const p = map.latLngToLayerPoint([n.lat, n.lon]);
        const ring = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        ring.setAttribute("cx", p.x);
        ring.setAttribute("cy", p.y);
        ring.setAttribute("r", n.home ? "6.5" : "5.5");
        ring.setAttribute("fill", "#ffffff");
        ring.setAttribute("stroke", n.home ? "#c8102e" : "#1a2030");
        ring.setAttribute("stroke-width", n.home ? "2.8" : "2.1");
        ring.setAttribute("opacity", "0.95");
        g.appendChild(ring);
      }});
    }}

    function animate(now) {{
      const cycle = 7600;
      movers.forEach(m => {{
        const raw = ((now % cycle) / cycle + m.offset) % 1;
        const t = raw <= 0.5 ? raw * 2 : (1 - raw) * 2;
        const idx = Math.min(Math.floor(t * (m.pts.length - 1)), m.pts.length - 1);
        const p = m.pts[idx];
        m.dot.setAttribute("cx", p[0]);
        m.dot.setAttribute("cy", p[1]);
      }});
      requestAnimationFrame(animate);
    }}

    redraw();
    map.on("zoomend moveend resize", redraw);
    requestAnimationFrame(animate);
  }}

  boot();
}})();
</script>
""", height=height + 10)

def build_cells(Games, Team_Info, Other_Locations):
    abb_lookup = dict(zip(Team_Info['Team'], Team_Info['Abb']))
    cells = {}
    for _, g in Games.iterrows():
        try:
            week_raw = pd.to_numeric(g['Week'], errors='coerce')
            if pd.notna(week_raw) and week_raw == int(week_raw):
                week = int(week_raw)
            else:
                continue
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
            bye_int = int(float(bye_wk)) if bye_wk is not None and str(bye_wk).strip() not in ('', 'nan') else None
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
    lv_lat_map = dict(TEAM_LAT_MAP)
    lv_lon_map = dict(TEAM_LON_MAP)
    lv_tz_map = dict(TEAM_TZ_MAP)
    lv_clr_map = {}
    for _, row in Team_Info.iterrows():
        t = row['Team']
        c = str(row.get('Color1', '') or '').strip().strip('`').strip("'\"")
        if not c or c.lower() in ('nan', 'none'):
            c = '#c8102e'
        lv_clr_map[t] = c if c.startswith('#') else f'#{c}'
    lv_intl_locs = set(NEUTRAL_LOCATION_SET)
    lv_intl_stad = {k: _clean_text(v.get('stad', '')) for k, v in INTL_DATA.items()}
    lv_intl_data = dict(INTL_DATA)

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
                # TV badge - use logo if available, otherwise use text
                if tv:
                    tv_logo_url = TV_LOGO_MAP.get(tv, '')
                    if tv_logo_url:
                        tv_badge = f'<img src="{tv_logo_url}" style="max-height:65px;max-width:200px;object-fit:contain;" onerror="this.style.display=\'none\';">'
                    else:
                        tv_badge = (
                            f'<span style="background:#f1f5f9;color:#475569;font-family:\'Barlow Condensed\','
                            f'sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;padding:3px 10px;'
                            f'border-radius:3px;border:1px solid #dde2ed;white-space:nowrap;">{tv}</span>'
                        )
                else:
                    tv_badge = ''
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

            bye_teams = Team_Info[pd.to_numeric(Team_Info['Bye'], errors='coerce') == selected_week].copy()
            if len(bye_teams) > 0:
                bye_tiles_html = """
<div style="margin-top:24px;">
  <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:800;
       letter-spacing:3px;text-transform:uppercase;color:#b0baca;margin-bottom:14px;">
    Teams on Bye
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:12px;">"""
                for _, bye_team in bye_teams.iterrows():
                    team_name = bye_team['Team']
                    team_abb = lv_abb_map.get(team_name, str(team_name)[:3].upper())
                    team_logo = lv_logo_map.get(team_name, TBD_LOGO)
                    team_clr = lv_clr_map.get(team_name, '#374151')

                    bye_tiles_html += f"""
    <div style="display:flex;flex-direction:column;align-items:center;padding:16px 12px;
         border:1px solid #e2e6ef;border-radius:8px;background:#fafbfc;
         border-left:4px solid {team_clr};min-width:100px;text-align:center;">
      <div style="width:48px;height:48px;display:flex;align-items:center;justify-content:center;
           margin-bottom:8px;flex-shrink:0;">
        <img src="{team_logo}" style="max-width:48px;max-height:48px;object-fit:contain;"
             onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      </div>
      <div style="font-family:'Rajdhani',sans-serif;font-size:14px;font-weight:700;
           color:{team_clr};letter-spacing:0.5px;margin-bottom:4px;">
        {team_abb}
      </div>
      <div style="font-family:'Barlow',sans-serif;font-size:11px;color:#9aa5be;line-height:1.3;">
        {team_name}
      </div>
    </div>"""
                bye_tiles_html += """
  </div>
</div>"""
                st.html(bye_tiles_html)

    with sub_tabs2[2]:
        pt_col, _ = st.columns([2.2, 3.8])
        with pt_col:
            primetime_choice = st.selectbox(
                "Select Primetime Window",
                ["Thursday Games", "Friday Games", "Saturday Games", "SNF Games", "Monday Games"],
                key="lv_primetime_select",
            )

        primetime_key = {
            "Thursday Games": "thursday",
            "Friday Games": "friday",
            "Saturday Games": "saturday",
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
                    wk_numeric = pd.to_numeric(wk_raw, errors='coerce')
                    if pd.notna(wk_numeric):
                        wk_val = 'TBD' if wk_numeric == 18.5 else (wk_numeric if wk_numeric != int(wk_numeric) else int(wk_numeric))
                    else:
                        wk_val = 'TBA'
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
                # TV badge - use logo if available, otherwise use text
                if tv:
                    tv_logo_url = TV_LOGO_MAP.get(tv, '')
                    if tv_logo_url:
                        tv_badge = f'<img src="{tv_logo_url}" style="max-height:65px;max-width:200px;object-fit:contain;" onerror="this.style.display=\'none\';">'
                    else:
                        tv_badge = (
                            f'<span style="background:#f1f5f9;color:#475569;font-family:\'Barlow Condensed\','
                            f'sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;padding:3px 10px;'
                            f'border-radius:3px;border:1px solid #dde2ed;white-space:nowrap;">{tv}</span>'
                        )
                else:
                    tv_badge = ''
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
        week_col, _ = st.columns([1.5, 5.5])
        with week_col:
            week_options = ['Full Season'] + [f'Week {w}' for w in range(1, 19)]
            selected_week_display = st.selectbox('Filter by Week', week_options, index=0, key='league_week_filter')

        selected_week_num = None
        if selected_week_display != 'Full Season':
            selected_week_num = int(selected_week_display.split()[1])

        league_routes = []
        team_totals = []
        for team in Team_Info.sort_values('Team')['Team'].tolist():
            route = build_team_travel(
                team, Games, lv_city_map, lv_stad_map, lv_lat_map, lv_lon_map, lv_tz_map, lv_intl_data, lv_clr_map
            )
            route_legs = route['legs']
            if selected_week_num is not None:
                route_legs = [
                    leg for leg in route_legs
                    if leg.get('week_num') is not None and float(leg.get('week_num')) == float(selected_week_num)
                ]
            league_routes.extend(route_legs)
            team_totals.append({
                'Team': team,
                'Total Miles': int(sum(l['miles'] for l in route_legs if l['miles'] is not None)),
            })

        league_total_miles = int(sum(r['Total Miles'] for r in team_totals))
        league_flights = len(league_routes)

        def league_stat_card(label, value, sub='', accent='#c8102e'):
            return f'''
      <div style="background:#fff;border:1px solid #e2e6ef;border-radius:10px;
          padding:18px 22px;box-shadow:0 1px 6px rgba(0,0,0,0.07);
          flex:1;min-width:150px;text-align:center;border-top:4px solid {accent};">
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:800;
            letter-spacing:4px;text-transform:uppercase;color:#b0baca;margin-bottom:4px;">{label}</div>
        <div style="font-family:'Bebas Neue',sans-serif;font-size:48px;color:{accent};line-height:1;">{value}</div>
        {f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:2px;">{sub}</div>' if sub else ''}
      </div>'''

        st.html(
            '<div style="display:flex;gap:14px;margin:18px 0;flex-wrap:wrap;">'
            + league_stat_card('League Flights', f'{league_flights:,}')
            + league_stat_card('Total Miles', f'{league_total_miles:,}')
            + league_stat_card('Teams', f'{len(team_totals):,}')
            + '</div>'
        )

        league_arc_df, league_node_df = travel_map_rows(league_routes)
        render_travel_motion_map(league_arc_df, league_node_df, 'league-travel', height=520, initial_view=(39.5, -98.35, 4))

        totals_df = pd.DataFrame(team_totals).sort_values('Total Miles', ascending=False).reset_index(drop=True)
        league_rows_html = ''
        for i, row in totals_df.iterrows():
            team = row['Team']
            row_bg = '#ffffff' if i % 2 == 0 else '#f8fafc'
            logo = lv_logo_map.get(team, TBD_LOGO)
            accent = lv_clr_map.get(team, '#374151')
            miles = f"{int(row['Total Miles']):,}"
            rank = i + 1
            league_rows_html += f"""
<tr style="background:{row_bg};border-bottom:1px solid #edf0f7;">
  <td style="width:5px;padding:0;background:{accent};"></td>
  <td style="padding:10px 12px;text-align:center;font-family:'Rajdhani',sans-serif;
       font-size:18px;font-weight:800;color:#64748b;width:70px;">{rank}</td>
  <td style="padding:10px 16px;vertical-align:middle;">
    <div style="display:flex;align-items:center;gap:12px;">
      <img src="{logo}" style="width:38px;height:38px;object-fit:contain;"
           onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:19px;font-weight:700;color:#1a2030;">{team}</div>
    </div>
  </td>
  <td style="padding:10px 18px;text-align:right;font-family:'Rajdhani',sans-serif;
       font-size:22px;font-weight:800;color:#1a2030;">{miles}</td>
</tr>"""

        st.html(f"""
<div style="margin-top:18px;overflow-x:auto;border-radius:10px;border:1px solid #e2e6ef;
     box-shadow:0 2px 10px rgba(0,0,0,0.08);background:#fff;">
  <table style="border-collapse:collapse;width:100%;min-width:640px;">
    <thead>
      <tr style="background:#f4f6fa;border-bottom:2px solid #e2e6ef;">
        <th style="width:5px;background:#f4f6fa;"></th>
        <th style="padding:10px 12px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;
             letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:center;">Rank</th>
        <th style="padding:10px 16px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;
             letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:left;">Team</th>
        <th style="padding:10px 18px;font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;
             letter-spacing:3px;text-transform:uppercase;color:#b0baca;text-align:right;">Total Miles</th>
      </tr>
    </thead>
    <tbody>
      {league_rows_html}
    </tbody>
  </table>
</div>""")

    with sub_tabs2[4]:
        # Filter to weeks 1-18 only
        analytics_games = Games.copy()
        analytics_games['_week_num'] = pd.to_numeric(analytics_games['Week'], errors='coerce')
        analytics_games = analytics_games[(analytics_games['_week_num'].notna()) & (analytics_games['_week_num'] >= 1) & (analytics_games['_week_num'] <= 18)]

        # ── Sorting JavaScript ───────────────────────────────────────────────
        sort_script = '''<script>
function makeSortable(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const headers = table.querySelectorAll('thead th');
  headers.forEach((header, idx) => {
    if (idx < 2) return;
    header.style.cursor = 'pointer';
    header.addEventListener('click', () => sortTable(tableId, idx));
  });
}
function sortTable(tableId, col) {
  const table = document.getElementById(tableId);
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr')).filter(r => r.querySelectorAll('td').length > col);
  rows.sort((a, b) => {
    const aVal = a.querySelectorAll('td')[col]?.textContent.trim() || '';
    const bVal = b.querySelectorAll('td')[col]?.textContent.trim() || '';
    const aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
    const bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
    if (!isNaN(aNum) && !isNaN(bNum)) return bNum - aNum;
    return aVal.localeCompare(bVal);
  });
  rows.forEach(r => tbody.appendChild(r));
}
setTimeout(() => {
  makeSortable('lga-sos-table');
  makeSortable('lga-sfi-table');
  makeSortable('lga-hardest-table');
  makeSortable('lga-top-games-table');
}, 100);
</script>'''

        # ── League Analytics Helpers ─────────────────────────────────────────
        lga_strength_cols = [
            ('O/U', 'Vegas O/U', 'high'),
            ('2025 W', '2025 Wins', 'high'),
            ('DVOA', 'Total', 'high'),
            ('DVOA Rk', 'Total Rank', 'low'),
            ('Off', 'Offense', 'high'),
            ('Off Rk', 'Offensive Rank', 'low'),
            ('Def', 'Defense', 'low'),
            ('Def Rk', 'Defensive Rank', 'low'),
            ('ST', 'Special Teams', 'high'),
            ('ST Rk', 'Special Teams Rank', 'low'),
        ]
        lga_continuity_cols = [
            ('QB', 'QB Tenure', 'high'),
            ('HC', 'HC Tenure', 'high'),
            ('OC', 'OC Tenure', 'high'),
            ('DC', 'DC Tenure', 'high'),
            ('SC', 'SC Tenure', 'high'),
        ]
        lga_fantasy_cols = [
            ('QB', 'QBF', 'high'),
            ('QB Rk', 'QBFR', 'high'),
            ('RB', 'RBF', 'high'),
            ('RB Rk', 'RBFR', 'high'),
            ('WR', 'WRF', 'high'),
            ('WR Rk', 'WRFR', 'high'),
            ('TE', 'TEF', 'high'),
            ('TE Rk', 'TEFR', 'high'),
            ('K', 'KF', 'high'),
            ('K Rk', 'KFR', 'high'),
            ('DST', 'DSTF', 'high'),
            ('DST Rk', 'DSTFR', 'high'),
        ]
        all_lga_cols = lga_strength_cols + lga_continuity_cols + lga_fantasy_cols

        def lga_clean_num(v):
            if v is None:
                return None
            s = str(v).strip().replace('%', '').replace(',', '')
            if s.lower() in ('', 'nan', 'none', '—', '-'):
                return None
            try:
                return float(s)
            except Exception:
                return None

        def lga_clean_metric(col, v):
            if col == '2025 Wins':
                if v is None:
                    return None
                parts = str(v).strip().split('-')
                try:
                    wins_num = float(parts[0])
                    ties_num = float(parts[2]) if len(parts) > 2 else 0
                    return wins_num + (ties_num * 0.5)
                except Exception:
                    return lga_clean_num(v)
            return lga_clean_num(v)

        team_lga_metric_values = {}
        for _, r in Team_Info.iterrows():
            tm = str(r.get('Team', '')).strip()
            team_lga_metric_values[tm] = {col: lga_clean_metric(col, r.get(col)) for _, col, _ in all_lga_cols}

        lga_metric_ranges = {}
        for _, col, _ in all_lga_cols:
            vals = [v.get(col) for v in team_lga_metric_values.values() if v.get(col) is not None]
            lga_metric_ranges[col] = (min(vals), max(vals)) if vals else (0, 0)

        def lga_strength(team, col, direction):
            val = team_lga_metric_values.get(team, {}).get(col)
            lo, hi = lga_metric_ranges.get(col, (0, 0))
            if val is None or hi == lo:
                return None
            pct = (val - lo) / (hi - lo)
            if direction == 'low':
                pct = 1 - pct
            return max(0, min(1, pct))

        def lga_heat_color(score):
            if score is None:
                return '#f1f5f9', '#94a3b8'
            if score < 0.5:
                t = score / 0.5
                r = round(22 + (245 - 22) * t)
                g = round(163 + (158 - 163) * t)
                b = round(74 + (11 - 74) * t)
            else:
                t = (score - 0.5) / 0.5
                r = round(245 + (190 - 245) * t)
                g = round(158 + (24 - 158) * t)
                b = round(11 + (34 - 11) * t)
            fg = '#ffffff' if score > 0.70 else '#111827'
            return f'rgb({r},{g},{b})', fg

        def lga_fmt(v, col):
            if v is None:
                return '—'
            if 'Rank' in col:
                return f'{int(v)}'
            if col in ('Total', 'Offense', 'Defense', 'Special Teams'):
                return f'{v:.2f}%'
            if col in ('Vegas O/U', '2025 Wins'):
                return f'{v:.2f}'
            return f'{v:.2f}' if isinstance(v, (int, float)) else str(v)

        def lga_avg_fmt(v, col):
            if v is None:
                return '—'
            if col in ('Total', 'Offense', 'Defense', 'Special Teams'):
                return f'{v:.2f}%'
            if col in ('Vegas O/U', '2025 Wins'):
                return f'{v:.2f}'
            return f'{v:.2f}' if isinstance(v, (int, float)) else str(v)

        # ── Per-team SOS & game stats ────────────────────────────────────────
        team_sos_data = []
        all_games_for_top50 = []

        for tm in Team_Info['Team'].astype(str).str.strip().tolist():
            tm_games = analytics_games[(analytics_games['Home'] == tm) | (analytics_games['Away'] == tm)].copy()
            tm_games['_week_num'] = pd.to_numeric(tm_games['Week'], errors='coerce')
            tm_games['_date_num'] = pd.to_datetime(tm_games['Date'], errors='coerce')
            tm_games = tm_games.sort_values(['_week_num', '_date_num']).reset_index(drop=True)

            ou_vals = []
            rest_edges = []
            rest_adv_ct = 0
            rest_dis_ct = 0
            road_ct = 0
            pt_ct = 0
            intl_ct = 0
            q1_scores, q2_scores, q3_scores, q4_scores = [], [], [], []

            hardest_4_game_stretch = None
            hardest_4_idx = None
            hardest_4_score = -1

            for i, (_, tg) in enumerate(tm_games.iterrows()):
                opp = tg['Away'] if tg['Home'] == tm else tg['Home']
                wk_num = pd.to_numeric(tg.get('Week'), errors='coerce')

                opp_ou = team_lga_metric_values.get(opp, {}).get('Vegas O/U')
                if opp_ou is not None:
                    ou_vals.append(opp_ou)

                opp_scores = [lga_strength(opp, col, direction) for _, col, direction in lga_strength_cols]
                opp_scores = [s for s in opp_scores if s is not None]
                opp_strength = sum(opp_scores) / len(opp_scores) if opp_scores else None

                if pd.notna(wk_num) and opp_strength is not None:
                    if wk_num <= 4:
                        q1_scores.append(opp_strength)
                    elif wk_num <= 9:
                        q2_scores.append(opp_strength)
                    elif wk_num <= 14:
                        q3_scores.append(opp_strength)
                    else:
                        q4_scores.append(opp_strength)
                    all_games_for_top50.append({'team': tm, 'opponent': opp, 'week': wk_num, 'strength': opp_strength})

                tg_dt = pd.to_datetime(tg.get('Date'), errors='coerce')
                if tg['Home'] != tm:
                    road_ct += 1
                is_neutral = bool(tg.get('International', False)) if not isinstance(tg.get('International', False), float) else False
                if is_neutral:
                    intl_ct += 1
                if get_day_type(tg) != 'sunday':
                    pt_ct += 1

                prev_tg = tm_games[tm_games['_date_num'] < tg_dt]
                if len(prev_tg) > 0:
                    prev_dt = pd.to_datetime(prev_tg.iloc[-1].get('Date'), errors='coerce')
                    if pd.notna(prev_dt) and pd.notna(tg_dt):
                        tm_rest = int((tg_dt - prev_dt).days)
                        # Find opponent's previous game
                        opp_all_games = Games[(Games['Home'] == opp) | (Games['Away'] == opp)].copy()
                        opp_all_games['_opp_date'] = pd.to_datetime(opp_all_games['Date'], errors='coerce')
                        opp_prev_games = opp_all_games[opp_all_games['_opp_date'] < tg_dt]
                        if len(opp_prev_games) > 0:
                            opp_prev_dt = pd.to_datetime(opp_prev_games.iloc[-1].get('Date'), errors='coerce')
                            if pd.notna(opp_prev_dt):
                                opp_rest = int((tg_dt - opp_prev_dt).days)
                                rest_edge = tm_rest - opp_rest
                                rest_edges.append(rest_edge)
                                if rest_edge > 0:
                                    rest_adv_ct += 1
                                elif rest_edge < 0:
                                    rest_dis_ct += 1

            avg_ou = sum(ou_vals) / len(ou_vals) if ou_vals else None
            q1_avg = sum(q1_scores) / len(q1_scores) if q1_scores else None
            q2_avg = sum(q2_scores) / len(q2_scores) if q2_scores else None
            q3_avg = sum(q3_scores) / len(q3_scores) if q3_scores else None
            q4_avg = sum(q4_scores) / len(q4_scores) if q4_scores else None
            all_q_scores = q1_scores + q2_scores + q3_scores + q4_scores
            avg_sos = sum(all_q_scores) / len(all_q_scores) if all_q_scores else None

            total_sfi = None
            if all_q_scores:
                first_half_avg = (sum(q1_scores) + sum(q2_scores)) / (len(q1_scores) + len(q2_scores)) if (q1_scores or q2_scores) else None
                second_half_avg = (sum(q3_scores) + sum(q4_scores)) / (len(q3_scores) + len(q4_scores)) if (q3_scores or q4_scores) else None
                if first_half_avg is not None and second_half_avg is not None:
                    total_sfi = first_half_avg - second_half_avg

            net_rest = sum(rest_edges) if rest_edges else 0

            hardest_4_stretch_str = 'N/A'
            hardest_4_games = []
            easiest_4_games = []
            hardest_4_score = -1
            easiest_4_score = float('inf')
            for i in range(len(tm_games) - 3):
                window = tm_games.iloc[i:i+4]
                if len(window) == 4:
                    window_wks = window['Week'].astype(str)
                    window_opps = [row['Away'] if row['Home'] == tm else row['Home'] for _, row in window.iterrows()]
                    opp_strengths = []
                    for opp in window_opps:
                        scores = [lga_strength(opp, col, direction) for _, col, direction in lga_strength_cols]
                        scores = [s for s in scores if s is not None]
                        if scores:
                            opp_strengths.append(sum(scores) / len(scores))
                    if opp_strengths and len(opp_strengths) == 4:
                        avg_str = sum(opp_strengths) / 4
                        if avg_str > hardest_4_score:
                            hardest_4_score = avg_str
                            hardest_4_games = []
                            for j, (_, row) in enumerate(window.iterrows()):
                                opp = window_opps[j]
                                is_home = row['Home'] == tm
                                hardest_4_games.append({
                                    'week': pd.to_numeric(row['Week'], errors='coerce') if pd.notna(row['Week']) else None,
                                    'opponent': opp,
                                    'is_home': is_home,
                                    'strength': opp_strengths[j]
                                })
                        if avg_str < easiest_4_score:
                            easiest_4_score = avg_str
                            easiest_4_games = []
                            for j, (_, row) in enumerate(window.iterrows()):
                                opp = window_opps[j]
                                is_home = row['Home'] == tm
                                easiest_4_games.append({
                                    'week': pd.to_numeric(row['Week'], errors='coerce') if pd.notna(row['Week']) else None,
                                    'opponent': opp,
                                    'is_home': is_home,
                                    'strength': opp_strengths[j]
                                })

            opponent_metric_avgs = {}
            for _, col, _ in lga_strength_cols:
                opp_metric_vals = []
                for _, tg in tm_games.iterrows():
                    opp = tg['Away'] if tg['Home'] == tm else tg['Home']
                    opp_metric_val = team_lga_metric_values.get(opp, {}).get(col)
                    if opp_metric_val is not None:
                        opp_metric_vals.append(opp_metric_val)
                avg_opp_metric = sum(opp_metric_vals) / len(opp_metric_vals) if opp_metric_vals else None
                opponent_metric_avgs[col] = avg_opp_metric

            team_sos_data.append({
                'team': tm,
                'avg_sos': avg_sos,
                'avg_ou': avg_ou,
                'net_rest': net_rest,
                'rest_adv': rest_adv_ct,
                'rest_dis': rest_dis_ct,
                'road_games': road_ct,
                'primetime_games': pt_ct,
                'intl_games': intl_ct,
                'sfi': total_sfi,
                'q1': q1_avg,
                'q2': q2_avg,
                'q3': q3_avg,
                'q4': q4_avg,
                'hardest_4_games': hardest_4_games,
                'easiest_4_games': easiest_4_games,
                'opponent_metric_avgs': opponent_metric_avgs,
            })

        # Recalculate rank columns as actual 1-32 ranks based on averages
        metric_to_rank = {
            'Total': ('Total Rank', False),
            'Offense': ('Offensive Rank', False),
            'Defense': ('Defensive Rank', True),
            'Special Teams': ('Special Teams Rank', False)
        }
        for metric_col, (rank_col, reverse_rank) in metric_to_rank.items():
            teams_with_metric = [(d, d['opponent_metric_avgs'].get(metric_col)) for d in team_sos_data]
            teams_with_metric = [(d, val) for d, val in teams_with_metric if val is not None]
            sorted_teams = sorted(teams_with_metric, key=lambda x: x[1], reverse=True)
            if reverse_rank:
                sorted_teams.reverse()
            for rank_idx, (team_record, _) in enumerate(sorted_teams, 1):
                team_record['opponent_metric_avgs'][rank_col] = rank_idx

        # ── Build cards ──────────────────────────────────────────────────────
        league_game_count = 285

        analytics_games['_date_str'] = pd.to_datetime(analytics_games['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
        analytics_games['_time_str'] = analytics_games.get('Time (ET)', '').astype(str).str.strip()
        date_time_counts = analytics_games.groupby(['_date_str', '_time_str']).size()
        league_pt_count = len(analytics_games[analytics_games.apply(lambda r: date_time_counts.get((r['_date_str'], r['_time_str']), 0) == 1, axis=1)])

        league_intl_count = len(analytics_games[analytics_games['International'].apply(lambda v: bool(v) if not isinstance(v, float) else False)])

        # Count teams with 3 consecutive games where they're away OR international
        three_game_road_trips = 0
        for tm in Team_Info['Team'].astype(str).str.strip().tolist():
            tm_games = analytics_games[(analytics_games['Home'] == tm) | (analytics_games['Away'] == tm)].copy()
            tm_games['_week_num'] = pd.to_numeric(tm_games['Week'], errors='coerce')
            tm_games = tm_games.sort_values('_week_num').reset_index(drop=True)

            # Vectorized: mark road games (away OR international)
            tm_games['_is_road'] = ((tm_games['Home'] != tm) | (tm_games['International'].fillna(False).astype(bool))).astype(int)
            # Create groups that reset on home games, then count consecutive road games
            tm_games['_reset_group'] = (tm_games['_is_road'] == 0).cumsum()
            tm_games['_consecutive'] = tm_games.groupby('_reset_group')['_is_road'].cumsum()

            if (tm_games['_consecutive'] >= 3).any():
                three_game_road_trips += 1

        def lga_card(label, value, sub='', accent='#c8102e'):
            sub_html = f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#64748b;margin-top:3px;">{sub}</div>' if sub else ''
            return f'<div style="background:#fff;border:1px solid #e2e6ef;border-radius:8px;padding:16px 18px;box-shadow:0 1px 6px rgba(0,0,0,0.06);border-top:4px solid {accent};min-width:150px;flex:1;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:800;letter-spacing:3.5px;text-transform:uppercase;color:#94a3b8;margin-bottom:5px;">{label}</div><div style="font-family:\'Bebas Neue\',sans-serif;font-size:44px;color:#1a2030;line-height:1;">{value}</div>{sub_html}</div>'

        cards_html = '<div style="display:flex;gap:12px;margin:18px 0;flex-wrap:wrap;">'
        cards_html += lga_card('Total Games', f'{league_game_count:,}')
        cards_html += lga_card('Primetime Games', f'{league_pt_count:,}', 'stand-alone games')
        cards_html += lga_card('International Games', f'{league_intl_count:,}')
        cards_html += lga_card('3-Game Road Trips', f'{three_game_road_trips}', 'teams with 3 straight road games')
        cards_html += '</div>'

        # ── Build SOS rankings table ─────────────────────────────────────────
        sos_sorted = sorted([d for d in team_sos_data if d['avg_sos'] is not None], key=lambda d: d['avg_sos'], reverse=True)
        sos_rows = ''
        for rank, d in enumerate(sos_sorted, 1):
            tm = d['team']
            logo = lv_logo_map.get(tm, TBD_LOGO)
            accent = lv_clr_map.get(tm, '#374151')
            avg_sos = d['avg_sos']
            rest_adv = d['rest_adv']
            rest_dis = d['rest_dis']
            net_rest = d['net_rest']
            sos_bg, sos_fg = lga_heat_color(avg_sos)

            metric_cells = ''
            for _, col, direction in lga_strength_cols:
                val = d['opponent_metric_avgs'].get(col)
                if val is not None:
                    lo, hi = lga_metric_ranges.get(col, (0, 0))
                    if hi == lo:
                        score = None
                    else:
                        score = (val - lo) / (hi - lo)
                        if direction == 'low':
                            score = 1 - score
                        score = max(0, min(1, score))
                else:
                    score = None
                bg, fg = lga_heat_color(score)
                metric_cells += f'<td style="background:{bg};color:{fg};text-align:center;padding:9px 8px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-right:1px solid rgba(255,255,255,0.35);border-bottom:1px solid rgba(255,255,255,0.35);">{lga_fmt(val, col)}</td>'

            rest_adv_bg = '#dcfce7'
            rest_adv_fg = '#166534'
            rest_dis_bg = '#fee2e2'
            rest_dis_fg = '#991b1b'
            net_bg = '#dcfce7' if net_rest > 0 else '#fee2e2' if net_rest < 0 else '#f1f5f9'
            net_fg = '#166534' if net_rest > 0 else '#991b1b' if net_rest < 0 else '#64748b'

            sos_rows += f'<tr><td style="position:sticky;left:0;z-index:2;background:#fff;padding:10px 12px;border-bottom:1px solid #edf0f7;border-left:5px solid {accent};min-width:50px;text-align:center;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;color:#1a2030;">{rank}</td><td style="position:sticky;left:50px;z-index:2;background:#fff;padding:9px 12px;border-bottom:1px solid #edf0f7;min-width:210px;"><div style="display:flex;align-items:center;gap:10px;"><img src="{logo}" style="width:34px;height:34px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:800;color:#1a2030;line-height:1.05;">{tm}</div></div></td><td style="background:{sos_bg};color:{sos_fg};text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{f"{avg_sos*100:.0f}" if avg_sos else "—"}</td><td style="background:{rest_adv_bg};color:{rest_adv_fg};text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid rgba(255,255,255,0.35);">{rest_adv}</td><td style="background:{rest_dis_bg};color:{rest_dis_fg};text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid rgba(255,255,255,0.35);">{rest_dis}</td><td style="background:{net_bg};color:{net_fg};text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid rgba(255,255,255,0.35);">{net_rest:+d}</td>{metric_cells}</tr>'

        sos_avg_cells = ''
        for _, col, direction in lga_strength_cols:
            vals = [d['opponent_metric_avgs'].get(col) for d in sos_sorted]
            vals = [v for v in vals if v is not None]
            avg_val = sum(vals) / len(vals) if vals else None
            lo, hi = lga_metric_ranges.get(col, (0, 0))
            score = None if avg_val is None or hi == lo else (avg_val - lo) / (hi - lo)
            if score is not None and direction == 'low':
                score = 1 - score
            score = max(0, min(1, score)) if score is not None else None
            bg, fg = lga_heat_color(score)
            sos_avg_cells += f'<td style="background:{bg};color:{fg};text-align:center;padding:10px 8px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:900;border-top:2px solid #cbd5e1;">{lga_avg_fmt(avg_val, col)}</td>'

        sos_avg_sos_vals = [d['avg_sos'] for d in sos_sorted if d['avg_sos'] is not None]
        sos_avg_sos = sum(sos_avg_sos_vals) / len(sos_avg_sos_vals) if sos_avg_sos_vals else None
        sos_avg_bg, sos_avg_fg = lga_heat_color(sos_avg_sos)

        rest_adv_vals = [d['rest_adv'] for d in sos_sorted]
        rest_dis_vals = [d['rest_dis'] for d in sos_sorted]
        net_rest_vals = [d['net_rest'] for d in sos_sorted]
        avg_rest_adv = sum(rest_adv_vals) / len(rest_adv_vals) if rest_adv_vals else 0
        avg_rest_dis = sum(rest_dis_vals) / len(rest_dis_vals) if rest_dis_vals else 0
        avg_net_rest = sum(net_rest_vals) / len(net_rest_vals) if net_rest_vals else 0

        sos_rows += f'<tr><td style="position:sticky;left:0;z-index:2;background:#eef2f8;padding:11px 12px;border-top:2px solid #cbd5e1;border-left:5px solid #c8102e;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;color:#1a2030;">AVG</td><td style="position:sticky;left:50px;z-index:2;background:#eef2f8;padding:11px 12px;border-top:2px solid #cbd5e1;font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;color:#1a2030;letter-spacing:1px;text-transform:uppercase;">League Avg</td><td style="background:{sos_avg_bg};color:{sos_avg_fg};text-align:center;padding:10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-top:2px solid #cbd5e1;">{f"{sos_avg_sos*100:.0f}" if sos_avg_sos else "—"}</td><td style="background:#eef2f8;color:#64748b;text-align:center;padding:10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-top:2px solid #cbd5e1;">{avg_rest_adv:.1f}</td><td style="background:#eef2f8;color:#64748b;text-align:center;padding:10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-top:2px solid #cbd5e1;">{avg_rest_dis:.1f}</td><td style="background:#eef2f8;color:#64748b;text-align:center;padding:10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-top:2px solid #cbd5e1;">{avg_net_rest:+.1f}</td>{sos_avg_cells}</tr>'

        sos_col_headers = ''.join(f'<th style="padding:9px 8px;min-width:74px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">{short}</th>' for short, _, _ in lga_strength_cols)

        sos_table_html = (
            f'<div style="margin-top:18px;"><div style="margin:0 0 8px;">'
            f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;'
            f'letter-spacing:4px;text-transform:uppercase;color:#c8102e;">Schedule Strength Rankings</div>'
            f'<div style="font-family:\'Barlow\',sans-serif;font-size:13px;color:#64748b;margin-top:3px;'
            f'line-height:1.45;">Average opponent metrics across all 17 opponents, with rest advantage/disadvantage. '
            f'Columns show opponents\' strength (O/U, Wins, DVOA, etc.), not team\'s own metrics. '
            f'Sorted hardest to easiest schedule.</div></div>'
            f'<div style="overflow-x:auto;overflow-y:visible;border:1px solid #dfe5ef;border-radius:10px;'
            f'background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table id="lga-sos-table" '
            f'style="border-collapse:separate;border-spacing:0;width:100%;min-width:1100px;"><thead><tr '
            f'style="background:#f8fafc;"><th style="position:sticky;left:0;top:0;z-index:4;'
            f'background:#f8fafc;padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;'
            f'font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;'
            f'border-bottom:1px solid #e2e6ef;min-width:50px;">Rank</th><th style="position:sticky;left:50px;'
            f'top:0;z-index:4;background:#f8fafc;padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;'
            f'font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;'
            f'text-align:left;border-bottom:1px solid #e2e6ef;">Team</th><th style="padding:9px 8px;'
            f'min-width:74px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;'
            f'letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">'
            f'Index</th><th style="padding:9px 8px;min-width:80px;font-family:\'Barlow Condensed\',sans-serif;'
            f'font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;'
            f'text-align:center;border-bottom:1px solid #e2e6ef;">Adv</th><th style="padding:9px 8px;'
            f'min-width:80px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;'
            f'letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">'
            f'Dis</th><th style="padding:9px 8px;min-width:80px;font-family:\'Barlow Condensed\',sans-serif;'
            f'font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;'
            f'text-align:center;border-bottom:1px solid #e2e6ef;">Net</th>{sos_col_headers}</tr></thead>'
            f'<tbody>{sos_rows}</tbody></table></div></div>'
        )

        # ── Build SFI (Schedule Frontloading Index) table ─────────────────────
        sfi_data = [d for d in team_sos_data if d['sfi'] is not None]
        sfi_sorted = sorted(sfi_data, key=lambda d: d['sfi'], reverse=True)
        sfi_rows = ''

        for rank, d in enumerate(sfi_sorted, 1):
            tm = d['team']
            logo = lv_logo_map.get(tm, TBD_LOGO)
            accent = lv_clr_map.get(tm, '#374151')
            sfi = d['sfi']
            q1 = d['q1']
            q2 = d['q2']
            q3 = d['q3']
            q4 = d['q4']
            sfi_norm = (sfi + 1) / 2 if sfi is not None else None
            sfi_norm = max(0, min(1, sfi_norm)) if sfi_norm is not None else None
            sfi_bg, sfi_fg = lga_heat_color(sfi_norm)

            verdict = 'FRONTLOADED' if sfi and sfi > 0.08 else 'BACKLOADED' if sfi and sfi < -0.08 else 'EVEN'
            verdict_color = '#be1822' if sfi and sfi > 0.08 else '#16a34a' if sfi and sfi < -0.08 else '#64748b'

            sfi_rows += f'<tr><td style="position:sticky;left:0;z-index:2;background:#fff;padding:10px 12px;border-bottom:1px solid #edf0f7;border-left:5px solid {accent};min-width:50px;text-align:center;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;color:#1a2030;">{rank}</td><td style="position:sticky;left:50px;z-index:2;background:#fff;padding:9px 12px;border-bottom:1px solid #edf0f7;min-width:210px;"><div style="display:flex;align-items:center;gap:10px;"><img src="{logo}" style="width:34px;height:34px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:800;color:#1a2030;line-height:1.05;">{tm}</div></div></td><td style="background:{sfi_bg};color:{sfi_fg};text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{f"{sfi:+.2f}" if sfi else "—"}</td><td style="background:#f1f5f9;color:#64748b;text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid #edf0f7;">{f"{q1*100:.0f}" if q1 else "—"}</td><td style="background:#f1f5f9;color:#64748b;text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid #edf0f7;">{f"{q2*100:.0f}" if q2 else "—"}</td><td style="background:#f1f5f9;color:#64748b;text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid #edf0f7;">{f"{q3*100:.0f}" if q3 else "—"}</td><td style="background:#f1f5f9;color:#64748b;text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;border-bottom:1px solid #edf0f7;">{f"{q4*100:.0f}" if q4 else "—"}</td><td style="background:#fff;color:{verdict_color};text-align:center;padding:9px 10px;font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:2px;text-transform:uppercase;border-bottom:1px solid #edf0f7;">{verdict}</td></tr>'

        sfi_table_html = f'<div style="margin-top:18px;"><div style="margin:0 0 8px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:#c8102e;">Schedule Frontloading Index (SFI)</div><div style="font-family:\'Barlow\',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">Opponent strength by quarter. Total SFI compares Q1-Q2 (first half) vs Q3-Q4 (second half). Positive = harder early; negative = harder late.</div></div><div style="overflow-x:auto;overflow-y:visible;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table id="lga-sfi-table" style="border-collapse:separate;border-spacing:0;width:100%;min-width:900px;"><thead><tr style="background:#f8fafc;"><th style="position:sticky;left:0;top:0;z-index:4;background:#f8fafc;padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:50px;">Rank</th><th style="position:sticky;left:50px;top:0;z-index:4;background:#f8fafc;padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;">Team</th><th style="padding:9px 8px;min-width:90px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">SFI</th><th style="padding:9px 8px;min-width:75px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Q1 (1-4)</th><th style="padding:9px 8px;min-width:75px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Q2 (5-9)</th><th style="padding:9px 8px;min-width:75px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Q3 (10-14)</th><th style="padding:9px 8px;min-width:75px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Q4 (15-18)</th><th style="padding:9px 8px;min-width:120px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Verdict</th></tr></thead><tbody>{sfi_rows}</tbody></table></div></div>'

        # ── All Games Table (Part C) ─────────────────────────────────────────
        all_games_copy = Games.copy()
        all_games_copy['_week_num'] = pd.to_numeric(all_games_copy['Week'], errors='coerce')
        all_games_copy['_date_dt'] = pd.to_datetime(all_games_copy['Date'], errors='coerce')

        known_games = all_games_copy[all_games_copy['_week_num'].notna()].copy()
        known_games = known_games.sort_values(['_week_num', '_date_dt']).reset_index(drop=True)

        tba_games = all_games_copy[all_games_copy['_week_num'].isna()].copy()
        game_type_priority = {'Regular Season': 0, 'Preseason': 1, 'Playoff': 2, 'Super Bowl': 3}
        tba_games['_type_priority'] = tba_games['Game Type'].apply(lambda x: game_type_priority.get(str(x).strip(), 999))
        tba_games = tba_games.sort_values(['_type_priority', 'Away']).reset_index(drop=True)

        all_games_rows_html = ''
        current_week_header = None

        for _, g in pd.concat([known_games, tba_games], ignore_index=True).iterrows():
            wk_raw = g.get('Week', '')
            try:
                wk_numeric = pd.to_numeric(wk_raw, errors='coerce')
                if pd.notna(wk_numeric):
                    if wk_numeric == 18.5:
                        wk_val = 'TBD'
                        wk_label = 'Week TBD'
                    else:
                        wk_val = wk_numeric if wk_numeric != int(wk_numeric) else int(wk_numeric)
                        wk_label = f'Week {wk_val}'
                else:
                    wk_val = None
                    wk_label = 'TBA'
            except Exception:
                wk_val = None
                wk_label = 'TBA'

            if wk_label != current_week_header:
                current_week_header = wk_label
                if wk_val is not None:
                    header_style = 'background:#eef2f8;border-top:1px solid #dde2ed;border-bottom:1px solid #dde2ed;'
                    fg = '#64748b'
                else:
                    header_style = 'background:#0b0f19;border-top:1px solid #111827;border-bottom:1px solid #111827;'
                    fg = '#fff'
                all_games_rows_html += f'<tr style="{header_style}"><td style="width:5px;padding:0;background:{"#1a2030" if wk_val else "#c8102e"};"></td><td colspan="7" style="padding:8px 14px;font-family:\'Barlow Condensed\',sans-serif;font-size:12px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:{fg};">{wk_label}</td></tr>'

            home = g['Home']
            away = g['Away']
            home_abb = lv_abb_map.get(home, str(home)[:3].upper())
            away_abb = lv_abb_map.get(away, str(away)[:3].upper())
            home_logo = lv_logo_map.get(home, TBD_LOGO)
            away_logo = lv_logo_map.get(away, TBD_LOGO)
            home_clr = lv_clr_map.get(home, '#374151')

            try:
                dt_label = pd.to_datetime(g.get('Date')).strftime('%a, %b %-d')
            except Exception:
                try:
                    dt_label = pd.to_datetime(g.get('Date')).strftime('%a, %b %#d')
                except Exception:
                    dt_label = str(g.get('Date', 'TBD'))

            time_et = str(g.get('Time (ET)', '') or '').strip()
            if time_et.lower() in ('', 'nan'):
                time_et = 'TBD'

            tv = str(g.get('TV Network', '') or '').strip()
            if tv.lower() in ('', 'nan'):
                tv = ''
            # TV badge - use logo if available, otherwise use text
            if tv:
                tv_logo_url = TV_LOGO_MAP.get(tv, '')
                if tv_logo_url:
                    tv_badge = f'<img src="{tv_logo_url}" style="max-height:55px;max-width:160px;object-fit:contain;" onerror="this.style.display=\'none\';">'
                else:
                    tv_badge = f'<span style="font-family:\'Barlow Condensed\',sans-serif;font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;background:#e5e7eb;color:#374151;padding:3px 8px;border-radius:3px;display:inline-block;">{tv}</span>'
            else:
                tv_badge = ''

            game_type = str(g.get('Game Type', '') or '').strip()
            if game_type.lower() in ('', 'nan', 'none'):
                game_type = 'Regular Season'

            loc = str(g.get('Location', '') or '').strip()
            if not loc:
                loc = 'TBD'

            all_games_rows_html += f'<tr style="background:#ffffff;border-bottom:1px solid #edf0f7;"><td style="width:5px;padding:0;background:{home_clr};"></td><td style="padding:10px 12px;font-family:\'Rajdhani\',sans-serif;font-size:13px;font-weight:800;color:#64748b;min-width:90px;">{dt_label}</td><td style="padding:10px 12px;font-family:\'Rajdhani\',sans-serif;font-size:13px;color:#64748b;min-width:60px;">{time_et}</td><td style="padding:10px 12px;min-width:140px;"><div style="display:flex;align-items:center;gap:8px;"><img src="{away_logo}" style="width:28px;height:28px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><span style="font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;color:#1a2030;">{away_abb}</span></div></td><td style="padding:10px 12px;text-align:center;font-family:\'Barlow Condensed\',sans-serif;font-size:13px;color:#64748b;">@</td><td style="padding:10px 12px;min-width:140px;"><div style="display:flex;align-items:center;gap:8px;"><img src="{home_logo}" style="width:28px;height:28px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><span style="font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;color:#1a2030;">{home_abb}</span></div></td><td style="padding:10px 12px;min-width:180px;font-family:\'Barlow\',sans-serif;font-size:12px;color:#64748b;">{game_type}</td><td style="padding:10px 12px;min-width:120px;">{tv_badge}</td></tr>'

        all_games_table_html = f'<div style="margin-top:18px;"><div style="margin:0 0 8px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:#c8102e;">All Games ({len(all_games_copy)} total)</div><div style="font-family:\'Barlow\',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">Complete game schedule including TBA matchups and dates.</div></div><div style="overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;min-width:800px;"><thead><tr style="background:#f8fafc;"><th style="width:5px;background:#f8fafc;"></th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;min-width:90px;">Date</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;min-width:60px;">Time</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;min-width:140px;">Away</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;width:30px;"></th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;min-width:140px;">Home</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;min-width:180px;">Type</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;min-width:120px;">TV</th></tr></thead><tbody>{all_games_rows_html}</tbody></table></div></div>'

        # ── Render everything ────────────────────────────────────────────────
        legend_html = f'<div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:10px 0 14px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:12px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#64748b;">Opponent metric heat map (SOS Index)</div><div style="display:flex;align-items:center;gap:8px;"><span style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#64748b;">Easier</span><div style="width:170px;height:12px;border-radius:3px;background:linear-gradient(90deg,#16a34a 0%,#f59e0b 50%,#be1822 100%);border:1px solid #d7deea;"></div><span style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#64748b;">Harder</span></div></div>'

        # ── Rest Advantage/Disadvantage Table ────────────────────────────────
        rest_sorted = sorted(team_sos_data, key=lambda d: d['rest_adv'] - d['rest_dis'], reverse=True)
        rest_rows = ''
        for rank, d in enumerate(rest_sorted, 1):
            tm = d['team']
            logo = lv_logo_map.get(tm, TBD_LOGO)
            accent = lv_clr_map.get(tm, '#374151')
            rest_adv = d['rest_adv']
            rest_dis = d['rest_dis']
            net = d['net_rest']
            rest_rows += f'<tr><td style="position:sticky;left:0;z-index:2;background:#fff;padding:10px 12px;border-bottom:1px solid #edf0f7;border-left:5px solid {accent};min-width:50px;text-align:center;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;color:#1a2030;">{rank}</td><td style="position:sticky;left:50px;z-index:2;background:#fff;padding:9px 12px;border-bottom:1px solid #edf0f7;min-width:210px;"><div style="display:flex;align-items:center;gap:10px;"><img src="{logo}" style="width:34px;height:34px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:800;color:#1a2030;line-height:1.05;">{tm}</div></div></td><td style="background:#dcfce7;color:#166534;text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{rest_adv}</td><td style="background:#fee2e2;color:#991b1b;text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{rest_dis}</td><td style="background:{"#dcfce7" if net > 0 else "#fee2e2" if net < 0 else "#f1f5f9"};color:{"#166534" if net > 0 else "#991b1b" if net < 0 else "#64748b"};text-align:center;padding:9px 10px;font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{net:+d}</td></tr>'

        rest_table_html = f'<div style="margin-top:18px;"><div style="margin:0 0 8px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:#c8102e;">Rest Advantage / Disadvantage</div><div style="font-family:\'Barlow\',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">Games where team had more rest (advantage) vs less rest (disadvantage) than opponent. Net = cumulative rest days vs opponents.</div></div><div style="overflow-x:auto;overflow-y:visible;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table id="lga-rest-table" style="border-collapse:separate;border-spacing:0;width:100%;min-width:800px;"><thead><tr style="background:#f8fafc;"><th style="position:sticky;left:0;top:0;z-index:4;background:#f8fafc;padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:50px;">Rank</th><th style="position:sticky;left:50px;top:0;z-index:4;background:#f8fafc;padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;">Team</th><th style="padding:9px 8px;min-width:90px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Adv Games</th><th style="padding:9px 8px;min-width:90px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Dis Games</th><th style="padding:9px 8px;min-width:90px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Net Rest</th></tr></thead><tbody>{rest_rows}</tbody></table></div></div>'

        # ── Hardest 4-Game Stretch Table ──────────────────────────────────────
        hardest_data = []
        for d in team_sos_data:
            tm = d['team']
            logo = lv_logo_map.get(tm, TBD_LOGO)
            accent = lv_clr_map.get(tm, '#374151')
            hardest_4_games = d['hardest_4_games']

            if hardest_4_games:
                difficulty_scores = [g['strength'] for g in hardest_4_games]
                avg_difficulty = sum(difficulty_scores) / len(difficulty_scores) if difficulty_scores else 0

                hardest_data.append({
                    'team': tm,
                    'logo': logo,
                    'accent': accent,
                    'games': hardest_4_games,
                    'difficulty': avg_difficulty
                })

        hardest_data_sorted = sorted(hardest_data, key=lambda x: x['difficulty'], reverse=True)

        def build_hardest_table(teams_data, start_rank):
            rows = ''
            for rank, d in enumerate(teams_data, start_rank):
                tm = d['team']
                logo = d['logo']
                accent = d['accent']
                hardest_4_games = d['games']
                avg_difficulty = d['difficulty']

                start_wk = hardest_4_games[0]['week']
                end_wk = hardest_4_games[-1]['week']
                week_range = f'Week {start_wk}-{end_wk}' if start_wk and end_wk else 'TBA'

                diff_bg, diff_fg = lga_heat_color(avg_difficulty)

                team_cell = f'<td style="position:sticky;left:0;z-index:2;padding:14px;border-bottom:1px solid #edf0f7;border-left:5px solid {accent};background:#fff;"><div style="display:flex;align-items:center;gap:10px;"><div style="font-family:\'Rajdhani\',sans-serif;font-size:22px;font-weight:900;color:#64748b;min-width:30px;">{rank}</div><img src="{logo}" style="width:36px;height:36px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:16px;font-weight:800;color:#1a2030;line-height:1.05;">{tm}</div></div></td>'

                week_cell = f'<td style="padding:14px;border-bottom:1px solid #edf0f7;font-family:\'Rajdhani\',sans-serif;font-size:15px;font-weight:800;color:#1a2030;text-align:center;min-width:100px;">{week_range}</td>'

                games_html = '<div style="display:flex;gap:6px;align-items:center;">'
                for g in hardest_4_games:
                    opp = g['opponent']
                    opp_logo = lv_logo_map.get(opp, TBD_LOGO)
                    opp_abb = lv_abb_map.get(opp, opp[:3].upper())
                    vs_at = '@' if not g['is_home'] else 'vs'
                    games_html += f'<div style="display:flex;flex-direction:column;align-items:center;gap:3px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:12px;color:#94a3b8;font-weight:700;">{vs_at}</div><img src="{opp_logo}" style="width:32px;height:32px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><span style="font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;color:#1a2030;">{opp_abb}</span></div>'
                games_html += '</div>'

                games_cell = f'<td style="padding:12px;border-bottom:1px solid #edf0f7;text-align:center;">{games_html}</td>'

                index_cell = f'<td style="background:{diff_bg};color:{diff_fg};padding:14px;border-bottom:1px solid rgba(255,255,255,0.35);font-family:\'Rajdhani\',sans-serif;font-size:18px;font-weight:900;text-align:center;min-width:80px;">{f"{avg_difficulty*100:.0f}"}</td>'

                rows += f'<tr>{team_cell}{week_cell}{games_cell}{index_cell}</tr>'
            return rows

        left_16_rows = build_hardest_table(hardest_data_sorted[:16], 1)
        right_16_rows = build_hardest_table(hardest_data_sorted[16:32], 17)

        table_header = '<thead><tr style="background:#f8fafc;"><th style="position:sticky;left:0;top:0;z-index:4;padding:12px;font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;background:#f8fafc;">Team</th><th style="padding:12px;font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:100px;">Weeks</th><th style="padding:12px;font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Opponents</th><th style="padding:12px;font-family:\'Barlow Condensed\',sans-serif;font-size:13px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:80px;">Index</th></tr></thead>'

        hardest_table_html = f'<div style="margin-top:18px;"><div style="margin:0 0 12px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:#c8102e;">Hardest 4-Game Stretch</div><div style="font-family:\'Barlow\',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">Toughest consecutive 4-game sequence by opponent strength. Each team shows their hardest 4-game window with week range and opponent matchups.</div></div><div style="display:flex;gap:12px;"><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{left_16_rows}</tbody></table></div><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{right_16_rows}</tbody></table></div></div></div>'

        # ── Easiest 4-Game Stretch Table ──────────────────────────────────────
        easiest_data = []
        for d in team_sos_data:
            tm = d['team']
            logo = lv_logo_map.get(tm, TBD_LOGO)
            accent = lv_clr_map.get(tm, '#374151')
            easiest_4_games = d['easiest_4_games']

            if easiest_4_games:
                difficulty_scores = [g['strength'] for g in easiest_4_games]
                avg_difficulty = sum(difficulty_scores) / len(difficulty_scores) if difficulty_scores else 0

                easiest_data.append({
                    'team': tm,
                    'logo': logo,
                    'accent': accent,
                    'games': easiest_4_games,
                    'difficulty': avg_difficulty
                })

        easiest_data_sorted = sorted(easiest_data, key=lambda x: x['difficulty'])
        left_16_easiest = build_hardest_table(easiest_data_sorted[:16], 1)
        right_16_easiest = build_hardest_table(easiest_data_sorted[16:32], 17)

        easiest_table_html = f'<div style="margin-top:18px;"><div style="margin:0 0 12px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:#c8102e;">Easiest 4-Game Stretch</div><div style="font-family:\'Barlow\',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">Easiest consecutive 4-game sequence by opponent strength. Each team shows their easiest 4-game window with week range and opponent matchups.</div></div><div style="display:flex;gap:12px;"><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{left_16_easiest}</tbody></table></div><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{right_16_easiest}</tbody></table></div></div></div>'

        # ── Top 50 Games (Bidirectional Strength) ────────────────────────────
        top_games = []
        games_processed = set()

        # Convert all_games_for_top50 to dict for fast lookup
        strength_dict = {}
        for g in all_games_for_top50:
            key = (g['team'], g['opponent'], g['week'])
            strength_dict[key] = g['strength']

        for _, orig_game in analytics_games.iterrows():
            away = orig_game['Away']
            home = orig_game['Home']
            wk = pd.to_numeric(orig_game['Week'], errors='coerce') if pd.notna(orig_game['Week']) else 0

            game_key = tuple(sorted([away, home, str(wk)]))
            if game_key in games_processed:
                continue
            games_processed.add(game_key)

            away_strength = strength_dict.get((away, home, wk))
            home_strength = strength_dict.get((home, away, wk))

            if away_strength is None or home_strength is None:
                continue

            combined_strength = (away_strength + home_strength) / 2

            weaker_strength = min(away_strength, home_strength)
            weaker_is_home = home_strength < away_strength

            home_field_bonus = 1.05 if weaker_is_home else 1.0
            adjusted_strength = combined_strength * home_field_bonus

            late_season_weight = 1.5 if wk > 13 else 1.2 if wk > 9 else 1.0
            weighted_strength = adjusted_strength * late_season_weight

            top_games.append({
                'week': wk,
                'away': away,
                'home': home,
                'combined': combined_strength,
                'weighted': weighted_strength,
            })

        top_games_sorted = sorted(top_games, key=lambda g: g['weighted'], reverse=True)[:75]

        def build_games_table(games, start_rank):
            rows = ''
            for rank, g in enumerate(games, start_rank):
                away = g['away']
                home = g['home']
                wk = g['week'] if pd.notna(g['week']) else 0
                wk_display = 'TBD' if wk == 18.5 else (str(wk if wk != int(wk) else int(wk)))
                weighted = g['weighted']
                away_abb = lv_abb_map.get(away, away[:3].upper())
                home_abb = lv_abb_map.get(home, home[:3].upper())
                away_logo = lv_logo_map.get(away, TBD_LOGO)
                home_logo = lv_logo_map.get(home, TBD_LOGO)
                weighted_norm = min(1.0, weighted / 1.5)
                weight_bg, weight_fg = lga_heat_color(weighted_norm)
                rows += f'<tr><td style="padding:10px 12px;border-bottom:1px solid #edf0f7;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;color:#1a2030;text-align:center;min-width:50px;">{rank}</td><td style="padding:10px 12px;border-bottom:1px solid #edf0f7;font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:800;color:#1a2030;text-align:center;min-width:60px;">Wk {wk_display}</td><td style="padding:8px 10px;border-bottom:1px solid #edf0f7;"><div style="display:flex;align-items:center;gap:6px;"><div style="display:flex;align-items:center;gap:3px;"><img src="{away_logo}" style="width:24px;height:24px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><span style="font-family:\'Barlow Condensed\',sans-serif;font-size:12px;font-weight:800;color:#1a2030;">{away_abb}</span></div><span style="font-family:\'Barlow Condensed\',sans-serif;font-size:11px;color:#94a3b8;">@</span><div style="display:flex;align-items:center;gap:3px;"><img src="{home_logo}" style="width:24px;height:24px;object-fit:contain;" onerror="this.onerror=null;this.src=\'{TBD_LOGO}\';"><span style="font-family:\'Barlow Condensed\',sans-serif;font-size:12px;font-weight:800;color:#1a2030;">{home_abb}</span></div></div></td><td style="background:{weight_bg};color:{weight_fg};padding:10px 12px;border-bottom:1px solid rgba(255,255,255,0.35);font-family:\'Rajdhani\',sans-serif;font-size:16px;font-weight:900;text-align:center;min-width:70px;">{f"{weighted*100:.0f}"}</td></tr>'
            return rows

        top25_rows = build_games_table(top_games_sorted[:25], 1)
        mid25_rows = build_games_table(top_games_sorted[25:50], 26)
        bottom25_rows = build_games_table(top_games_sorted[50:75], 51)

        table_header = '<thead><tr style="background:#f8fafc;"><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:50px;">Rank</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:60px;">Week</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;">Matchup</th><th style="padding:10px 12px;font-family:\'Barlow Condensed\',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;min-width:70px;">Index</th></tr></thead>'

        top_games_table_html = f'<div style="margin-top:18px;"><div style="margin:0 0 12px;"><div style="font-family:\'Barlow Condensed\',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;text-transform:uppercase;color:#c8102e;">Top 75 Biggest Potential Games</div><div style="font-family:\'Barlow\',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">Highest matchup strength based on combined team metrics. Weaker team at home gets 5% bonus. Late-season weighting: 1.5x weeks 14+, 1.2x weeks 10-13. Index shown includes all adjustments.</div></div><div style="display:flex;gap:12px;"><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{top25_rows}</tbody></table></div><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{mid25_rows}</tbody></table></div><div style="flex:1;overflow-x:auto;border:1px solid #dfe5ef;border-radius:10px;background:#fff;box-shadow:0 2px 12px rgba(15,23,42,0.08);"><table style="border-collapse:collapse;width:100%;"><tbody>{table_header}<tbody>{bottom25_rows}</tbody></table></div></div></div>'

        st.html(f"""{sort_script}{ANALYTICS_RELEASE_NOTE}{cards_html}{sos_table_html}{legend_html}{sfi_table_html}{hardest_table_html}{easiest_table_html}{top_games_table_html}""")

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
        bye_int = int(float(bye_wk)) if bye_wk and str(bye_wk).strip() not in ('', 'nan') else None
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

    tot = f'{float(tot):.1f}%' if tot != '—' and isinstance(tot, (int, float)) else tot
    off = f'{float(off):.1f}%' if off != '—' and isinstance(off, (int, float)) else off
    deff = f'{float(deff):.1f}%' if deff != '—' and isinstance(deff, (int, float)) else deff
    st_dvoa = f'{float(st_dvoa):.1f}%' if st_dvoa != '—' and isinstance(st_dvoa, (int, float)) else st_dvoa

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
      {div}
    </div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:62px;letter-spacing:3px;
         color:{fg1};line-height:0.95;margin-bottom:14px;">
      {team_name.upper()}
    </div>
    <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center;">
      {stat_block('O/U', ou)}
      {divider}
      {stat_block('Record', wins)}
      {divider}
      {stat_block('DVOA', tot, f'#{tot_r}')}
      {divider}
      {stat_block('O. DVOA', off, f'#{off_r}')}
      {divider}
      {stat_block('D. DVOA', deff, f'#{def_r}')}
      {divider}
      {stat_block('S.T. DVOA', st_dvoa, f'#{st_r}')}
      {bye_block}
    </div>
  </div>
  <img src="{wm}"
       style="height:52px;max-width:200px;object-fit:contain;opacity:0.9;flex-shrink:0;
              filter:{wm_filter};"
       onerror="this.style.display='none'">
</div>""")

    # ── Sub-tabs ──────────────────────────────────────────────────────────────
    sub_tabs = st.tabs(["📅  Schedule", "✈️  Travel", "📊  Analytics"])

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
            team_games['_week_num'] = pd.to_numeric(team_games['Week'], errors='coerce')
            team_games = team_games.sort_values(
                ['_is_non_reg', '_post_order', '_week_num', '_ha_sort', '_opp_sort'],
                na_position='last'
            ).reset_index(drop=True)
            wk_iter = [None]
        else:
            max_wk_val = pd.to_numeric(Games['Week'], errors='coerce').max()
            max_wk = max(int(max_wk_val), 18) if pd.notna(max_wk_val) else 18
            wk_iter = range(1, max_wk + 1)
        rows_html = ''
        current_game_type = None

        if tba_week_mode and bye_int is not None:
            rows_html += f"""
<tr style="background:#f8fafc;border-bottom:1px solid #edf0f7;">
  <td style="width:5px;background:#e2e6ef;"></td>
  <td style="padding:10px 8px 10px 12px;text-align:center;vertical-align:middle;">
    <div style="width:34px;height:34px;border-radius:50%;background:#e2e6ef;color:#b0baca;
         display:inline-flex;align-items:center;justify-content:center;
         font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:800;">{bye_int}</div>
  </td>
  <td colspan="5" style="padding:12px 16px;vertical-align:middle;">
    <span style="font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:800;
         letter-spacing:5px;text-transform:uppercase;color:#c8d2e0;">— BYE WEEK —</span>
  </td>
</tr>"""

        for wk in wk_iter:
            wk_rows = team_games if tba_week_mode else team_games[team_week_num == wk]

            if len(wk_rows) == 0:
                if bye_int is not None and wk == bye_int:
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

                # TV badge - use logo if available, otherwise use text
                if tv:
                    tv_logo_url = TV_LOGO_MAP.get(tv, '')
                    if tv_logo_url:
                        tv_badge = f'<img src="{tv_logo_url}" style="max-height:65px;max-width:200px;object-fit:contain;" onerror="this.style.display=\'none\';">'
                    else:
                        tv_badge = (
                            f'<span style="background:#f1f5f9;color:#475569;font-family:\'Barlow Condensed\','
                            f'sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;padding:3px 10px;'
                            f'border-radius:3px;border:1px solid #dde2ed;white-space:nowrap;">{tv}</span>'
                        )
                else:
                    tv_badge = ''

                location_html = (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:700;color:#2a3550;line-height:1.2;">{stad}</div>'
                    f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#9aa5be;margin-top:1px;">{loc_disp}</div>'
                ) if stad else (
                    f'<div style="font-family:\'Barlow Condensed\',sans-serif;font-size:17px;'
                    f'font-weight:600;color:#4a5a78;">{loc_disp}</div>'
                )
                wk_num = pd.to_numeric(g.get('Week'), errors='coerce')
                if pd.notna(wk_num):
                    if wk_num == 18.5:
                        wk_badge = 'TBD'
                    else:
                        wk_badge = str(wk_num if wk_num != int(wk_num) else int(wk_num))
                else:
                    wk_badge = 'TBA'

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
    with sub_tabs[2]:
        strength_metric_cols = [
            ('O/U', 'Vegas O/U', 'high'),
            ('2025 W', '2025 Wins', 'high'),
            ('DVOA', 'Total', 'high'),
            ('DVOA Rk', 'Total Rank', 'low'),
            ('Off', 'Offense', 'high'),
            ('Off Rk', 'Offensive Rank', 'low'),
            ('Def', 'Defense', 'low'),
            ('Def Rk', 'Defensive Rank', 'low'),
            ('ST', 'Special Teams', 'high'),
            ('ST Rk', 'Special Teams Rank', 'low'),
        ]
        continuity_metric_cols = [
            ('QB', 'QB Tenure', 'high'),
            ('HC', 'HC Tenure', 'high'),
            ('OC', 'OC Tenure', 'high'),
            ('DC', 'DC Tenure', 'high'),
            ('SC', 'SC Tenure', 'high'),
        ]
        fantasy_metric_cols = [
            ('QB', 'QBF', 'high'),
            ('QB Rk', 'QBFR', 'high'),
            ('RB', 'RBF', 'high'),
            ('RB Rk', 'RBFR', 'high'),
            ('WR', 'WRF', 'high'),
            ('WR Rk', 'WRFR', 'high'),
            ('TE', 'TEF', 'high'),
            ('TE Rk', 'TEFR', 'high'),
            ('K', 'KF', 'high'),
            ('K Rk', 'KFR', 'high'),
            ('DST', 'DSTF', 'high'),
            ('DST Rk', 'DSTFR', 'high'),
        ]
        all_metric_cols = strength_metric_cols + continuity_metric_cols + fantasy_metric_cols
        metric_cols = all_metric_cols

        def ana_clean_num(v):
            if v is None:
                return None
            s = str(v).strip().replace('%', '').replace(',', '')
            if s.lower() in ('', 'nan', 'none', '—', '-'):
                return None
            try:
                return float(s)
            except Exception:
                return None

        def ana_clean_metric(col, v):
            if col == '2025 Wins':
                if v is None:
                    return None
                parts = str(v).strip().split('-')
                try:
                    wins_num = float(parts[0])
                    ties_num = float(parts[2]) if len(parts) > 2 else 0
                    return wins_num + (ties_num * 0.5)
                except Exception:
                    return ana_clean_num(v)
            return ana_clean_num(v)

        team_metric_values = {}
        for _, r in Team_Info.iterrows():
            tm = str(r.get('Team', '')).strip()
            team_metric_values[tm] = {col: ana_clean_metric(col, r.get(col)) for _, col, _ in all_metric_cols}

        metric_ranges = {}
        for _, col, _ in all_metric_cols:
            vals = [v.get(col) for v in team_metric_values.values() if v.get(col) is not None]
            metric_ranges[col] = (min(vals), max(vals)) if vals else (0, 0)

        def ana_strength(team, col, direction):
            val = team_metric_values.get(team, {}).get(col)
            lo, hi = metric_ranges.get(col, (0, 0))
            if val is None or hi == lo:
                return None
            pct = (val - lo) / (hi - lo)
            if direction == 'low':
                pct = 1 - pct
            return max(0, min(1, pct))

        def ana_heat_color(score):
            if score is None:
                return '#f1f5f9', '#94a3b8'
            # Green -> gold -> red, where red means a tougher opponent for that column.
            if score < 0.5:
                t = score / 0.5
                r = round(22 + (245 - 22) * t)
                g = round(163 + (158 - 163) * t)
                b = round(74 + (11 - 74) * t)
            else:
                t = (score - 0.5) / 0.5
                r = round(245 + (190 - 245) * t)
                g = round(158 + (24 - 158) * t)
                b = round(11 + (34 - 11) * t)
            fg = '#ffffff' if score > 0.70 else '#111827'
            return f'rgb({r},{g},{b})', fg

        def ana_fmt(v, col):
            if v is None:
                return '—'
            if 'Rank' in col:
                return f'{int(v)}'
            if col in ('Total', 'Offense', 'Defense', 'Special Teams'):
                return f'{v:g}%'
            if col in ('QB Tenure', 'HC Tenure', 'OC Tenure', 'DC Tenure', 'SC Tenure', '2025 Wins'):
                return f'{v:g}'
            return f'{v:g}'

        def ana_avg_fmt(v, col):
            if v is None:
                return 'â€”'
            if col in ('Total', 'Offense', 'Defense', 'Special Teams'):
                return f'{v:.1f}%'
            return f'{v:.1f}'

        team_games_ana = Games[
            (Games['Home'] == selected_team) | (Games['Away'] == selected_team)
        ].copy()
        team_games_ana['_week_num'] = pd.to_numeric(team_games_ana['Week'], errors='coerce')
        team_games_ana['_date_num'] = pd.to_datetime(team_games_ana['Date'], errors='coerce')
        team_games_ana = team_games_ana.sort_values(['_week_num', '_date_num']).reset_index(drop=True)

        games_by_week = {}
        for _, g in team_games_ana.iterrows():
            wk = pd.to_numeric(g.get('Week'), errors='coerce')
            if pd.notna(wk):
                games_by_week[wk] = g

        def ana_game_date(row):
            return pd.to_datetime(row.get('Date'), errors='coerce')

        def ana_prev_date(team, before_dt):
            if pd.isna(before_dt):
                return None
            tg = Games[
                ((Games['Home'] == team) | (Games['Away'] == team)) &
                (pd.to_datetime(Games['Date'], errors='coerce') < before_dt)
            ].copy()
            if len(tg) == 0:
                return None
            prev = pd.to_datetime(tg['Date'], errors='coerce').max()
            return prev if pd.notna(prev) else None

        def ana_rest_days(team, game_dt):
            prev = ana_prev_date(team, game_dt)
            if prev is None or pd.isna(game_dt):
                return None
            return int((game_dt - prev).days)

        sched_rows = []
        primetime_games = 0
        road_games = 0
        neutral_games = 0
        rest_edges = []
        avg_scores = []

        max_wk_val = pd.to_numeric(Games['Week'], errors='coerce').max()
        max_wk = max(int(max_wk_val), 18) if pd.notna(max_wk_val) else 18
        max_wk = min(max_wk, 18)

        for wk in range(1, max_wk + 1):
            if bye_int == wk and wk not in games_by_week:
                sched_rows.append({'week': wk, 'bye': True})
                continue
            if wk not in games_by_week:
                continue
            g = games_by_week[wk]
            is_home = g['Home'] == selected_team
            opponent = g['Away'] if is_home else g['Home']
            intl_val = g.get('International', False)
            is_intl = bool(intl_val) if not isinstance(intl_val, float) else False
            is_neutral = is_intl or (get_forced_venue(g) is not None)
            if is_neutral:
                neutral_games += 1
            elif not is_home:
                road_games += 1
            if tv_day_key(g) != 'sunday':
                primetime_games += 1

            dt = ana_game_date(g)
            team_rest = ana_rest_days(selected_team, dt)
            opp_rest = ana_rest_days(opponent, dt)
            rest_edge = None if team_rest is None or opp_rest is None else team_rest - opp_rest
            if rest_edge is not None:
                rest_edges.append(rest_edge)

            scores = [
                ana_strength(opponent, col, direction)
                for _, col, direction in strength_metric_cols
            ]
            score_vals = [s for s in scores if s is not None]
            avg_score = sum(score_vals) / len(score_vals) if score_vals else None
            if avg_score is not None:
                avg_scores.append(avg_score)

            sched_rows.append({
                'week': wk,
                'bye': False,
                'game': g,
                'opponent': opponent,
                'is_home': is_home,
                'is_neutral': is_neutral,
                'team_rest': team_rest,
                'opp_rest': opp_rest,
                'rest_edge': rest_edge,
                'avg_score': avg_score,
            })

        avg_opp_ou_vals = [
            team_metric_values.get(r.get('opponent'), {}).get('Vegas O/U')
            for r in sched_rows if not r.get('bye')
        ]
        avg_opp_ou_vals = [v for v in avg_opp_ou_vals if v is not None]
        avg_opp_ou = sum(avg_opp_ou_vals) / len(avg_opp_ou_vals) if avg_opp_ou_vals else None
        net_rest = sum(rest_edges) if rest_edges else 0

        def ana_rank_suffix(rank, total):
            return f'#{rank} of {total}' if rank is not None else ''

        league_tile_rows = []
        for tm in Team_Info['Team'].astype(str).str.strip().tolist():
            tm_games = Games[(Games['Home'] == tm) | (Games['Away'] == tm)].copy()
            tm_games['_week_num'] = pd.to_numeric(tm_games['Week'], errors='coerce')
            tm_games = tm_games.sort_values('_week_num').reset_index(drop=True)
            tm_ou_vals = []
            tm_rest_edges = []
            for _, tg in tm_games.iterrows():
                opp = tg['Away'] if tg['Home'] == tm else tg['Home']
                opp_ou = team_metric_values.get(opp, {}).get('Vegas O/U')
                if opp_ou is not None:
                    tm_ou_vals.append(opp_ou)
                tg_dt = ana_game_date(tg)
                tm_rest = ana_rest_days(tm, tg_dt)
                opp_rest = ana_rest_days(opp, tg_dt)
                if tm_rest is not None and opp_rest is not None:
                    tm_rest_edges.append(tm_rest - opp_rest)
            league_tile_rows.append({
                'team': tm,
                'avg_ou': (sum(tm_ou_vals) / len(tm_ou_vals)) if tm_ou_vals else None,
                'net_rest': sum(tm_rest_edges) if tm_rest_edges else 0,
            })

        ou_ranked = sorted([r for r in league_tile_rows if r['avg_ou'] is not None], key=lambda r: r['avg_ou'], reverse=True)
        rest_ranked = sorted(league_tile_rows, key=lambda r: -float(r['net_rest']))
        avg_ou_rank = next((i + 1 for i, r in enumerate(ou_ranked) if r['team'] == selected_team), None)
        net_rest_rank = next((i + 1 for i, r in enumerate(rest_ranked) if r['team'] == selected_team), None)

        four_game_windows = []
        game_only_rows = [r for r in sched_rows if not r.get('bye') and r.get('avg_score') is not None]
        for i in range(0, max(0, len(game_only_rows) - 3)):
            chunk = game_only_rows[i:i + 4]
            four_game_windows.append((sum(r['avg_score'] for r in chunk) / 4, chunk[0]['week'], chunk[-1]['week']))
        toughest_window = max(four_game_windows, default=None)

        def ana_card(label, value, sub='', accent=c1):
            return f'''
  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:8px;padding:16px 18px;
       box-shadow:0 1px 6px rgba(0,0,0,0.06);border-top:4px solid {accent};min-width:150px;flex:1;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:10px;font-weight:800;
         letter-spacing:3.5px;text-transform:uppercase;color:#94a3b8;margin-bottom:5px;">{label}</div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:44px;color:#1a2030;line-height:1;">{value}</div>
    {f'<div style="font-family:\'Barlow\',sans-serif;font-size:12px;color:#64748b;margin-top:3px;">{sub}</div>' if sub else ''}
  </div>'''

        schedule_rating = (sum(avg_scores) / len(avg_scores)) if avg_scores else None
        rating_label = 'TBD'
        if schedule_rating is not None:
            rating_label = 'Hard' if schedule_rating >= 0.64 else 'Soft' if schedule_rating <= 0.42 else 'Balanced'

        cards_html = '<div style="display:flex;gap:12px;margin:18px 0;flex-wrap:wrap;">'
        cards_html += ana_card('Schedule Read', rating_label, f'{schedule_rating * 100:.0f} strength index' if schedule_rating is not None else 'Needs opponent data')
        cards_html += ana_card('Avg Opp O/U', f'{avg_opp_ou:.1f}' if avg_opp_ou is not None else '—', f'Vegas baseline ({ana_rank_suffix(avg_ou_rank, len(ou_ranked))})')
        cards_html += ana_card('Road / Neutral', f'{road_games}/{neutral_games}', 'travel pressure')
        cards_html += ana_card('Net Rest', f'{net_rest:+d}', ' ')
        cards_html += '</div>'

        col_header = ''.join(
            f'<th style="padding:9px 8px;min-width:74px;font-family:\'Barlow Condensed\',sans-serif;'
            f'font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;'
            f'color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">{short}</th>'
            for short, _, _ in metric_cols
        )

        heat_rows = ''
        for r in sched_rows:
            if r.get('bye'):
                heat_rows += f"""
<tr>
  <td style="position:sticky;left:0;z-index:2;background:#0b0f19;color:#fff;padding:12px 12px;
       font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:800;border-bottom:1px solid #111827;">WK {r['week']}</td>
  <td colspan="{len(metric_cols) + 2}" style="background:#05070d;color:#fff;text-align:center;
       padding:13px;font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:900;
       letter-spacing:5px;text-transform:uppercase;border-bottom:1px solid #111827;">Bye Week</td>
</tr>"""
                continue

            g = r['game']
            opp = r['opponent']
            opp_logo = logo_map.get(opp, TBD_LOGO)
            opp_clr = clr1_map.get(opp, '#64748b')
            ha = 'N' if r['is_neutral'] else 'H' if r['is_home'] else 'A'
            try:
                dt_label = pd.to_datetime(g.get('Date')).strftime('%b %-d')
            except Exception:
                try:
                    dt_label = pd.to_datetime(g.get('Date')).strftime('%b %#d')
                except Exception:
                    dt_label = str(g.get('Date', 'TBA'))
            avg_bg, avg_fg = ana_heat_color(r.get('avg_score'))
            cells_html = ''
            for _, col, direction in metric_cols:
                val = team_metric_values.get(opp, {}).get(col)
                score = ana_strength(opp, col, direction)
                bg, fg = ana_heat_color(score)
                cells_html += f"""
  <td style="background:{bg};color:{fg};text-align:center;padding:9px 8px;
       font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:800;
       border-right:1px solid rgba(255,255,255,0.35);border-bottom:1px solid rgba(255,255,255,0.35);">
    {ana_fmt(val, col)}
  </td>"""

            heat_rows += f"""
<tr>
  <td style="position:sticky;left:0;z-index:2;background:#fff;padding:10px 12px;
       border-bottom:1px solid #edf0f7;border-left:5px solid {opp_clr};min-width:82px;">
    <div style="font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:900;color:#1a2030;line-height:1;">WK {r['week']}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:11px;color:#94a3b8;margin-top:2px;">{dt_label}</div>
  </td>
  <td style="position:sticky;left:82px;z-index:2;background:#fff;padding:9px 12px;
       border-bottom:1px solid #edf0f7;min-width:210px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <img src="{opp_logo}" style="width:34px;height:34px;object-fit:contain;"
           onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      <div>
        <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:800;color:#1a2030;line-height:1.05;">
          {ha} {opp}</div>
        <div style="font-family:'Barlow',sans-serif;font-size:11px;color:#94a3b8;margin-top:2px;">
          Rest {r['team_rest'] if r['team_rest'] is not None else '—'} vs {r['opp_rest'] if r['opp_rest'] is not None else '—'}</div>
      </div>
    </div>
  </td>
  <td style="background:{avg_bg};color:{avg_fg};text-align:center;padding:9px 10px;
       font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">
    {f"{r['avg_score'] * 100:.0f}" if r.get('avg_score') is not None else '—'}
  </td>
  {cells_html}
</tr>"""

        def render_heat_table(title, description, metrics, include_index=False, include_rest=False):
            extra_headers = ''
            if include_index:
                extra_headers += """
        <th style="position:sticky;top:0;z-index:3;background:#f8fafc;padding:9px 10px;min-width:74px;
             font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;
             text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Index</th>"""
            if include_rest:
                extra_headers += """
        <th style="position:sticky;top:0;z-index:3;background:#f8fafc;padding:9px 10px;min-width:74px;
             font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;
             text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Rest</th>
        <th style="position:sticky;top:0;z-index:3;background:#f8fafc;padding:9px 10px;min-width:74px;
             font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:2px;
             text-transform:uppercase;color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">Opp Rest</th>"""

            table_col_header = ''.join(
                f'<th style="padding:9px 8px;min-width:74px;font-family:\'Barlow Condensed\',sans-serif;'
                f'font-size:11px;font-weight:800;letter-spacing:2px;text-transform:uppercase;'
                f'color:#94a3b8;text-align:center;border-bottom:1px solid #e2e6ef;">{short}</th>'
                for short, _, _ in metrics
            )

            table_rows = ''
            extra_count = (1 if include_index else 0) + (2 if include_rest else 0)
            for r in sched_rows:
                if r.get('bye'):
                    table_rows += f"""
<tr>
  <td style="position:sticky;left:0;z-index:2;background:#0b0f19;color:#fff;padding:12px 12px;
       font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:800;border-bottom:1px solid #111827;">WK {r['week']}</td>
  <td colspan="{len(metrics) + extra_count + 1}" style="background:#05070d;color:#fff;text-align:center;
       padding:13px;font-family:'Barlow Condensed',sans-serif;font-size:14px;font-weight:900;
       letter-spacing:5px;text-transform:uppercase;border-bottom:1px solid #111827;">Bye Week</td>
</tr>"""
                    continue

                g = r['game']
                opp = r['opponent']
                opp_logo = logo_map.get(opp, TBD_LOGO)
                opp_clr = clr1_map.get(opp, '#64748b')
                ha = 'N ' if r['is_neutral'] else '@ ' if not r['is_home'] else ''
                try:
                    dt_label = pd.to_datetime(g.get('Date')).strftime('%b %-d')
                except Exception:
                    try:
                        dt_label = pd.to_datetime(g.get('Date')).strftime('%b %#d')
                    except Exception:
                        dt_label = str(g.get('Date', 'TBA'))

                extra_cells = ''
                if include_index:
                    avg_bg, avg_fg = ana_heat_color(r.get('avg_score'))
                    idx_val = f"{r['avg_score'] * 100:.0f}" if r.get('avg_score') is not None else '—'
                    extra_cells += f"""
  <td style="background:{avg_bg};color:{avg_fg};text-align:center;padding:9px 10px;
       font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{idx_val}</td>"""
                if include_rest:
                    rest_edge = r.get('rest_edge')
                    rest_bg = '#dcfce7' if rest_edge is not None and rest_edge > 0 else '#fee2e2' if rest_edge is not None and rest_edge < 0 else '#f1f5f9'
                    rest_fg = '#166534' if rest_edge is not None and rest_edge > 0 else '#991b1b' if rest_edge is not None and rest_edge < 0 else '#64748b'
                    extra_cells += f"""
  <td style="background:{rest_bg};color:{rest_fg};text-align:center;padding:9px 10px;
       font-family:'Rajdhani',sans-serif;font-size:17px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{r['team_rest'] if r['team_rest'] is not None else '—'}</td>
  <td style="background:{rest_bg};color:{rest_fg};text-align:center;padding:9px 10px;
       font-family:'Rajdhani',sans-serif;font-size:17px;font-weight:900;border-bottom:1px solid rgba(255,255,255,0.35);">{r['opp_rest'] if r['opp_rest'] is not None else '—'}</td>"""

                cells_html = ''
                for _, col, direction in metrics:
                    val = team_metric_values.get(opp, {}).get(col)
                    score = ana_strength(opp, col, direction)
                    bg, fg = ana_heat_color(score)
                    cells_html += f"""
  <td style="background:{bg};color:{fg};text-align:center;padding:9px 8px;
       font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:800;
       border-right:1px solid rgba(255,255,255,0.35);border-bottom:1px solid rgba(255,255,255,0.35);">{ana_fmt(val, col)}</td>"""

                table_rows += f"""
<tr>
  <td style="position:sticky;left:0;z-index:2;background:#fff;padding:10px 12px;
       border-bottom:1px solid #edf0f7;border-left:5px solid {opp_clr};min-width:82px;">
    <div style="font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:900;color:#1a2030;line-height:1;">WK {r['week']}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:11px;color:#94a3b8;margin-top:2px;">{dt_label}</div>
  </td>
  <td style="position:sticky;left:82px;z-index:2;background:#fff;padding:9px 12px;
       border-bottom:1px solid #edf0f7;min-width:210px;">
    <div style="display:flex;align-items:center;gap:10px;">
      <img src="{opp_logo}" style="width:34px;height:34px;object-fit:contain;"
           onerror="this.onerror=null;this.src='{TBD_LOGO}';">
      <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:800;color:#1a2030;line-height:1.05;">{ha}{opp}</div>
    </div>
  </td>
  {extra_cells}
  {cells_html}
</tr>"""

            data_rows = [r for r in sched_rows if not r.get('bye')]
            avg_extra_cells = ''
            if include_index:
                idx_vals = [r.get('avg_score') for r in data_rows if r.get('avg_score') is not None]
                idx_avg = (sum(idx_vals) / len(idx_vals)) if idx_vals else None
                idx_bg, idx_fg = ana_heat_color(idx_avg)
                avg_extra_cells += f"""
  <td style="background:{idx_bg};color:{idx_fg};text-align:center;padding:10px;
       font-family:'Rajdhani',sans-serif;font-size:18px;font-weight:900;border-top:2px solid #cbd5e1;">
    {f"{idx_avg * 100:.0f}" if idx_avg is not None else '—'}
  </td>"""
            if include_rest:
                team_rest_vals = [r.get('team_rest') for r in data_rows if r.get('team_rest') is not None]
                opp_rest_vals = [r.get('opp_rest') for r in data_rows if r.get('opp_rest') is not None]
                team_rest_avg = sum(team_rest_vals) / len(team_rest_vals) if team_rest_vals else None
                opp_rest_avg = sum(opp_rest_vals) / len(opp_rest_vals) if opp_rest_vals else None
                rest_edge_avg = None if team_rest_avg is None or opp_rest_avg is None else team_rest_avg - opp_rest_avg
                rest_bg = '#dcfce7' if rest_edge_avg is not None and rest_edge_avg > 0 else '#fee2e2' if rest_edge_avg is not None and rest_edge_avg < 0 else '#f1f5f9'
                rest_fg = '#166534' if rest_edge_avg is not None and rest_edge_avg > 0 else '#991b1b' if rest_edge_avg is not None and rest_edge_avg < 0 else '#64748b'
                avg_extra_cells += f"""
  <td style="background:{rest_bg};color:{rest_fg};text-align:center;padding:10px;
       font-family:'Rajdhani',sans-serif;font-size:17px;font-weight:900;border-top:2px solid #cbd5e1;">
    {f"{team_rest_avg:.1f}" if team_rest_avg is not None else '—'}
  </td>
  <td style="background:{rest_bg};color:{rest_fg};text-align:center;padding:10px;
       font-family:'Rajdhani',sans-serif;font-size:17px;font-weight:900;border-top:2px solid #cbd5e1;">
    {f"{opp_rest_avg:.1f}" if opp_rest_avg is not None else '—'}
  </td>"""

            avg_metric_cells = ''
            for _, col, direction in metrics:
                vals = [team_metric_values.get(r.get('opponent'), {}).get(col) for r in data_rows]
                vals = [v for v in vals if v is not None]
                avg_val = sum(vals) / len(vals) if vals else None
                lo, hi = metric_ranges.get(col, (0, 0))
                score = None if avg_val is None or hi == lo else (avg_val - lo) / (hi - lo)
                if score is not None and direction == 'low':
                    score = 1 - score
                if score is not None:
                    score = max(0, min(1, score))
                bg, fg = ana_heat_color(score)
                avg_metric_cells += f"""
  <td style="background:{bg};color:{fg};text-align:center;padding:10px 8px;
       font-family:'Rajdhani',sans-serif;font-size:16px;font-weight:900;border-top:2px solid #cbd5e1;">
    {ana_avg_fmt(avg_val, col)}
  </td>"""

            table_rows += f"""
<tr>
  <td style="position:sticky;left:0;z-index:2;background:#eef2f8;padding:11px 12px;
       border-top:2px solid #cbd5e1;border-left:5px solid {c1};font-family:'Rajdhani',sans-serif;
       font-size:18px;font-weight:900;color:#1a2030;">AVG</td>
  <td style="position:sticky;left:82px;z-index:2;background:#eef2f8;padding:11px 12px;
       border-top:2px solid #cbd5e1;font-family:'Barlow Condensed',sans-serif;font-size:18px;
       font-weight:900;color:#1a2030;letter-spacing:1px;text-transform:uppercase;">Schedule Avg</td>
  {avg_extra_cells}
  {avg_metric_cells}
</tr>"""

            min_width = 420 + (74 * (len(metrics) + extra_count))
            return f"""
<div style="margin-top:18px;">
  <div style="margin:0 0 8px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:18px;font-weight:900;letter-spacing:4px;
         text-transform:uppercase;color:{c1};">{title}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:14px;color:#64748b;margin-top:3px;line-height:1.45;">{description}</div>
  </div>
  <div style="overflow-x:auto;overflow-y:visible;border:1px solid #dfe5ef;border-radius:10px;background:#fff;
       box-shadow:0 2px 12px rgba(15,23,42,0.08);">
    <table style="border-collapse:separate;border-spacing:0;width:100%;min-width:{min_width}px;">
      <thead>
        <tr style="background:#f8fafc;">
          <th style="position:sticky;left:0;top:0;z-index:4;background:#f8fafc;padding:10px 12px;
               font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;
               text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;">Week</th>
          <th style="position:sticky;left:82px;top:0;z-index:4;background:#f8fafc;padding:10px 12px;
               font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:800;letter-spacing:3px;
               text-transform:uppercase;color:#94a3b8;text-align:left;border-bottom:1px solid #e2e6ef;">Opponent</th>
          {extra_headers}
          {table_col_header}
        </tr>
      </thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</div>"""

        legend_html = f"""
<div style="display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
     margin:10px 0 14px;">
  <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:800;
       letter-spacing:3px;text-transform:uppercase;color:#64748b;">Opponent metric heat map</div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-family:'Barlow',sans-serif;font-size:12px;color:#64748b;">Easier</span>
    <div style="width:170px;height:12px;border-radius:3px;
         background:linear-gradient(90deg,#16a34a 0%,#f59e0b 50%,#be1822 100%);
         border:1px solid #d7deea;"></div>
    <span style="font-family:'Barlow',sans-serif;font-size:12px;color:#64748b;">Harder</span>
  </div>
</div>"""

        index_note_html = f"""
<div style="background:#fff;border:1px solid #e2e6ef;border-left:5px solid {c1};border-radius:8px;
     padding:14px 16px;margin:12px 0 6px;box-shadow:0 1px 6px rgba(0,0,0,0.05);">
  <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:900;
       letter-spacing:3px;text-transform:uppercase;color:#1a2030;margin-bottom:5px;">How Index Works</div>
  <div style="font-family:'Barlow',sans-serif;font-size:13px;color:#64748b;line-height:1.55;">
    Index is a 0-100 opponent strength score built from the Opponent Strength columns below. Each metric is scaled across the league for the selected season, then flipped where lower is better, such as rank columns and defensive DVOA. Higher/redder rows mean the opponent grades tougher across the available strength profile.
  </div>
</div>"""

        toughest_text = (
            f"Weeks {toughest_window[1]}-{toughest_window[2]}"
            if toughest_window else "Not enough dated games"
        )
        rest_tilt = 'favorable' if net_rest > 0 else 'unfavorable' if net_rest < 0 else 'even'
        insight_html = f"""
<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:16px;">
  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:8px;padding:16px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:900;letter-spacing:3px;text-transform:uppercase;color:{c1};margin-bottom:6px;">Toughest Run</div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:38px;color:#1a2030;line-height:1;">{toughest_text}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:13px;color:#64748b;margin-top:6px;line-height:1.5;">Highest four-game average across the opponent metric index.</div>
  </div>
  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:8px;padding:16px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:900;letter-spacing:3px;text-transform:uppercase;color:{c1};margin-bottom:6px;">Rest Profile</div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:38px;color:#1a2030;line-height:1;">{rest_tilt.upper()}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:13px;color:#64748b;margin-top:6px;line-height:1.5;">Net rest compares days since each team&apos;s previous game.</div>
  </div>
  <div style="background:#fff;border:1px solid #e2e6ef;border-radius:8px;padding:16px;">
    <div style="font-family:'Barlow Condensed',sans-serif;font-size:12px;font-weight:900;letter-spacing:3px;text-transform:uppercase;color:{c1};margin-bottom:6px;">Spotlight Load</div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:38px;color:#1a2030;line-height:1;">{primetime_games}</div>
    <div style="font-family:'Barlow',sans-serif;font-size:13px;color:#64748b;margin-top:6px;line-height:1.5;">Counts SNF plus non-Sunday games as schedule disruption/visibility spots.</div>
  </div>
</div>"""

        strength_table_html = render_heat_table(
            'Opponent Strength',
            'Market baseline, record, rest and DVOA profile by opponent',
            strength_metric_cols,
            include_index=True,
            include_rest=True,
        )
        continuity_table_html = render_heat_table(
            'Opponent Continuity',
            'Coaching and quarterback tenure can point to communication stability, system familiarity, and early-season readiness.',
            continuity_metric_cols,
        )
        fantasy_table_html = render_heat_table(
            'Fantasy Outlook',
            'Position-level fantasy matchups metrics.',
            fantasy_metric_cols,
        )

        st.html(f"""
{ANALYTICS_RELEASE_NOTE}
{cards_html}
{insight_html}
{index_note_html}
{legend_html}
{strength_table_html}
{continuity_table_html}
{fantasy_table_html}
""")

    # ═══════════════════ TRAVEL TAB ══════════════════════════════════════════
    with sub_tabs[1]:
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

            team_city = city_map.get(selected_team, '').lower()
            opp_city = city_map.get(opponent, '').lower()
            game_loc_lower = game_loc.lower() if game_loc else ''
            is_neutral = (game_loc in NEUTRAL_LOCATION_SET) or (is_intl and game_loc) or (game_loc_lower and team_city and opp_city and game_loc_lower != team_city and game_loc_lower != opp_city)

            if is_neutral and game_loc:
                idata = intl_data.get(game_loc, {})
                return {
                    'opponent': opponent, 'is_intl': is_intl, 'travel_required': True,
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
            if not dst.get('city') or dst.get('city') == '—':
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

        def flag_is_true(v):
            if isinstance(v, float):
                return False if math.isnan(v) else bool(v)
            return str(v).strip().lower() in ('true', '1', 'yes', 'y')

        def team_origin(team):
            return {
                'team': team,
                'city': city_map.get(team, ''),
                'lat': lat_map.get(team),
                'lon': lon_map.get(team),
            }

        def game_site(game_loc):
            idata = intl_data.get(game_loc, {})
            return {
                'team': '',
                'city': game_loc,
                'lat': idata.get('lat'),
                'lon': idata.get('lon'),
            }

        def direct_miles(src, dst):
            if tv_valid_coord(src.get('lat')) and tv_valid_coord(src.get('lon')) and tv_valid_coord(dst.get('lat')) and tv_valid_coord(dst.get('lon')):
                return tv_haversine(float(src['lat']), float(src['lon']), float(dst['lat']), float(dst['lon']))
            return None

        def add_direct_flight(src, dst, flight_team, opponent, week_label, kind):
            miles = direct_miles(src, dst)
            legs.append({
                'from': src.get('city') or src.get('team') or 'Unknown',
                'to': dst.get('city') or dst.get('team') or 'Unknown',
                'miles': miles,
                'kind': kind,
                'note': f"{week_label}: {flight_team} vs {opponent}",
                'src_lat': src.get('lat'), 'src_lon': src.get('lon'),
                'dst_lat': dst.get('lat'), 'dst_lon': dst.get('lon'),
                'color_hex': clr1_map.get(flight_team, '#2563eb'),
            })

        legs = []
        for _, g in team_games_all.iterrows():
            home_team = str(g.get('Home', '')).strip()
            away_team = str(g.get('Away', '')).strip()
            game_loc = str(g.get('Location', '') or '').strip()
            wk_num = travel_week_num(g.get('Week'))
            wk_lbl = f"Wk {int(wk_num)}" if wk_num is not None else 'Wk TBA'

            if flag_is_true(g.get('International', False)) and game_loc:
                site = game_site(game_loc)
                if not manual_travel_stayover_to(home_team, wk_num):
                    add_direct_flight(team_origin(home_team), site, home_team, away_team, wk_lbl, 'international')
                if not manual_travel_stayover_to(away_team, wk_num):
                    add_direct_flight(team_origin(away_team), site, away_team, home_team, wk_lbl, 'international')
            else:
                add_direct_flight(team_origin(away_team), team_origin(home_team), away_team, home_team, wk_lbl, 'flight')

        def add_team_travel_leg(src, dst, opponent, week_label, kind, direction):
            miles = direct_miles(src, dst)
            travel_legs.append({
                'from': src.get('city') or src.get('team') or 'Unknown',
                'to': dst.get('city') or dst.get('team') or 'Unknown',
                'miles': miles,
                'kind': kind,
                'note': f"{week_label}: {selected_team} {direction} vs {opponent}",
                'src_lat': src.get('lat'), 'src_lon': src.get('lon'),
                'dst_lat': dst.get('lat'), 'dst_lon': dst.get('lon'),
            })

        travel_legs = []
        selected_origin = team_origin(selected_team)
        for _, g in team_games_all.iterrows():
            home_team = str(g.get('Home', '')).strip()
            away_team = str(g.get('Away', '')).strip()
            game_loc = str(g.get('Location', '') or '').strip()
            wk_num = pd.to_numeric(g.get('Week'), errors='coerce')
            wk_lbl = f"Wk {int(wk_num)}" if pd.notna(wk_num) else 'Wk TBA'
            is_intl = flag_is_true(g.get('International', False))

            if is_intl and game_loc:
                opponent = away_team if home_team == selected_team else home_team
                destination = game_site(game_loc)
                kind = 'international'
            elif away_team == selected_team:
                opponent = home_team
                destination = team_origin(home_team)
                kind = 'flight'
            else:
                continue

            add_team_travel_leg(selected_origin, destination, opponent, wk_lbl, kind, 'to game')
            add_team_travel_leg(destination, selected_origin, opponent, wk_lbl, kind, 'return')

        team_route = build_team_travel(
            selected_team, team_games_all, city_map, stad_map, lat_map, lon_map, tz_map, intl_data, clr1_map
        )
        travel_legs = team_route['legs']
        transfer_legs = [l for l in travel_legs if l.get('kind') == 'transfer']
        flights = team_route['flights']
        total_miles = team_route['total_miles']

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

        visual_legs = legs + transfer_legs
        arc_rows = []
        for l in visual_legs:
            if not (tv_valid_coord(l['src_lat']) and tv_valid_coord(l['src_lon']) and tv_valid_coord(l['dst_lat']) and tv_valid_coord(l['dst_lon'])):
                continue
            arc_rows.append({
                'from': l['from'], 'to': l['to'], 'note': l['note'], 'miles': l['miles'] or 0,
                'src_lon': float(l['src_lon']), 'src_lat': float(l['src_lat']),
                'dst_lon': float(l['dst_lon']), 'dst_lat': float(l['dst_lat']),
                'kind': l['kind'],
                'color_hex': l.get('color_hex', c1),
                'color': [37, 99, 235, 180],
            })

        arc_df = pd.DataFrame(arc_rows) if arc_rows else pd.DataFrame()
        node_rows = []
        if tv_valid_coord(home_base.get('lat')) and tv_valid_coord(home_base.get('lon')):
            node_rows.append({
                'name': home_base.get('city') or selected_team,
                'lon': float(home_base['lon']), 'lat': float(home_base['lat']),
                'size': 18000, 'color': [200, 16, 46, 210], 'home': True,
            })
        for a in arc_rows:
            node_rows.append({
                'name': a['from'],
                'lon': a['src_lon'],
                'lat': a['src_lat'],
                'size': 9000,
                'color': [30, 64, 175, 180],
                'home': False,
            })
            node_rows.append({
                'name': a['to'],
                'lon': a['dst_lon'],
                'lat': a['dst_lat'],
                'size': 9000,
                'color': [30, 64, 175, 180],
                'home': False,
            })
        node_df = pd.DataFrame(node_rows).drop_duplicates(subset=['lon', 'lat']) if node_rows else pd.DataFrame()

        render_travel_motion_map(arc_df, node_df, f'team-travel-{abb}', height=500, initial_view=(39.5, -98.35, 4))

        leg_rows_html = ''
        for i, l in enumerate(travel_legs):
            row_bg = '#ffffff' if i % 2 == 0 else '#f8fafc'
            miles = f"{int(l['miles']):,} mi" if l['miles'] is not None else 'TBD'
            kind = 'XFER' if l['kind'] == 'transfer' else 'OUT' if l['kind'] == 'outbound' else 'RET'
            kind_bg = '#fef3c7' if l['kind'] == 'transfer' else '#dbeafe' if l['kind'] == 'outbound' else '#fee2e2'
            kind_fg = '#92400e' if l['kind'] == 'transfer' else '#1e3a8a' if l['kind'] == 'outbound' else '#991b1b'
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
