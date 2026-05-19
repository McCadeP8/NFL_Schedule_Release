from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from urllib.request import urlopen

import streamlit as st


DEFAULT_ROWS = [
    {"Question": "2024 NFL Passing Leaders", "Rank": "1", "Player": "Joe Burrow", "Team": "CIN", "Value": "4918"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "2", "Player": "Jared Goff", "Team": "DET", "Value": "4629"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "3", "Player": "Baker Mayfield", "Team": "TAM", "Value": "4500"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "4", "Player": "Geno Smith", "Team": "SEA", "Value": "4320"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "5", "Player": "Sam Darnold", "Team": "MIN", "Value": "4319"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "6", "Player": "Lamar Jackson", "Team": "BAL", "Value": "4172"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "7", "Player": "Patrick Mahomes", "Team": "KAN", "Value": "3928"},
    {"Question": "2024 NFL Passing Leaders", "Rank": "8", "Player": "Aaron Rodgers", "Team": "NYJ", "Value": "3897"},
]


@dataclass(frozen=True)
class Answer:
    rank: int
    points: int
    player: str
    team: str
    value: str


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def normalize_team(team: str) -> str:
    aliases = {"KC": "KAN", "TB": "TAM", "GB": "GNB", "NO": "NOR", "SF": "SFO"}
    cleaned = team.strip().upper()
    return aliases.get(cleaned, cleaned)


def weighted_points(count: int) -> list[int]:
    weights = list(range(count, 0, -1))
    total_weight = sum(weights)
    points = [max(1, round(100 * weight / total_weight)) for weight in weights]
    drift = 100 - sum(points)
    index = 0
    while drift:
        step = 1 if drift > 0 else -1
        if points[index] + step > 0:
            points[index] += step
            drift -= step
        index = (index + 1) % len(points)
    return points


def load_rows_from_csv_url(url: str) -> list[dict[str, str]]:
    with urlopen(url, timeout=10) as response:
        text = response.read().decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def load_rows(csv_url: str) -> list[dict[str, str]]:
    if not csv_url.strip():
        return DEFAULT_ROWS
    return load_rows_from_csv_url(csv_url.strip())


def get_questions(rows: list[dict[str, str]]) -> list[str]:
    return sorted({row.get("Question", "").strip() for row in rows if row.get("Question", "").strip()})


def build_answers(rows: list[dict[str, str]], question: str) -> list[Answer]:
    question_rows = [row for row in rows if row.get("Question", "").strip() == question]
    question_rows.sort(key=lambda row: int(row.get("Rank", 999)))
    points = weighted_points(len(question_rows))
    return [
        Answer(
            rank=int(row.get("Rank", index + 1)),
            points=int(row.get("Pts") or row.get("Points") or points[index]),
            player=row.get("Player", "").strip(),
            team=normalize_team(row.get("Team", "").strip()),
            value=row.get("Value", "").strip(),
        )
        for index, row in enumerate(question_rows)
    ]


def format_value(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value)
    return f"{int(digits):,}" if digits else value


def reset_game(answers: list[Answer]) -> None:
    st.session_state.answer_key = tuple(answer.player for answer in answers)
    st.session_state.revealed = set()
    st.session_state.strikes = 0
    st.session_state.score = 0
    st.session_state.message = ""


def ensure_game(answers: list[Answer]) -> None:
    if st.session_state.get("answer_key") != tuple(answer.player for answer in answers):
        reset_game(answers)


def find_match(guess: str, answers: list[Answer]) -> Answer | None:
    clean_guess = normalize(guess)
    if not clean_guess:
        return None

    for answer in answers:
        player = normalize(answer.player)
        last_name = normalize(answer.player.split()[-1])
        if clean_guess in {player, last_name} or clean_guess in player:
            return answer
    return None


