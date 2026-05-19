from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st


CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1qjPpIEGmhV8aF3CZ8hi-ijQlIP-_z6QYJzSArjJV9d8/"
    "export?format=csv&gid=0"
)
SEASON = "2026"
WEEK = 1
DB_PATH = Path(__file__).parent / "data" / "pickem_results.sqlite"


st.set_page_config(
    page_title="NFL Pick'em",
    page_icon=":football:",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=300)
def get_games() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)
    return df


def filtered_games(df: pd.DataFrame, season: str = SEASON, week: int = WEEK) -> pd.DataFrame:
    required = {"GameID", "Away", "Home", "Date", "Week"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    games = df.copy()
    games["Week"] = pd.to_numeric(games["Week"], errors="coerce")
    games["Date_sort"] = pd.to_datetime(games["Date"], errors="coerce")
    games = games[
        games["GameID"].astype(str).str.startswith(f"{season}_")
        & (games["Week"] == week)
        & (games["Away"].astype(str).str.lower() != "to be determined")
        & (games["Home"].astype(str).str.lower() != "to be determined")
    ].copy()

    games = games.sort_values(["Date_sort", "Time (ET)", "GameID"], na_position="last")
    return games.reset_index(drop=True)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                submitted_at_utc TEXT NOT NULL,
                player_name TEXT NOT NULL,
                email TEXT,
                season TEXT NOT NULL,
                week INTEGER NOT NULL,
                tiebreaker_points INTEGER,
                picks_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS picks (
                submission_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_team TEXT NOT NULL,
                selected_team TEXT NOT NULL,
                confidence INTEGER,
                PRIMARY KEY (submission_id, game_id),
                FOREIGN KEY (submission_id) REFERENCES submissions(submission_id)
            )
            """
        )


def save_submission(
    player_name: str,
    email: str,
    games: pd.DataFrame,
    picks: dict[str, str],
    confidence: dict[str, int],
    tiebreaker_points: int,
) -> str:
    init_db()
    submission_id = str(uuid.uuid4())
    submitted_at = datetime.now(timezone.utc).isoformat()

    pick_records = []
    for game in games.to_dict("records"):
        game_id = str(game["GameID"])
        pick_records.append(
            {
                "game_id": game_id,
                "away_team": str(game["Away"]),
                "home_team": str(game["Home"]),
                "selected_team": picks[game_id],
                "confidence": int(confidence.get(game_id, 1)),
            }
        )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO submissions (
                submission_id, submitted_at_utc, player_name, email,
                season, week, tiebreaker_points, picks_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission_id,
                submitted_at,
                player_name,
                email,
                SEASON,
                WEEK,
                tiebreaker_points,
                json.dumps(pick_records),
            ),
        )
        conn.executemany(
            """
            INSERT INTO picks (
                submission_id, game_id, away_team, home_team,
                selected_team, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    submission_id,
                    row["game_id"],
                    row["away_team"],
                    row["home_team"],
                    row["selected_team"],
                    row["confidence"],
                )
                for row in pick_records
            ],
        )

    return submission_id


def load_submissions() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """
            SELECT
                s.submitted_at_utc,
                s.player_name,
                s.email,
                s.season,
                s.week,
                s.tiebreaker_points,
                p.game_id,
                p.away_team,
                p.home_team,
                p.selected_team,
                p.confidence,
                s.submission_id
            FROM submissions s
            JOIN picks p ON s.submission_id = p.submission_id
            ORDER BY s.submitted_at_utc DESC, p.game_id
            """,
            conn,
        )


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1", "y"}


def clean_label(value: object, fallback: str = "TBA") -> str:
    text = str(value or "").strip()
    if text.lower() in {"", "nan", "none"}:
        return fallback
    return text


