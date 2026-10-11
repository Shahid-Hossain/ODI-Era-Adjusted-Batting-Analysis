"""07 - Extra lenses, all judged against same-match top-order peers where it makes sense.

  a) Same-age comparison (both careers cut at Kohli's age on the cutoff date, ~35)
  b) Best 5-year peak (5 consecutive calendar years, at least 50 innings)
  c) Setting a target vs chasing
  d) Home / away / neutral venues
  e) 50-to-100 conversion and consistency (share of innings of 30+, 50+, under 10)
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (COLORS, INK, INK2, KOHLI, PEER, PLAYERS, PROCESSED, SACHIN, SHORT, SURFACE,
                    TOP_ORDER, finish, match_index, match_table, save_table, set_style)

print("07 Extra lenses")
set_style()
inn = pd.read_pickle(PROCESSED / "innings_adj.pkl")
P = {pid: inn[inn.player_id == pid].set_index("match_id") for pid in (SACHIN, KOHLI)}
MT = {pid: match_table(inn, pid) for pid in (SACHIN, KOHLI)}


def idx_for(pid, mask):
    """Match index on the subset of the player's matches where `mask` (by match_id) holds."""
    mt = MT[pid].loc[mask[mask].index]
    a, s = match_index(mt)
    p = P[pid].loc[mt.index]
    return {"innings": len(mt), "runs": int(p.runs.sum()),
            "avg": p.runs.sum() / p.out.sum(), "sr": 100 * p.runs.sum() / p.balls.sum(),
            "avg_index": a, "sr_index": s}


# ---- a) same age
cut_age = P[KOHLI].age.max()
rows = []
for pid in (SACHIN, KOHLI):
    p = P[pid]
    r = idx_for(pid, p.age <= cut_age)
    r.update({"player": PLAYERS[pid], "span": f"to age {cut_age:.1f}",
              "hundreds": int((p[p.age <= cut_age].runs >= 100).sum())})
    rows.append(r)
r = idx_for(SACHIN, P[SACHIN].age > cut_age)
r.update({"player": PLAYERS[SACHIN], "span": f"after age {cut_age:.1f}",
          "hundreds": int((P[SACHIN][P[SACHIN].age > cut_age].runs >= 100).sum())})
rows.append(r)
same_age = pd.DataFrame(rows)[["player", "span", "innings", "runs", "hundreds", "avg", "sr",
                                "avg_index", "sr_index"]].round(2)
save_table(same_age, "07a_same_age")
print(same_age.to_string(index=False))

# ---- b) best 5-year peak (and the rolling career arc for the chart)
peaks, arc = [], []
for pid in (SACHIN, KOHLI):
    years = P[pid].year
    for start in range(years.min(), years.max() - 3):
        m = years.between(start, start + 4)
        if m.sum() < 50:
            continue
        r = idx_for(pid, m)
        r.update({"player": PLAYERS[pid], "window": f"{start}-{start + 4}", "mid": start + 2})
        arc.append(r)
arc = pd.DataFrame(arc)
for pid in (SACHIN, KOHLI):
    a = arc[arc.player == PLAYERS[pid]]
    for col, label in (("avg_index", "Best 5 years by average index"),
                       ("sr_index", "Best 5 years by SR index")):
        b = a.loc[a[col].idxmax()]
        peaks.append({"player": PLAYERS[pid], "lens": label, "window": b.window,
                      "innings": b.innings, "avg": b.avg, "sr": b.sr,
                      "avg_index": b.avg_index, "sr_index": b.sr_index})
peaks = pd.DataFrame(peaks).round(2)
save_table(peaks, "07b_best_5yr_peak")
save_table(arc.round(2), "07b_rolling_5yr")
print(peaks.to_string(index=False))

# ---- c) + d) splits
splits = []
for pid in (SACHIN, KOHLI):
    p = P[pid]
    won = p.winner == p.team
    for label, m in [("Setting a target (bat 1st)", ~p.chasing), ("Chasing (bat 2nd)", p.chasing),
                     ("Chasing, team won", p.chasing & won),
                     ("Home", p.venue == "Home"), ("Away", p.venue == "Away"),
                     ("Neutral", p.venue == "Neutral")]:
        r = idx_for(pid, m)
        r.update({"player": PLAYERS[pid], "split": label})
        splits.append(r)
