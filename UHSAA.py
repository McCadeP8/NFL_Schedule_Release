"""
Scraper for MaxPreps team schedule pages.
Tested with: https://www.maxpreps.com/ut/panguitch/panguitch-bobcats/basketball/schedule/

Requirements:
    pip install requests beautifulsoup4 pandas
"""

import re
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup

URL = "https://www.maxpreps.com/ut/panguitch/panguitch-bobcats/basketball/schedule/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def school_year_bounds(today: datetime.date = None):
    """
    Return (year1, year2) for the current school year.
    School year starts July 1:
      - On/after July 1  → year1=today.year,     year2=today.year+1
      - Before July 1    → year1=today.year-1,   year2=today.year
    """
    if today is None:
        today = datetime.date.today()
    if today >= datetime.date(today.year, 7, 1):
        return today.year, today.year + 1
    else:
        return today.year - 1, today.year


def resolve_date(month: int, day: int, year1: int, year2: int) -> datetime.date:
    """
    Assign the correct year to a month/day based on school year convention:
      July–December  → year1
      January–June   → year2
    """
    year = year1 if month >= 7 else year2
    return datetime.date(year, month, day)


def parse_team_from_url(url: str) -> str:
    """Extract a human-readable team name from the MaxPreps URL."""
    # e.g. .../ut/panguitch/panguitch-bobcats/basketball/... → "Panguitch Bobcats"
    match = re.search(r"/[a-z]{2}/[^/]+/([^/]+)/", url)
    if match:
        slug = match.group(1)           # "panguitch-bobcats"
        return slug.replace("-", " ").title()
    return "Unknown"


def parse_sport_from_url(url: str) -> str:
    """Extract sport from the MaxPreps URL."""
    match = re.search(r"/([^/]+)/schedule", url)
    if match:
        return match.group(1).replace("-", " ").title()
    return "Unknown"


def scrape_schedule(url: str = URL) -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Derive metadata from URL
    team  = parse_team_from_url(url)
    sport = parse_sport_from_url(url)

    # Determine school-year bounds dynamically
    year1, year2 = school_year_bounds()

    # Find the schedule table
    table = soup.find("table")
    if table is None:
        raise ValueError("Could not find schedule table on page.")

    rows = table.find_all("tr")
    games = []

    for row in rows[1:]:  # skip header row
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # --- Date (with year) ---
        date_text = cols[0].get_text(separator=" ", strip=True)
        # e.g. "11/21 7:00pm"
        date_match = re.match(r"(\d+)/(\d+)", date_text)
        if date_match:
            month, day = int(date_match.group(1)), int(date_match.group(2))
            date = resolve_date(month, day, year1, year2)
        else:
            date = date_text

        # --- Opponent & Home/Away ---
        opp_col = cols[1].get_text(separator=" ", strip=True)
        if opp_col.startswith("vs"):
            location = "Home"
            opponent = opp_col.replace("vs", "", 1).strip()
        elif opp_col.startswith("@"):
            location = "Away"
            opponent = opp_col.replace("@", "", 1).strip()
        else:
            location = "Neutral"
            opponent = opp_col.strip()

        # Strip trailing region/playoff markers like *, **, ***
        opponent = re.sub(r"\*+$", "", opponent).strip()

        # --- Result ---
        result_text = cols[2].get_text(separator=" ", strip=True)
        # e.g. "W 72-54" or "L 58-53 (OT)"
        result_match = re.match(r"([WL])\s+(\d+)-(\d+)", result_text)
        if result_match:
            outcome   = "Win" if result_match.group(1) == "W" else "Loss"
            t_score   = int(result_match.group(2))
            o_score   = int(result_match.group(3))
            overtime  = "(OT)" in result_text
        else:
            outcome  = result_text or None
            t_score  = None
            o_score  = None
            overtime = False

        games.append({
            "Team":     team,
            "Sport":    sport,
            "Date":     date,
            "Opponent": opponent,
            "Location": location,
            "Result":   outcome,
            "TScore":   t_score,
            "OScore":   o_score,
            "Overtime": overtime,
        })

    df = pd.DataFrame(games)
    return df


if __name__ == "__main__":
    df = scrape_schedule()
    print(df.to_string(index=False))
    print(f"\n{len(df)} games scraped.")

    # Optionally save to CSV
    # df.to_csv("panguitch_schedule.csv", index=False)