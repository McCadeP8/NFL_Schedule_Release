from __future__ import annotations
import pandas as pd
import streamlit as st
from data import load_all_rosters, LEAGUES, POSITIONS, position_table

st.set_page_config(page_title="NCFL Rosters", layout="wide")
st.title("NCFL Rosters")

all_rosters = load_all_rosters()
selected_league = st.selectbox("League", list(LEAGUES.keys()))
league_rosters = all_rosters.loc[all_rosters["league_name"].eq(selected_league)].copy()

for position in POSITIONS:
    st.subheader(position)
    st.dataframe(
        position_table(league_rosters, position),
        use_container_width=True,
        hide_index=True,
        height="content")
