"""Shared paths, constants, chart style and index calculations.

Every numbered script imports from here so that the definitions of
"peer", "index" and the chart look are written exactly once.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PROCESSED = DATA / "processed"
CHARTS = ROOT / "outputs" / "charts"
TABLES = ROOT / "outputs" / "tables"
for _p in (PROCESSED, CHARTS, TABLES):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- constants
SACHIN, KOHLI = 1934, 49752
PLAYERS = {SACHIN: "Sachin Tendulkar", KOHLI: "Virat Kohli"}
SHORT = {SACHIN: "Sachin", KOHLI: "Kohli"}
CUTOFF = "18 March 2024"
CUTOFF_NOTE = (
    "Data: ODI Cricket Matches Dataset (1971–2024), Kaggle / ESPNcricinfo. "
    f"All ODIs to {CUTOFF}; Kohli's career covered to the 2023 World Cup final."
)
TOP_ORDER = 4          # batting positions 1-4 count as "top order"
MIN_PEER_INNS = 10     # yearly peer pool: top-order innings needed in a year...
MIN_PEER_INNS_LOW = 5  # ...relaxed to this in thin years (e.g. COVID 2020-21)
MIN_PEER_BATTERS = 20  # a year is "thin" if fewer than this many batters qualify
N_BOOT = 2000
SEED = 2024

# ODI Full Members and the date each gained full status (for the robustness check).
FULL_MEMBERS = {
    "Australia": "1971-01-01", "England": "1971-01-01", "India": "1971-01-01",
    "New Zealand": "1971-01-01", "Pakistan": "1971-01-01", "West Indies": "1971-01-01",
    "South Africa": "1971-01-01", "Sri Lanka": "1981-07-21", "Zimbabwe": "1992-07-06",
    "Bangladesh": "2000-06-26", "Ireland": "2017-06-22", "Afghanistan": "2017-06-22",
}

# ---------------------------------------------------------------- chart style
COLORS = {SACHIN: "#2a78d6", KOHLI: "#eb6834"}   # validated categorical pair
PEER = "#898781"                                 # peer / benchmark grey
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
WINDOWS = {SACHIN: (1989, 2012), KOHLI: (2008, 2023)}


def set_style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "DejaVu Sans", "font.size": 10,
        "text.color": INK, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlecolor": INK, "legend.frameon": False, "legend.fontsize": 9,
        "lines.linewidth": 2, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "xtick.major.size": 0, "ytick.major.size": 0,
    })


def finish(fig, title, subtitle, name, note=None):
    """Add a left-aligned title, subtitle and the data/cutoff footnote, then save."""
    h = fig.get_figheight()
    fig.text(0.01, 1 - 0.12 / h, title, ha="left", va="top", fontsize=14, weight="bold", color=INK)
    fig.text(0.01, 1 - 0.46 / h, subtitle, ha="left", va="top", fontsize=10, color=INK2)
    foot = CUTOFF_NOTE if note is None else f"{note}\n{CUTOFF_NOTE}"
    fig.text(0.01, 0.005, foot, ha="left", va="bottom", fontsize=7.5, color=MUTED)
    path = CHARTS / f"{name}.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    print(f"  chart -> {path.relative_to(ROOT)}")


def save_table(df, name, index=False):
    path = TABLES / f"{name}.csv"
    df.to_csv(path, index=index)
    print(f"  table -> {path.relative_to(ROOT)}")
    return path


def load_innings():
    return pd.read_pickle(PROCESSED / "innings.pkl")


def load_matches():
    return pd.read_pickle(PROCESSED / "matches.pkl")


# ---------------------------------------------------------------- core metrics
def bat_summary(d, runs="runs"):
    outs = d["out"].sum()
    r = d[runs].sum()
    return {
        "innings": len(d), "runs": round(r, 1), "outs": int(outs),
        "average": r / outs if outs else np.nan,
        "strike_rate": 100 * r / d["balls"].sum() if d["balls"].sum() else np.nan,
    }


def match_table(inn, pid, avg_col="runs", sr_col="runs", peers="all"):
    """One row per match the player batted in: his totals and his same-match peers' totals.

    Peers = every other batter at positions 1-4 in the same match (both teams by default;
    'team' = only his team-mates, 'opp' = only the opposition top order).
    """
    p = inn[inn.player_id == pid]
    q = inn[(inn.pos <= TOP_ORDER) & (inn.player_id != pid) & inn.match_id.isin(p.match_id)]
    q = q.merge(p[["match_id", "team"]].rename(columns={"team": "p_team"}), on="match_id")
    if peers == "team":
        q = q[q.team == q.p_team]
    elif peers == "opp":
        q = q[q.team != q.p_team]
    pm = p.groupby("match_id").agg(p_ra=(avg_col, "sum"), p_rs=(sr_col, "sum"),
                                   p_out=("out", "sum"), p_balls=("balls", "sum"))
    qm = q.groupby("match_id").agg(q_ra=(avg_col, "sum"), q_rs=(sr_col, "sum"),
                                   q_out=("out", "sum"), q_balls=("balls", "sum"))
    return pm.join(qm, how="left").fillna(0.0)


def match_index(mt):
    """Career index (100 = same-match top-order peers) from a match_table."""
    s = mt.sum()
    avg = (s.p_ra / s.p_out) / (s.q_ra / s.q_out) * 100
    sr = (s.p_rs / s.p_balls) / (s.q_rs / s.q_balls) * 100
    return avg, sr


def yearly_peers(inn, exclude_pid, avg_col="runs", sr_col="runs"):
    """Top-order peer average and strike rate per calendar year.

    Pool = innings at positions 1-4 by batters with >= MIN_PEER_INNS top-order innings
    that year (>= MIN_PEER_INNS_LOW in thin years where fewer than MIN_PEER_BATTERS
    qualify), excluding the player being rated.
    """
    top = inn[(inn.pos <= TOP_ORDER) & (inn.player_id != exclude_pid)]
    n = top.groupby(["player_id", "year"]).size().rename("n")
    top = top.join(n, on=["player_id", "year"])
    qualified = n[n >= MIN_PEER_INNS].groupby(level="year").size()
    thin = qualified.reindex(top.year.unique(), fill_value=0) < MIN_PEER_BATTERS
    need = np.where(top.year.map(thin), MIN_PEER_INNS_LOW, MIN_PEER_INNS)
    top = top[top.n >= need]
    g = top.groupby("year")
    return pd.DataFrame({
        "peer_avg": g[avg_col].sum() / g["out"].sum(),
        "peer_sr": 100 * g[sr_col].sum() / g["balls"].sum(),
        "peer_innings": g.size(),
        "peer_batters": g["player_id"].nunique(),
    })


def plus_arrays(inn, pid, avg_col="runs", sr_col="runs"):
    """Per-innings arrays for Average+/SR+: runs, outs, balls, and the peer level that year."""
    p = inn[inn.player_id == pid]
    yp = yearly_peers(inn, pid, avg_col, sr_col)
    j = p.join(yp, on="year")
    return {"ra": j[avg_col].to_numpy(float), "rs": j[sr_col].to_numpy(float),
            "out": j["out"].to_numpy(float), "balls": j["balls"].to_numpy(float),
            "pa": j["peer_avg"].to_numpy(float), "ps": j["peer_sr"].to_numpy(float)}


def plus_index(a):
    """Average+ = career average / innings-weighted peer average x 100 (same for SR+)."""
    avg = (a["ra"].sum() / a["out"].sum()) / a["pa"].mean() * 100
    sr = (100 * a["rs"].sum() / a["balls"].sum()) / a["ps"].mean() * 100
    return avg, sr


def to_markdown(df):
    """Minimal Markdown table (avoids an extra dependency)."""
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "|" + "|".join("---" for _ in df.columns) + "|"
    body = ["| " + " | ".join(map(str, r)) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep, *body])
