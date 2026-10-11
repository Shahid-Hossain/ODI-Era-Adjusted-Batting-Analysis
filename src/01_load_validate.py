"""01 - Load the raw files, build one clean table of batting innings, and validate it.

Stops with an error if Sachin Tendulkar's totals do not match his official ODI record
(18,426 runs, average 44.83, strike rate 86.23).
"""
import numpy as np
import pandas as pd

from common import (DATA, FULL_MEMBERS, KOHLI, PLAYERS, PROCESSED, SACHIN, bat_summary,
                    save_table)

COUNTRY_ALIASES = {"United Arab Emirates": "U.A.E.", "United States of America": "U.S.A.",
                   "Papua New Guinea": "P.N.G."}

print("01 Load & validate")
bat = pd.read_csv(DATA / "odi_Batting_Card.csv")
mat = pd.read_csv(DATA / "odi_Matches_Data.csv")
bowl = pd.read_csv(DATA / "odi_Bowling_Card.csv")
players = pd.read_csv(DATA / "players_info.csv")

# ---- matches
mat["date"] = pd.to_datetime(mat["Match Date"], format="%d-%m-%Y")
empty = mat["date"].isna()
print(f"  matches: {len(mat):,} rows, {empty.sum()} empty placeholder row(s) dropped")
mat = mat[~empty].copy()
mat["year"] = mat["date"].dt.year
mat["venue_country"] = mat["Match Venue (Country)"].replace(COUNTRY_ALIASES)
fm_since = {k: pd.Timestamp(v) for k, v in FULL_MEMBERS.items()}


def is_fm(team, date):
    return team in fm_since and date >= fm_since[team]


mat["full_member_match"] = [is_fm(a, d) and is_fm(b, d) for a, b, d in
                            zip(mat["Team1 Name"], mat["Team2 Name"], mat["date"])]
matches = mat.rename(columns={"Match ID": "match_id", "Team1 Name": "team1",
                              "Team2 Name": "team2", "Team1 Runs Scored": "team1_runs",
                              "Team2 Runs Scored": "team2_runs",
                              "Team1 Wickets Fell": "team1_wkts",
                              "Team2 Wickets Fell": "team2_wkts",
                              "Match Winner": "winner", "Match Result Text": "result"})
matches = matches[["match_id", "date", "year", "team1", "team2", "team1_runs", "team2_runs",
                   "team1_wkts", "team2_wkts", "venue_country", "winner", "result",
                   "full_member_match"]]

# ---- batting: position = order of rows within each team innings (DNB rows included)
bat = bat.rename(columns={"Match ID": "match_id", "batsman": "player_id"})
bat["pos"] = bat.groupby(["match_id", "innings"]).cumcount() + 1
n_rows = len(bat)
bat = bat[bat.player_id.notna()]                       # 12 blank rows (abandoned matches)
dnb = bat.runs.isna()
print(f"  batting card: {n_rows:,} rows; {dnb.sum():,} 'did not bat' rows excluded")
bat = bat[~dnb].copy()
bat["player_id"] = bat.player_id.astype(int)
bat["out"] = bat["isOut"].astype(str).str.upper().eq("TRUE")

inn = bat.merge(matches, on="match_id", how="inner")
inn["opp"] = np.where(inn.team == inn.team1, inn.team2, inn.team1)
inn["chasing"] = inn.innings == 2
inn["venue"] = np.select([inn.venue_country == inn.team, inn.venue_country == inn.opp],
                         ["Home", "Away"], "Neutral")
players["dob"] = pd.to_datetime(players["dob"], format="%d-%m-%Y", errors="coerce")
inn = inn.merge(players[["player_id", "player_name", "dob"]], on="player_id", how="left")
inn["age"] = (inn.date - inn.dob).dt.days / 365.25
inn = inn[["match_id", "date", "year", "innings", "team", "opp", "player_id", "player_name",
           "pos", "runs", "balls", "out", "chasing", "venue", "venue_country", "dob", "age",
           "winner", "full_member_match"]].sort_values(["date", "match_id", "innings", "pos"])
inn.to_pickle(PROCESSED / "innings.pkl")
matches.to_pickle(PROCESSED / "matches.pkl")

# bowling card: 'team' = bowling side, 'opposition' = batting side, 'innings' = batting innings
bowl = bowl.rename(columns={"Match ID": "match_id", "bowler id": "bowler_id"})
bowl = bowl[bowl.bowler_id.notna()].merge(matches[["match_id", "date", "year"]], on="match_id")
bowl.to_pickle(PROCESSED / "bowling.pkl")
print(f"  clean innings: {len(inn):,}; matches: {len(matches):,}; bowling spells: {len(bowl):,}")
print(f"  date range: {matches.date.min():%d %b %Y} to {matches.date.max():%d %b %Y}")

# ---- validation
rows = []
for pid in (SACHIN, KOHLI):
    d = inn[inn.player_id == pid]
    s = bat_summary(d)
    s.update({"player": PLAYERS[pid], "matches_in_data": inn.loc[inn.player_id == pid, "match_id"].nunique(),
              "hundreds": int((d.runs >= 100).sum()), "fifties": int(((d.runs >= 50) & (d.runs < 100)).sum()),
              "highest": int(d.runs.max()), "first": f"{d.date.min():%d %b %Y}",
              "last": f"{d.date.max():%d %b %Y}", "dob": f"{d.dob.iloc[0]:%d %b %Y}"})
    rows.append(s)
val = pd.DataFrame(rows).set_index("player")
val["average"] = val["average"].round(2)
val["strike_rate"] = val["strike_rate"].round(2)
print(val[["innings", "runs", "outs", "average", "strike_rate", "hundreds", "fifties", "first", "last"]].to_string())

sachin = val.loc[PLAYERS[SACHIN]]
official = {"runs": 18426, "average": 44.83, "strike_rate": 86.23, "innings": 452}
for k, v in official.items():
    if not np.isclose(sachin[k], v, atol=0.005):
        raise SystemExit(f"VALIDATION FAILED: Sachin {k} = {sachin[k]} but official is {v}")
print("  OK: Sachin matches his official record (452 inns, 18,426 runs, avg 44.83, SR 86.23)")
kohli = val.loc[PLAYERS[KOHLI]]
if not (kohli.runs == 13848 and kohli.innings == 280):
    raise SystemExit("VALIDATION FAILED: Kohli totals differ from 280 innings / 13,848 runs")
print("  OK: Kohli = 280 innings, 13,848 runs (official figures after the 2023 World Cup final)")
val["official_check"] = ["Matches official: 452 inns, 18,426 runs, 44.83, 86.23",
                         "Matches official at Nov 2023: 280 inns, 13,848 runs"]
save_table(val.reset_index(), "01_validation")
