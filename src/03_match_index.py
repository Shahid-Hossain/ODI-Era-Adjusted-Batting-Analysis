"""03 - Match-adjusted index: each player vs the other top-order batters in the SAME matches.

For every match Sachin or Kohli batted in, the comparison group is every other batter at
positions 1-4 in that match (both teams). Same ground, same pitch, same day, same era.

    Average index = player's average  / peers' average in those matches  x 100
    SR index      = player's SR       / peers' SR in those matches       x 100

100 = exactly peer level; 120 = 20% better than the top-order batters around him.
Variants: team-mates only, opposition only, and Full Member matches only (robustness).
"""
import matplotlib.pyplot as plt
import pandas as pd

from common import (COLORS, INK, INK2, KOHLI, PEER, PLAYERS, SACHIN, SHORT, SURFACE,
                    finish, load_innings, match_index, match_table, save_table, set_style)

print("03 Match-adjusted index")
set_style()
inn = load_innings()

rows = []
variants = [("All top-order peers (headline)", inn, "all"),
            ("Team-mates only", inn, "team"),
            ("Opposition top order only", inn, "opp"),
            ("Full Member matches only", inn[inn.full_member_match], "all")]
for label, data, peers in variants:
    for pid in (SACHIN, KOHLI):
        mt = match_table(data, pid, peers=peers)
        s = mt.sum()
        a, r = match_index(mt)
        rows.append({
            "variant": label, "player": PLAYERS[pid], "matches": len(mt),
            "player_avg": s.p_ra / s.p_out, "peer_avg": s.q_ra / s.q_out, "avg_index": a,
            "player_sr": 100 * s.p_rs / s.p_balls, "peer_sr": 100 * s.q_rs / s.q_balls,
            "sr_index": r, "peer_innings": int(data[(data.pos <= 4) & (data.player_id != pid)
                                                   & data.match_id.isin(mt.index)].shape[0])
            if peers == "all" else None,
        })
res = pd.DataFrame(rows).round(2)
save_table(res, "03_match_index")
print(res[["variant", "player", "matches", "player_avg", "peer_avg", "avg_index",
           "player_sr", "peer_sr", "sr_index"]].to_string(index=False))

# ---- chart: player vs same-match peers (dumbbell), average and strike rate
head = res[res.variant.str.startswith("All")].set_index("player")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
fig.subplots_adjust(top=0.78, bottom=0.2, left=0.13, right=0.97, wspace=0.35)
for ax, (pcol, qcol, icol, label) in zip(axes, [
        ("player_avg", "peer_avg", "avg_index", "Batting average"),
        ("player_sr", "peer_sr", "sr_index", "Strike rate")]):
    for y, pid in enumerate((KOHLI, SACHIN)):
        r = head.loc[PLAYERS[pid]]
        ax.plot([r[qcol], r[pcol]], [y, y], color="#d8d7d0", lw=6, solid_capstyle="round", zorder=1)
        ax.scatter(r[qcol], y, s=90, color=PEER, edgecolor=SURFACE, lw=2, zorder=3)
        ax.scatter(r[pcol], y, s=110, color=COLORS[pid], edgecolor=SURFACE, lw=2, zorder=3)
        ax.annotate(f"{r[qcol]:.1f}", (r[qcol], y), xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK2)
        ax.annotate(f"{r[pcol]:.1f}", (r[pcol], y), xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK, weight="bold")
        ax.annotate(f"index {r[icol]:.0f}", (r[pcol], y), xytext=(12, 0),
                    textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.set_yticks([0, 1], [SHORT[KOHLI], SHORT[SACHIN]], color=INK, fontsize=10)
    ax.set_ylim(-0.7, 1.6)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_title(label)
    lo = min(head[qcol].min(), head[pcol].min()); hi = max(head[qcol].max(), head[pcol].max())
    ax.set_xlim(lo - (hi - lo) * 0.25, hi + (hi - lo) * 0.45)
axes[0].scatter([], [], s=70, color=PEER, label="Other top-order batters in the same matches")
axes[0].scatter([], [], s=70, color=COLORS[SACHIN], label="Sachin")
axes[0].scatter([], [], s=70, color=COLORS[KOHLI], label="Kohli")
axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.12), ncol=3, fontsize=9)
finish(fig, "Same match, same conditions: how far each player stood above his peers",
       "Grey dot = the other top-order (1–4) batters in the matches each player batted in, "
       "both teams. Index = player ÷ peers × 100.",
       "03_match_index")