splits = pd.DataFrame(splits)[["player", "split", "innings", "runs", "avg", "sr",
                               "avg_index", "sr_index"]].round(2)
save_table(splits, "07cd_splits")
print(splits.to_string(index=False))

# ---- e) conversion & consistency vs same-match peers
cons = []
for pid in (SACHIN, KOHLI):
    p = P[pid]
    q = inn[(inn.pos <= TOP_ORDER) & (inn.player_id != pid) & inn.match_id.isin(p.index)]
    for who, d in (("player", p), ("peers", q)):
        fifty_plus = (d.runs >= 50).sum()
        cons.append({"player": PLAYERS[pid], "group": who, "innings": len(d),
                     "fifty_plus": int(fifty_plus), "hundreds": int((d.runs >= 100).sum()),
                     "conversion_50_to_100": (d.runs >= 100).sum() / fifty_plus,
                     "share_30_plus": (d.runs >= 30).mean(), "share_50_plus": (d.runs >= 50).mean(),
                     "share_under_10": (d.runs < 10).mean(), "median_score": d.runs.median()})
cons = pd.DataFrame(cons).round(3)
save_table(cons, "07e_conversion_consistency")
print(cons.to_string(index=False))

# ---- charts
# 1) cumulative runs by age
fig, ax = plt.subplots(figsize=(11, 5))
fig.subplots_adjust(top=0.82, bottom=0.14, left=0.08, right=0.95)
for pid in (SACHIN, KOHLI):
    p = P[pid].sort_values("date")
    ax.plot(p.age, p.runs.cumsum(), color=COLORS[pid], lw=2, label=SHORT[pid])
    at = p[p.age <= cut_age]
    ax.scatter(at.age.iloc[-1], at.runs.cumsum().iloc[-1], s=60, color=COLORS[pid],
               edgecolor=SURFACE, lw=2, zorder=3)
    ax.annotate(f"{SHORT[pid]}: {int(at.runs.sum()):,} runs by {cut_age:.0f}",
                (at.age.iloc[-1], at.runs.cumsum().iloc[-1]),
                xytext=(-10, 8) if pid == SACHIN else (10, -4), textcoords="offset points",
                ha="right" if pid == SACHIN else "left", va="bottom" if pid == SACHIN else "top",
                fontsize=9, color=INK)
ax.axvline(cut_age, color=INK2, lw=1)
ax.annotate(f"Kohli's age at cutoff ({cut_age:.1f})", (cut_age, 1000), xytext=(5, 0),
            textcoords="offset points", fontsize=8.5, color=INK2)
ax.set_xlabel("Age (years)")
ax.yaxis.set_major_locator(plt.MultipleLocator(3000))
ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}K")
ax.legend(loc="upper left")
sa = same_age.set_index(["player", "span"])
s_row = sa.loc[(PLAYERS[SACHIN], f"to age {cut_age:.1f}")]
k_row = sa.loc[(PLAYERS[KOHLI], f"to age {cut_age:.1f}")]
finish(fig, "At the same age Sachin had more runs; Kohli had more runs per dismissal",
       f"Cumulative ODI runs by age. To age {cut_age:.0f}: Sachin average index "
       f"{s_row.avg_index:.0f}, SR index {s_row.sr_index:.0f}; Kohli {k_row.avg_index:.0f} "
       f"and {k_row.sr_index:.0f}. Sachin debuted at 16, Kohli at 19.",
       "07a_same_age")

# 2) rolling 5-year career arc
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
fig.subplots_adjust(top=0.8, bottom=0.16, left=0.07, right=0.98, wspace=0.2)
for ax, col, label in ((axes[0], "avg_index", "Average index, rolling 5 years"),
                       (axes[1], "sr_index", "SR index, rolling 5 years")):
    ax.axhline(100, color=INK, lw=1)
    for pid in (SACHIN, KOHLI):
        a = arc[arc.player == PLAYERS[pid]]
        ax.plot(a.mid, a[col], color=COLORS[pid], lw=2, label=SHORT[pid])
        b = a.loc[a[col].idxmax()]
        ax.scatter(b.mid, b[col], s=60, color=COLORS[pid], edgecolor=SURFACE, lw=2, zorder=3)
        ax.annotate(f"peak {b.window}: {b[col]:.0f}", (b.mid, b[col]), xytext=(0, 8),
                    textcoords="offset points", ha="center", fontsize=8.5, color=INK)
    ax.set_title(label)
    ax.set_xlabel("Middle year of the 5-year window")
    lo, hi = ax.get_ylim()
    ax.set_ylim(min(lo, 95), hi + (hi - lo) * 0.12)
