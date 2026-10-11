"""02 - Era context: how much easier did run-scoring get?

Per calendar year: runs per match (decided matches, both teams), run rate (runs per over),
runs per wicket, and the top-order (positions 1-4) batting average and strike rate.
Compares Sachin's career window (1989-2012) with Kohli's (2008-2023).
"""
import matplotlib.pyplot as plt
import pandas as pd

from common import (COLORS, INK, INK2, SURFACE, KOHLI, PROCESSED, SACHIN, SHORT, TOP_ORDER, WINDOWS,
                    finish, load_innings, load_matches, save_table, set_style)

print("02 Era context")
set_style()
m = load_matches()
inn = load_innings()
bowl = pd.read_pickle(PROCESSED / "bowling.pkl")

# team innings: runs and wickets from the match table, legal balls from the bowling card
balls = bowl.groupby(["match_id", "opposition"]).balls.sum().rename("balls").reset_index()
t1 = m[["match_id", "year", "team1", "team1_runs", "team1_wkts"]].set_axis(
    ["match_id", "year", "team", "runs", "wkts"], axis=1)
t2 = m[["match_id", "year", "team2", "team2_runs", "team2_wkts"]].set_axis(
    ["match_id", "year", "team", "runs", "wkts"], axis=1)
ti = pd.concat([t1, t2]).merge(balls, left_on=["match_id", "team"],
                               right_on=["match_id", "opposition"], how="left")
ti = ti[(ti.balls > 0) & ti.runs.notna()]

decided = m[m.winner.notna() & m.team1_runs.notna() & m.team2_runs.notna()
            & ~m.result.str.contains("No result|abandon", case=False, na=False)]
decided = decided.assign(match_runs=decided.team1_runs + decided.team2_runs)

top = inn[inn.pos <= TOP_ORDER]
yr = pd.DataFrame({
    "matches": m.groupby("year").size(),
    "runs_per_match": decided.groupby("year").match_runs.mean(),
    "run_rate": ti.groupby("year").runs.sum() / (ti.groupby("year").balls.sum() / 6),
    "runs_per_wicket": ti.groupby("year").runs.sum() / ti.groupby("year").wkts.sum(),
    "top_order_avg": top.groupby("year").runs.sum() / top.groupby("year").out.sum(),
    "top_order_sr": 100 * top.groupby("year").runs.sum() / top.groupby("year").balls.sum(),
}).round(2)
yr.index.name = "year"
save_table(yr.reset_index(), "02_era_by_year")


def window(df_year_filter):
    d_m, d_ti, d_top = df_year_filter
    return {
        "runs_per_match": d_m.match_runs.mean(),
        "run_rate": d_ti.runs.sum() / (d_ti.balls.sum() / 6),
        "runs_per_wicket": d_ti.runs.sum() / d_ti.wkts.sum(),
        "top_order_avg": d_top.runs.sum() / d_top.out.sum(),
        "top_order_sr": 100 * d_top.runs.sum() / d_top.balls.sum(),
    }


rows = {}
for pid in (SACHIN, KOHLI):
    a, b = WINDOWS[pid]
    sel = lambda d: d[(d.year >= a) & (d.year <= b)]  # noqa: E731
    rows[f"{SHORT[pid]} window ({a}-{b})"] = window((sel(decided), sel(ti), sel(top)))
win = pd.DataFrame(rows).T
win.loc["Change (Kohli vs Sachin window)"] = (win.iloc[1] / win.iloc[0] - 1) * 100
win = win.round(2)
win.index.name = "window"
save_table(win.reset_index(), "02_era_windows")
print(win.to_string())

# ---- chart: four small multiples, career windows shaded
plot = yr[yr.index >= 1975]
panels = [("runs_per_match", "Runs per match (both teams, decided matches)"),
          ("run_rate", "Run rate (runs per over)"),
          ("runs_per_wicket", "Runs per wicket"),
          ("top_order_sr", "Top-order (1–4) strike rate")]
fig, axes = plt.subplots(2, 2, figsize=(11, 7.2), sharex=True)
fig.subplots_adjust(top=0.86, bottom=0.11, left=0.06, right=0.98, hspace=0.28, wspace=0.16)
for ax, (col, label) in zip(axes.flat, panels):
    for pid in (SACHIN, KOHLI):
        a, b = WINDOWS[pid]
        ax.axvspan(a - 0.5, b + 0.5, color=COLORS[pid], alpha=0.10, lw=0)
    ax.plot(plot.index, plot[col], color=INK2, lw=1.8)
    ax.plot(plot.index[-1], plot[col].iloc[-1], "o", ms=5, color=INK2, mec="white", mew=1.5)
    ax.set_title(label, fontsize=10.5)
    lo, hi = plot[col].min(), plot[col].max()
    ax.set_ylim(lo - (hi - lo) * 0.08, hi + (hi - lo) * 0.25)
    for pid, key in ((SACHIN, "Sachin"), (KOHLI, "Kohli")):
        v = win.loc[[i for i in win.index if i.startswith(key)][0], col]
        a, b = WINDOWS[pid]
        ax.hlines(v, a, b, color=COLORS[pid], lw=2.2)
        ax.annotate(f"{key} era avg {v:.1f}" if col != "run_rate" else f"{key} era avg {v:.2f}",
                    (a if pid == SACHIN else b, v), xytext=(0, 7), textcoords="offset points",
                    ha="left" if pid == SACHIN else "right", fontsize=8, color=INK,
                    bbox=dict(boxstyle="round,pad=0.2", fc=SURFACE, ec="none", alpha=0.9))
axes[1, 0].set_xlabel("Year")
axes[1, 1].set_xlabel("Year")
finish(fig, "ODI scoring got faster between the two careers; runs per wicket rose less",
       "Blue shading = Sachin's career (1989–2012); orange = Kohli's (2008–2023); they overlap in "
       "2008–12. Coloured lines = average over each window.",
       "02_era_context", note="2024 covers January to 18 March only.")