def submit_guess(guess: str, answers: list[Answer]) -> None:
    game_finished = st.session_state.strikes >= 3 or len(st.session_state.revealed) == len(answers)
    if game_finished:
        return

    match = find_match(guess, answers)
    if match and match.rank not in st.session_state.revealed:
        st.session_state.revealed.add(match.rank)
        st.session_state.score += match.points
        st.session_state.message = f"Correct: {match.player} for {match.points} points."
        return

    if match:
        st.session_state.message = f"{match.player} is already revealed."
        return

    st.session_state.strikes += 1
    st.session_state.message = "No match. Strike."


def render_sidebar() -> tuple[str, list[dict[str, str]]]:
    st.sidebar.header("Data")
    csv_url = st.sidebar.text_input(
        "Google Sheets CSV URL",
        placeholder="Paste a published CSV link",
        help="Columns: Question, Rank, Player, Team, Value, optional Pts.",
    )

    try:
        rows = load_rows(csv_url)
    except Exception as exc:
        st.sidebar.error(f"Sheet load failed: {exc}")
        rows = DEFAULT_ROWS

    questions = get_questions(rows)
    question = st.sidebar.selectbox("Question", questions)
    return question, rows


def render_header(question: str, answers: list[Answer]) -> None:
    found = len(st.session_state.revealed)
    left = len(answers) - found
    strike_text = "X " * st.session_state.strikes + "_ " * (3 - st.session_state.strikes)

    st.caption("NFL Family Feud")
    st.title(question)

    score_col, found_col, left_col, strikes_col = st.columns(4)
    score_col.metric("Score", st.session_state.score)
    found_col.metric("Found", f"{found}/{len(answers)}")
    left_col.metric("Left", left)
    strikes_col.metric("Strikes", strike_text.strip())


def render_guess_form(answers: list[Answer]) -> None:
    disabled = st.session_state.strikes >= 3 or len(st.session_state.revealed) == len(answers)

    with st.form("guess_form", clear_on_submit=True):
        guess_col, button_col = st.columns([4, 1])
        with guess_col:
            guess = st.text_input(
                "Guess a player",
                placeholder="Search players...",
                label_visibility="collapsed",
                disabled=disabled,
            )
        with button_col:
            submitted = st.form_submit_button("Guess", type="primary", use_container_width=True, disabled=disabled)

    if submitted:
        submit_guess(guess, answers)
        st.rerun()


def render_message(answers: list[Answer]) -> None:
    if len(st.session_state.revealed) == len(answers):
        st.success("Clean sweep. You got the whole board.")
    elif st.session_state.strikes >= 3:
        st.error("Three strikes. Game over.")
    elif st.session_state.message:
        st.info(st.session_state.message)


def render_answer(answer: Answer) -> None:
    is_revealed = answer.rank in st.session_state.revealed
    with st.container(border=True):
        if is_revealed:
            st.subheader(answer.player)
            st.caption(f"{answer.team} | Rank {answer.rank} | {format_value(answer.value)} yards")
            st.metric("Points", answer.points)
        else:
            st.subheader(f"#{answer.rank}")
            st.caption("Hidden answer")
            st.metric("Points", "?")


def render_board(answers: list[Answer]) -> None:
    first_col, second_col = st.columns(2)
    for index, answer in enumerate(answers):
        with first_col if index % 2 == 0 else second_col:
            render_answer(answer)


def render_footer_controls(answers: list[Answer]) -> None:
    reset_col, reveal_col = st.columns([1, 1])
    with reset_col:
        if st.button("New game", use_container_width=True):
            reset_game(answers)
            st.rerun()
    with reveal_col:
        if st.button("Reveal board", use_container_width=True):
            st.session_state.revealed = {answer.rank for answer in answers}
            st.session_state.message = "Board revealed."
            st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="NFL Family Feud",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    question, rows = render_sidebar()
    answers = build_answers(rows, question)
    ensure_game(answers)

    render_header(question, answers)
    render_guess_form(answers)
    render_message(answers)
    st.divider()
    render_board(answers)
    st.divider()
    render_footer_controls(answers)


if __name__ == "__main__":
    main()