axes[0].legend(loc="upper left")
finish(fig, "Career arcs: Kohli's peak was higher on average; Sachin's peak SR was higher",
       "Match index (100 = same-match top-order peers) over every 5-calendar-year window with "
       "at least 50 innings.", "07b_career_arc")

# 3) splits
order = ["Setting a target (bat 1st)", "Chasing (bat 2nd)", "Chasing, team won",
         "Home", "Away", "Neutral"]
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
fig.subplots_adjust(top=0.8, bottom=0.17, left=0.2, right=0.98, wspace=0.08)
for ax, col, label in ((axes[0], "avg_index", "Average index"), (axes[1], "sr_index", "SR index")):
    ax.axvline(100, color=INK, lw=1)
    for pid in (SACHIN, KOHLI):
        d = splits[splits.player == PLAYERS[pid]].set_index("split").loc[order]
        y = np.arange(len(order))[::-1] + (0.14 if pid == SACHIN else -0.14)
        ax.hlines(y, 100, d[col], color=COLORS[pid], lw=2, alpha=0.35)
        ax.scatter(d[col], y, s=60, color=COLORS[pid], edgecolor=SURFACE, lw=2, zorder=3,
                   label=SHORT[pid])
        for yi, v, n in zip(y, d[col], d.innings):
            ax.annotate(f"{v:.0f} ({n})", (v, yi), xytext=(7, 0), textcoords="offset points",
                        va="center", fontsize=7.5, color=INK2)
    ax.set_yticks(np.arange(len(order))[::-1], order, color=INK)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_xlim(90, 270 if col == "avg_index" else 140)
    ax.set_title(f"{label} (100 = same-match peers)")
axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=2)
finish(fig, "Kohli's average edge: chases and away games. Sachin's tempo edge: every situation",
       "Match index by situation (note the different scales). Number in brackets = innings.",
       "07cd_splits",
       note="'Chasing, team won' selects innings by the result, which flatters every batter; "
            "compare the two players with each other, not with 100.")

# 4) conversion & consistency
metrics = [("share_30_plus", "Share of innings 30+"), ("share_50_plus", "Share of innings 50+"),
           ("share_under_10", "Share of innings under 10"),
           ("conversion_50_to_100", "50s turned into 100s")]
fig, axes = plt.subplots(1, 4, figsize=(11, 4.4))
fig.subplots_adjust(top=0.76, bottom=0.18, left=0.04, right=0.99, wspace=0.3)
for ax, (col, label) in zip(axes, metrics):
    for k, pid in enumerate((SACHIN, KOHLI)):
        c = cons[cons.player == PLAYERS[pid]].set_index("group")
        ax.bar(k, c.loc["player", col] * 100, width=0.6, color=COLORS[pid], zorder=2)
        ax.scatter(k, c.loc["peers", col] * 100, marker="_", s=600, lw=2, color=INK, zorder=3,
                   label="Same-match top-order peers" if k == 0 else None)
        top = max(c.loc["player", col], c.loc["peers", col]) * 100
        ax.annotate(f"{c.loc['player', col] * 100:.0f}%", (k, top),
                    xytext=(0, 6), textcoords="offset points", ha="center", fontsize=9, color=INK)
    ax.set_xticks([0, 1], [SHORT[SACHIN], SHORT[KOHLI]], color=INK)
    ax.set_title(label, fontsize=9.5)
    ax.set_ylim(0, max(ax.get_ylim()[1], 10) * 1.12)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=1)
finish(fig, "Kohli was the more reliable and the better converter of starts",
       "Bars = player; black tick = the other top-order batters in the same matches.",
       "07e_consistency")
