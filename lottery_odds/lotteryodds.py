import numpy as np
import pandas as pd
from itertools import permutations

# ── Setup ────────────────────────────────────────────────────────────────────
teams = ["Wizards", "Pacers", "Nets", "Jazz", "Kings", "Grizzlies", "Pelicans", "Mavericks", "Bulls", "Bucks", "Warriors", "Clippers", "Heat", "Hornets"]
odds  = [140, 140, 140, 115, 115, 90, 68, 67, 45, 30, 20, 15, 10, 5]

W = sum(odds)

# ── Probability of one ORDERED top-4 permutation ─────────────────────────────
def perm_prob(idx):
    w = [odds[i] for i in idx]
    return (
        (w[0] / W) *
        (w[1] / (W - w[0])) *
        (w[2] / (W - w[0] - w[1])) *
        (w[3] / (W - w[0] - w[1] - w[2]))
    )

# ── Generate all P(14,4) = 24,024 ordered permutations ───────────────────────
rows = []
for top4 in permutations(range(14), 4):
    rest  = [i for i in range(14) if i not in top4]   # remaining 10, original order
    full  = list(top4) + rest
    prob  = perm_prob(top4)
    rows.append(full + [prob])

# ── Build results DataFrame ───────────────────────────────────────────────────
pick_cols = [f"Pick{i+1}" for i in range(14)]
df = pd.DataFrame(rows, columns=pick_cols + ["Probability"])

# Map indices → team names
for col in pick_cols:
    df[col] = df[col].apply(lambda x: teams[x])

df["Pct"] = (df["Probability"] * 100).round(6)
df["Probability"] = df["Probability"].round(8)
df = df.sort_values("Probability", ascending=False).reset_index(drop=True)

# ── Apply pick transitions ────────────────────────────────────────────────────
# 1. Clippers pick goes to Thunder
for col in pick_cols:
    df[col] = df[col].replace("Clippers", "Thunder")

# 2. Pacers pick is top-4 protected; if not in top 4, goes to Clippers
for col in pick_cols[4:]:  # Picks 5-14 (indices 4-13)
    df[col] = df[col].replace("Pacers", "Clippers")

# 3. Pelicans pick goes to Hawks, then Hawks and Bucks do a pick swap
for col in pick_cols:
    df[col] = df[col].replace("Pelicans", "Hawks")

# 4. Hawks and Bucks pick swap - Hawks get the better (earlier) pick
def apply_pick_swap(row):
    pick_cols_list = pick_cols
    hawks_idx = None
    bucks_idx = None
    for i, col in enumerate(pick_cols_list):
        if row[col] == "Hawks":
            hawks_idx = i
        if row[col] == "Bucks":
            bucks_idx = i
    if hawks_idx is not None and bucks_idx is not None:
        if hawks_idx > bucks_idx:  # Bucks pick is better (earlier)
            row[pick_cols_list[hawks_idx]] = "Bucks"
            row[pick_cols_list[bucks_idx]] = "Hawks"
    return row

df = df.apply(apply_pick_swap, axis=1)

def get_lottery_data(selections=None):
    """
    Get lottery scenarios, optionally filtered by pick selections.

    Args:
        selections: dict of {pick_number: team_name} to filter by

    Returns:
        Filtered dataframe with probabilities
    """
    filtered = df.copy()

    if selections:
        for pick_num, team in selections.items():
            if team:
                col = f"Pick{pick_num}"
                filtered = filtered[filtered[col] == team]

    return filtered.sort_values("Probability", ascending=False)

def get_pick_probability(pick_num, team, selections=None):
    """Get probability of a specific team getting a specific pick."""
    data = get_lottery_data(selections)
    if len(data) == 0:
        return 0.0

    col = f"Pick{pick_num}"
    matching = data[data[col] == team]
    total_prob = matching["Probability"].sum()

    # Normalize by total probability of filtered data to get conditional probability
    data_total = data["Probability"].sum()
    if data_total > 0:
        return total_prob / data_total
    else:
        return 0.0
