"""04 - Yearly Average+ and SR+ (like OPS+ in baseball).

For each calendar year, the peer level is the pooled average and strike rate of every
top-order (1-4) innings by batters with at least 10 top-order innings that year
(excluding the player being rated). A player's career benchmark is those yearly peer levels
weighted by how many innings he played in each year.

    Average+ = career average / innings-weighted peer average x 100
    SR+      = career SR      / innings-weighted peer SR      x 100
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (COLORS, INK, KOHLI, MIN_PEER_INNS, MIN_PEER_INNS_LOW, PLAYERS, SACHIN,
                    SHORT, SURFACE, finish, load_innings, plus_arrays, plus_index, save_table, set_style, yearly_peers)

print("04 Yearly Average+ and SR+")
set_style()
inn = load_innings()

career, yearly = [], []
for label, data in [("All matches (headline)", inn),
                    ("Full Member matches only", inn[inn.full_member_match])]:
    for pid in (SACHIN, KOHLI):
        a = plus_arrays(data, pid)
        avg_p, sr_p = plus_index(a)
        career.append({"variant": label, "player": PLAYERS[pid], "innings": len(a["ra"]),
                       "career_avg": a["ra"].sum() / a["out"].sum(),
                       "weighted_peer_avg": a["pa"].mean(), "average_plus": avg_p,
                       "career_sr": 100 * a["rs"].sum() / a["balls"].sum(),
                       "weighted_peer_sr": a["ps"].mean(), "sr_plus": sr_p})
        if label.startswith("All"):
            p = data[data.player_id == pid]
            g = p.groupby("year")
            y = pd.DataFrame({"innings": g.size(), "runs": g.runs.sum(), "outs": g.out.sum(),
                              "avg": g.runs.sum() / g.out.sum().replace(0, np.nan),
                              "sr": 100 * g.runs.sum() / g.balls.sum()})
            y = y.join(yearly_peers(data, pid))
            y["average_plus"] = 100 * y.avg / y.peer_avg
            y["sr_plus"] = 100 * y.sr / y.peer_sr
            y.insert(0, "player", PLAYERS[pid])
            yearly.append(y.reset_index())

career = pd.DataFrame(career).round(2)
yearly = pd.concat(yearly).round(2)
save_table(career, "04_yearly_plus_career")
save_table(yearly, "04_yearly_plus_by_year")
print(f"  peer pool: top-order batters with >= {MIN_PEER_INNS} top-order innings in the year")
print(career.to_string(index=False))

# ---- chart: year-by-year Average+ and SR+
fig, axes = plt.subplots(2, 1, figsize=(11, 7.4), sharex=True)
fig.subplots_adjust(top=0.86, bottom=0.1, left=0.1, right=0.97, hspace=0.25)
for ax, col, label, short in [(axes[0], "average_plus", "Average+ by year", "Average+"),
                              (axes[1], "sr_plus", "SR+ by year", "SR+")]:
    ax.axhline(100, color=INK, lw=1)
    for pid in (SACHIN, KOHLI):
        y = yearly[yearly.player == PLAYERS[pid]]
        y = y[y.innings >= 5]   # very short years are too noisy to plot
        c = career[(career.player == PLAYERS[pid]) & career.variant.str.startswith("All")].iloc[0]
        ax.plot(y.year, y[col], color=COLORS[pid], lw=2,
                label=f"{SHORT[pid]} (career {short} {c[col]:.0f})")
        ax.scatter(y.year, y[col], s=26, color=COLORS[pid], edgecolor=SURFACE, lw=1.5, zorder=3)
    ticks = [t for t in ax.get_yticks() if ax.get_ylim()[0] <= t <= ax.get_ylim()[1]]
    ax.set_yticks(ticks, [f"{t:.0f}" + (" = peers" if t == 100 else "") for t in ticks])
    ax.set_title(label)
    ax.set_xlim(1989, 2024.5)
    ax.legend(loc="upper left" if col == "average_plus" else "upper right", ncol=2)
finish(fig, "Kohli's best years towered higher on average; Sachin led his era more on "
       "scoring rate",
       "Each point = that year's average (top) or strike rate (bottom) ÷ the top-order peer level "
       "that year × 100. Years with < 5 innings not plotted.",
       "04_yearly_plus",
       note=f"Peers = batters with >= {MIN_PEER_INNS} innings at positions 1–4 in that calendar year "
            f"(>= {MIN_PEER_INNS_LOW} in thin years such as 2020–21). Career figures weight each year "
            "by the player's innings.")