def matchup_card(game: pd.Series, index: int) -> None:
    game_id = str(game["GameID"])
    away = str(game["Away"])
    home = str(game["Home"])
    date = pd.to_datetime(game.get("Date"), errors="coerce")
    date_label = f"{date:%a, %b} {date.day}" if pd.notna(date) else clean_label(game.get("Date"))
    time_label = clean_label(game.get("Time (ET)"))
    network = clean_label(game.get("TV Network"))
    location = clean_label(game.get("Location"), fallback="")
    tags = []
    if boolish(game.get("International")):
        tags.append("International")
    primetime = str(game.get("Primetime", "") or "").strip()
    if primetime and primetime.lower() != "no":
        tags.append(primetime)

    st.markdown(
        f"""
        <div class="game-card">
            <div class="game-meta">
                <span>Game {index}</span>
                <span>{date_label}</span>
                <span>{time_label} ET</span>
                <span>{network}</span>
            </div>
            <div class="matchup">
                <div class="team away">{away}</div>
                <div class="at">@</div>
                <div class="team home">{home}</div>
            </div>
            <div class="venue">{location}</div>
            <div class="tags">{" ".join(f"<span>{tag}</span>" for tag in tags)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.radio(
        "Winner",
        options=[away, home],
        index=None,
        key=f"pick_{game_id}",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.slider(
        "Confidence",
        min_value=1,
        max_value=16,
        value=1,
        key=f"confidence_{game_id}",
        help="Optional scoring idea: award confidence points for correct picks.",
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #697386;
            --line: #d9e0ea;
            --field: #f6f8fb;
            --accent: #c8102e;
            --gold: #c9a227;
        }
        .block-container {
            max-width: 1180px;
            padding-top: 2.25rem;
        }
        .hero {
            border-bottom: 1px solid var(--line);
            padding-bottom: 1rem;
            margin-bottom: 1.25rem;
        }
        .hero h1 {
            margin: 0;
            color: var(--ink);
            font-size: 2.4rem;
            line-height: 1.1;
            letter-spacing: 0;
        }
        .hero p {
            color: var(--muted);
            font-size: 1rem;
            margin: .5rem 0 0;
        }
        .status-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: .75rem;
            margin: 1rem 0 1.25rem;
        }
        .status-pill {
            background: var(--field);
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: .75rem .85rem;
        }
        .status-pill strong {
            display: block;
            color: var(--ink);
            font-size: 1.35rem;
            line-height: 1.1;
        }
        .status-pill span {
            color: var(--muted);
            font-size: .82rem;
        }
        .game-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            background: #ffffff;
            margin-top: .35rem;
        }
        .game-meta {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            color: var(--muted);
            font-size: .78rem;
            text-transform: uppercase;
            letter-spacing: 0;
        }
        .game-meta span {
            background: var(--field);
            border: 1px solid #e5eaf2;
            border-radius: 999px;
            padding: .14rem .45rem;
        }
        .matchup {
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
            align-items: center;
            gap: .8rem;
            margin-top: .8rem;
        }
        .team {
            color: var(--ink);
            font-size: 1.35rem;
            font-weight: 800;
            line-height: 1.15;
        }
        .team.home {
            text-align: right;
        }
        .at {
            color: var(--accent);
            font-weight: 900;
        }
        .venue {
            color: var(--muted);
            margin-top: .5rem;
            font-size: .9rem;
        }
        .tags {
            min-height: 1.65rem;
            margin-top: .6rem;
        }
        .tags span {
            display: inline-block;
            background: #fff8df;
            border: 1px solid #ead68d;
            color: #6d5608;
            border-radius: 999px;
            padding: .18rem .5rem;
            margin-right: .35rem;
            font-size: .78rem;
            font-weight: 700;
        }
        @media (max-width: 700px) {
            .status-row {
                grid-template-columns: 1fr;
            }
            .matchup {
                grid-template-columns: 1fr;
                gap: .35rem;
            }
            .team.home {
                text-align: left;
            }
            .at {
                display: none;
            }
            .team.home::before {
                content: "@ ";
                color: var(--accent);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    inject_css()

    st.markdown(
        """
        <div class="hero">
            <h1>NFL Pick'em</h1>
            <p>Pick every Week 1 winner, add a confidence score, and submit your entry.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("League Setup")
        player_name = st.text_input("Name", placeholder="Your name")
        email = st.text_input("Email optional", placeholder="name@example.com")
        tiebreaker_points = st.number_input(
            "Tiebreaker total points",
            min_value=0,
            max_value=200,
            value=44,
            step=1,
        )
        st.caption("This prototype saves submissions to a local SQLite database.")

    try:
        all_games = get_games()
        games = filtered_games(all_games)
    except Exception as exc:
        st.error("I could not load the Week 1 schedule.")
        st.exception(exc)
        return

    if games.empty:
        st.warning(f"No {SEASON} Week {WEEK} games were found in the source sheet.")
        return

    st.markdown(
        f"""
        <div class="status-row">
            <div class="status-pill"><strong>{len(games)}</strong><span>Games loaded</span></div>
            <div class="status-pill"><strong>{SEASON}</strong><span>Season</span></div>
            <div class="status-pill"><strong>Week {WEEK}</strong><span>Pool slate</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("pickem_form", clear_on_submit=False):
        for i, (_, game) in enumerate(games.iterrows(), start=1):
            matchup_card(game, i)

        submitted = st.form_submit_button("Submit Picks", use_container_width=True)

    game_ids = [str(game_id) for game_id in games["GameID"]]
    picks = {game_id: st.session_state.get(f"pick_{game_id}") for game_id in game_ids}
    confidence = {
        game_id: int(st.session_state.get(f"confidence_{game_id}", 1))
        for game_id in game_ids
    }
    completed = sum(1 for pick in picks.values() if pick)

    st.progress(completed / len(games), text=f"{completed} of {len(games)} winners selected")

    if submitted:
        if not player_name.strip():
            st.error("Add your name before submitting.")
        elif completed < len(games):
            st.error("Pick a winner for every game before submitting.")
        else:
            submission_id = save_submission(
                player_name=player_name.strip(),
                email=email.strip(),
                games=games,
                picks=picks,
                confidence=confidence,
                tiebreaker_points=int(tiebreaker_points),
            )
            st.success(f"Picks saved. Submission ID: {submission_id}")

    with st.expander("View saved submissions"):
        submissions = load_submissions()
        if submissions.empty:
            st.info("No submissions saved yet.")
        else:
            st.dataframe(submissions, use_container_width=True, hide_index=True)
            st.download_button(
                "Download submissions CSV",
                data=submissions.to_csv(index=False).encode("utf-8"),
                file_name=f"nfl_pickem_{SEASON}_week_{WEEK}_submissions.csv",
                mime="text/csv",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
