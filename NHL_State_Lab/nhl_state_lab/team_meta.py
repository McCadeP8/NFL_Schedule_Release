TEAM_NAMES = {
    "ANA": "Anaheim", "BOS": "Boston", "BUF": "Buffalo", "CAR": "Carolina", "CBJ": "Columbus",
    "CGY": "Calgary", "CHI": "Chicago", "COL": "Colorado", "DAL": "Dallas", "DET": "Detroit",
    "EDM": "Edmonton", "FLA": "Florida", "LAK": "Los Angeles", "MIN": "Minnesota", "MTL": "Montreal",
    "NJD": "New Jersey", "NSH": "Nashville", "NYI": "New York I", "NYR": "New York R", "OTT": "Ottawa",
    "PHI": "Philadelphia", "PIT": "Pittsburgh", "SEA": "Seattle", "SJS": "San Jose", "STL": "St. Louis",
    "TBL": "Tampa Bay", "TOR": "Toronto", "UTA": "Utah", "VAN": "Vancouver", "VGK": "Vegas",
    "WPG": "Winnipeg", "WSH": "Washington",
}


TEAM_LOGOS = {
    abbreviation: f"https://assets.nhle.com/logos/nhl/svg/{abbreviation}_light.svg"
    for abbreviation in TEAM_NAMES
}


TEAM_ABBREV_BY_NAME = {name: abbreviation for abbreviation, name in TEAM_NAMES.items()}
