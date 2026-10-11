"""08 - Old vs new: the original EAA/EASR next to the rebuilt indexes.

Also re-runs the ORIGINAL method on this dataset (benchmark = mean average and mean strike
rate of the top 10 career averages among batters whose careers fall inside each era), so we
can separate "different data" from "different method".
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (COLORS, INK, INK2, KOHLI, PLAYERS, PROCESSED, SACHIN, SHORT, SURFACE, TABLES,
                    finish, save_table, set_style)

print("08 Old vs new")
set_style()
inn = pd.read_pickle(PROCESSED / "innings_adj.pkl")
boot = pd.read_csv(TABLES / "06_bootstrap_ci.csv")


def pick(index, measure, who):
    return boot[(boot["index"] == index) & (boot.measure == measure)][who].iloc[0]


# ---- original method re-run on this data
g = inn.groupby("player_id")
car = pd.DataFrame({"name": g.player_name.first(), "first": g.year.min(), "last": g.year.max(),
                    "innings": g.size(), "runs": g.runs.sum(), "outs": g.out.sum(),
                    "balls": g.balls.sum()})
car["avg"] = car.runs / car.outs
car["sr"] = 100 * car.runs / car.balls
eras = {SACHIN: (car["first"] >= 1989) & (car["last"] <= 2012),
        KOHLI: car["first"] >= 2008}
replica, elite_lists = {}, []
for pid, mask in eras.items():
    pool = car[mask & (car.innings >= 50) & (car.index != pid)].nlargest(10, "avg")
    elite_lists.append(pool.assign(benchmark_for=PLAYERS[pid]).reset_index())
    me = car.loc[pid]
    replica[pid] = (100 * me.avg / pool.avg.mean(), 100 * me.sr / pool.sr.mean(),
                    pool.avg.mean(), pool.sr.mean())
save_table(pd.concat(elite_lists)[["benchmark_for", "name", "first", "last", "innings", "avg", "sr"]]
           .round(2), "08_original_method_elite_peers")

rows = [
    ("Raw career average", 44.83, 58.20, car.loc[SACHIN].avg, car.loc[KOHLI].avg),
    ("Raw career strike rate", 86.23, 93.50, car.loc[SACHIN].sr, car.loc[KOHLI].sr),
    ("EAA (original) / original method re-run here", 102.67, 107.78, replica[SACHIN][0], replica[KOHLI][0]),
    ("EASR (original) / original method re-run here", 110.10, 104.40, replica[SACHIN][1], replica[KOHLI][1]),
    ("NEW Match index: average", np.nan, np.nan, pick("Match index", "Average", "sachin"),
     pick("Match index", "Average", "kohli")),
    ("NEW Match index: strike rate", np.nan, np.nan, pick("Match index", "Strike rate", "sachin"),
     pick("Match index", "Strike rate", "kohli")),
    ("NEW Bowling-adjusted Average+", np.nan, np.nan,
     pick("Average+ / SR+, bowling-adjusted", "Average", "sachin"),
     pick("Average+ / SR+, bowling-adjusted", "Average", "kohli")),
    ("NEW Bowling-adjusted SR+", np.nan, np.nan,
     pick("Average+ / SR+, bowling-adjusted", "Strike rate", "sachin"),
     pick("Average+ / SR+, bowling-adjusted", "Strike rate", "kohli")),
]
ovn = pd.DataFrame(rows, columns=["metric", "old_sachin", "old_kohli", "new_sachin", "new_kohli"])
ovn["old_gap_kohli_minus_sachin"] = ovn.old_kohli - ovn.old_sachin
ovn["new_gap_kohli_minus_sachin"] = ovn.new_kohli - ovn.new_sachin
ovn = ovn.round(2)
save_table(ovn, "08_old_vs_new")
print(ovn.to_string(index=False))
print(f"  original-method benchmarks on this data: Sachin era avg {replica[SACHIN][2]:.2f} / "
      f"SR {replica[SACHIN][3]:.2f}; Kohli era avg {replica[KOHLI][2]:.2f} / SR {replica[KOHLI][3]:.2f}")

# ---- chart: old vs new, average and strike rate side by side
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
fig.subplots_adjust(top=0.78, bottom=0.2, left=0.27, right=0.98, wspace=0.08)
labels = ["Original EAA / EASR", "New: match index", "New: bowling-adj. Average+ / SR+"]
groups = [("Average", [ovn.loc[2], ovn.loc[4], ovn.loc[6]]),
          ("Strike rate", [ovn.loc[3], ovn.loc[5], ovn.loc[7]])]
for ax, (title, rs) in zip(axes, groups):
    ax.axvline(100, color=INK, lw=1)
    for i, r in enumerate(rs):
        y = len(rs) - 1 - i
        old = i == 0
        for pid, col in ((SACHIN, "sachin"), (KOHLI, "kohli")):
            v = r[f"old_{col}"] if old else r[f"new_{col}"]
            yy = y + (0.13 if pid == SACHIN else -0.13)
            ax.hlines(yy, 100, v, color=COLORS[pid], lw=2, alpha=0.35)
            ax.scatter(v, yy, s=70, color=COLORS[pid], edgecolor=SURFACE, lw=2, zorder=3,
                       label=SHORT[pid] if i == 0 else None)
            ax.annotate(f"{v:.0f}", (v, yy), xytext=(7, 0), textcoords="offset points",
                        va="center", fontsize=8.5, color=INK2)
    ax.set_yticks(range(len(rs))[::-1], labels, color=INK)   # same rows in both panels
    ax.set_title(f"{title} (100 = benchmark)")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_xlim(95, 165)
    ax.set_ylim(-0.6, len(rs) - 0.4)
axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=2)
finish(fig, "Same direction as the original; the average gap is now much wider",
       "Original = vs the 10 best career averages of the era. New = vs all top-order batters in "
       "the same matches / years.",
       "08_old_vs_new")
