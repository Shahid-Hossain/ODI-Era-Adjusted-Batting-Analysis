# Data

## Source and credit

**ODI Cricket Matches Dataset (1971–2024) by Bhuvanesh Prasad, Kaggle, Apache 2.0 licence, originally sourced from ESPNcricinfo.**

Dataset page: <https://www.kaggle.com/datasets/bhuvaneshprasad/odi-matches-historical-data-since-1971>

The four CSV files in this folder are redistributed unchanged under the Apache License 2.0. A copy of the licence is included at [`LICENSE-APACHE-2.0.txt`](LICENSE-APACHE-2.0.txt). All credit for collecting and publishing the data belongs to the dataset author and to ESPNcricinfo. This project uses these files only; nothing else is downloaded.

**Coverage: every men's ODI from 5 January 1971 to 18 March 2024.** Virat Kohli's career is therefore covered up to and including the 2023 World Cup final (19 November 2023). Sachin Tendulkar's ODI career (1989–2012) is complete.

---

## Files

| File | Rows | One row is | Used for |
|---|---|---|---|
| `odi_Batting_Card.csv` | 103,225 | one batter in one team innings | every batting number in the project |
| `odi_Matches_Data.csv` | 4,745 | one match | dates, teams, venue country, result |
| `odi_Bowling_Card.csv` | 56,514 | one bowler in one team innings | rating the bowling attacks each batter faced |
| `players_info.csv` | 6,701 | one player | names and dates of birth (for ages) |

All four files join on `Match ID`; batters and bowlers join to `players_info.csv` on `player_id`.

### `odi_Batting_Card.csv`

`Match ID, innings, team, batsman, runs, balls, fours, sixes, strikeRate, isOut, wicketType, fielders, bowler`

- `batsman` is a player ID, not a name.
- `innings` is 1 (batting first) or 2 (chasing).
- **Row order within each team innings is the batting order.** The first row is the opener, and so on. The pipeline uses this to define the top order (positions 1–4).
- **Rows with blank `runs` and `balls` are "did not bat".** There are 20,174 of them. They are kept when working out batting positions and then dropped from all batting statistics.
- 12 rows have no batter at all. They are placeholders for six matches with no play (five abandoned after the toss, plus the empty match row noted below), and are dropped.

### `odi_Matches_Data.csv`

- `Match Date` is in `DD-MM-YYYY` format.
- `Team1` is the side that batted first in 99.9% of matches.
- `Match Venue (Country)` gives home/away/neutral. A few country names differ from team names (e.g. "United Arab Emirates" vs "U.A.E."); the pipeline maps them.
- One row (Match ID 736451) is an empty placeholder with no date or teams, and is dropped.
- `ODI Match No` is this dataset's own running number, not the official ODI number. A handful of official matches are not in the file (most likely washouts with no scorecard), which is why Sachin has 457 matches here against his official 463, and Kohli 288 against 292. Their innings and runs match the official figures exactly, so no batting is missing.

### `odi_Bowling_Card.csv`

- **`team` is the bowling side, `opposition` is the batting side, and `innings` is the innings being bowled at.** So the bowling card for innings 1 is the attack that the innings-1 batters faced.
- Columns used: `bowler id`, `balls`, `conceded`, `wickets`. `conceded` excludes byes and leg byes, as on any scorecard.

### `players_info.csv`

- `dob` is in `DD-MM-YYYY` format. Sachin Tendulkar is `player_id` 1934 (born 24-04-1973); Virat Kohli is `player_id` 49752 (born 05-11-1988).

---

## Validation

[`src/01_load_validate.py`](../src/01_load_validate.py) stops with an error unless Sachin's totals match his official ODI record. They do:

| Player | Innings | Runs | Average | Strike rate |
|---|---|---|---|---|
| Sachin Tendulkar | 452 | 18,426 | 44.83 | 86.23 |
| Virat Kohli (to Nov 2023) | 280 | 13,848 | 58.68 | 93.59 |

---

## Derived files

`data/processed/` holds intermediate tables written by the pipeline (clean innings, matches, bowling, and innings with attack-strength factors). It is rebuilt on every run and is not committed.
