"""05 - Opposition strength: adjust for the quality of the bowling attack faced.

1. Rate every bowler before every match using only his previous 3 years of ODIs:
   bowling average (runs per wicket) and economy (runs per ball). Only spells against
   Full Member batting line-ups count, so Associate bowlers are not flattered by records
   built against other Associates.
   Bowlers with little history are pulled toward the league norm (shrinkage), so a debutant
   counts as "average", not as "elite" or "terrible".
2. An attack's strength in a team innings = its bowlers' ratings weighted by balls bowled,
   divided by the league norm for the same 3-year window.
   attack_avg_factor 1.10 = this attack concedes 10% more runs per wicket than a typical attack.
3. Adjusted runs = runs / factor (runs vs weak attacks are discounted, vs strong attacks
   credited). Average uses the bowling-average factor; strike rate uses the economy factor.
4. Re-run Average+/SR+ and the match index with adjusted runs - for the player AND his peers.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (COLORS, FULL_MEMBERS, INK, INK2, KOHLI, PEER, PLAYERS, PROCESSED, SACHIN, SHORT, SURFACE,
                    TOP_ORDER, WINDOWS, finish, load_innings, match_index, match_table,
                    plus_arrays, plus_index, save_table, set_style)

WINDOW = pd.Timedelta(days=3 * 365)
K_BALLS = 300   # shrinkage: economy rating behaves as if +50 overs at league economy
K_WKTS = 10     # shrinkage: average rating behaves as if +10 wickets at league average

print("05 Opposition (bowling attack) adjustment")
set_style()
inn = load_innings()
bowl = pd.read_pickle(PROCESSED / "bowling.pkl").sort_values("date").reset_index(drop=True)


def trailing(dates, values, query_dates):
    """Sum of `values` with date in [query - 3y, query) for each query date (dates sorted)."""
    c = np.vstack([np.zeros((1, values.shape[1])), np.cumsum(values, axis=0)])
    end = np.searchsorted(dates, query_dates, side="left")
    start = np.searchsorted(dates, query_dates - WINDOW, side="left")
    return c[end] - c[start]


cols = ["conceded", "balls", "wickets"]
fm_since = bowl.opposition.map({k: pd.Timestamp(v) for k, v in FULL_MEMBERS.items()})
bowl["vs_full_member"] = bowl.date >= fm_since          # NaT (Associate) -> False
rated = bowl[cols].where(bowl.vs_full_member, 0.0)      # spells that feed the ratings

# league norm for each spell's trailing window
daily = rated.groupby(bowl.date).sum()
lg = trailing(daily.index.values, daily.values, bowl.date.values)
with np.errstate(invalid="ignore", divide="ignore"):    # 1971: no history yet
    bowl["lg_rpb"] = lg[:, 0] / lg[:, 1]
    bowl["lg_avg"] = lg[:, 0] / lg[:, 2]

# each bowler's own trailing record (strictly before the match date)
prior = np.zeros((len(bowl), 3))
for _, idx in bowl.groupby("bowler_id").indices.items():
    g = bowl.loc[idx]
    prior[idx] = trailing(g.date.values, rated.loc[idx].values.astype(float), g.date.values)
bowl[["prior_runs", "prior_balls", "prior_wkts"]] = prior
bowl["rating_rpb"] = (bowl.prior_runs + K_BALLS * bowl.lg_rpb) / (bowl.prior_balls + K_BALLS)
bowl["rating_avg"] = (bowl.prior_runs + K_WKTS * bowl.lg_avg) / (bowl.prior_wkts + K_WKTS)
bowl["rel_rpb"] = bowl.rating_rpb / bowl.lg_rpb
bowl["rel_avg"] = bowl.rating_avg / bowl.lg_avg

ok = bowl[(bowl.balls > 0) & bowl.rel_avg.notna() & bowl.rel_rpb.notna()]
w = ok.balls
attack = pd.DataFrame({
    "attack_avg_factor": (ok.rel_avg * w).groupby([ok.match_id, ok.innings]).sum()
    / w.groupby([ok.match_id, ok.innings]).sum(),
    "attack_sr_factor": (ok.rel_rpb * w).groupby([ok.match_id, ok.innings]).sum()
    / w.groupby([ok.match_id, ok.innings]).sum(),
}).reset_index()

inn = inn.merge(attack, on=["match_id", "innings"], how="left")
inn[["attack_avg_factor", "attack_sr_factor"]] = inn[["attack_avg_factor",
                                                      "attack_sr_factor"]].fillna(1.0)
inn["runs_adj_avg"] = inn.runs / inn.attack_avg_factor
inn["runs_adj_sr"] = inn.runs / inn.attack_sr_factor
inn.to_pickle(PROCESSED / "innings_adj.pkl")

# ---- strength of attacks faced
top_window = inn[(inn.pos <= TOP_ORDER) & inn.year.between(1989, 2023)]
cuts = top_window.attack_avg_factor.quantile([1 / 3, 2 / 3]).values
inn["attack_tier"] = pd.cut(inn.attack_avg_factor, [-np.inf, *cuts, np.inf],
                            labels=["Strong attack", "Middle", "Weak attack"])
faced = []
for pid in (SACHIN, KOHLI):
    p = inn[inn.player_id == pid]
    a, b = WINDOWS[pid]
    peers = inn[(inn.pos <= TOP_ORDER) & inn.year.between(a, b) & (inn.player_id != pid)]
    faced.append({
        "player": PLAYERS[pid],
        "mean_attack_avg_factor": p.attack_avg_factor.mean(),
        "mean_attack_sr_factor": p.attack_sr_factor.mean(),
        "peer_mean_attack_avg_factor": peers.attack_avg_factor.mean(),
        "share_innings_vs_strong": (p.attack_tier == "Strong attack").mean(),
        "share_innings_vs_weak": (p.attack_tier == "Weak attack").mean(),
    })
faced = pd.DataFrame(faced).round(3)
save_table(faced, "05_attack_faced")
print(faced.to_string(index=False))

tiers = []
for pid in (SACHIN, KOHLI):
    for tier, d in inn[inn.player_id == pid].groupby("attack_tier", observed=True):
        a, b = WINDOWS[pid]
        q = inn[(inn.pos <= TOP_ORDER) & inn.year.between(a, b) & (inn.player_id != pid)
                & (inn.attack_tier == tier)]
        tiers.append({"player": PLAYERS[pid], "attack_tier": tier, "innings": len(d),
                      "avg": d.runs.sum() / d.out.sum(),
                      "sr": 100 * d.runs.sum() / d.balls.sum(),
                      "peer_avg_same_years": q.runs.sum() / q.out.sum(),
                      "peer_sr_same_years": 100 * q.runs.sum() / q.balls.sum()})
tiers = pd.DataFrame(tiers).round(2)
save_table(tiers, "05_by_attack_tier")
print(tiers.to_string(index=False))

# ---- bowling-adjusted indexes
rows = []
for label, data in [("All matches (headline)", inn),
                    ("Full Member matches only", inn[inn.full_member_match])]:
    for pid in (SACHIN, KOHLI):
        a = plus_arrays(data, pid, "runs_adj_avg", "runs_adj_sr")
        ap, sp = plus_index(a)
        mi_a, mi_s = match_index(match_table(data, pid, "runs_adj_avg", "runs_adj_sr"))
        rows.append({"variant": label, "player": PLAYERS[pid],
                     "adj_career_avg": a["ra"].sum() / a["out"].sum(),
                     "adj_career_sr": 100 * a["rs"].sum() / a["balls"].sum(),
                     "bowling_adj_average_plus": ap, "bowling_adj_sr_plus": sp,
                     "bowling_adj_match_avg_index": mi_a, "bowling_adj_match_sr_index": mi_s})
adj = pd.DataFrame(rows).round(2)
save_table(adj, "05_bowling_adjusted_indexes")
print(adj.to_string(index=False))

# ---- chart: average and SR by strength of attack
order = ["Strong attack", "Middle", "Weak attack"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
fig.subplots_adjust(top=0.8, bottom=0.23, left=0.06, right=0.98, wspace=0.18)
x = np.arange(3)
for ax, col, pcol, label in [(axes[0], "avg", "peer_avg_same_years", "Batting average"),
                             (axes[1], "sr", "peer_sr_same_years", "Strike rate")]:
    for k, pid in enumerate((SACHIN, KOHLI)):
        t = tiers[tiers.player == PLAYERS[pid]].set_index("attack_tier").loc[order]
        xs = x + (k - 0.5) * 0.3
        ax.bar(xs, t[col], width=0.26, color=COLORS[pid], label=SHORT[pid], zorder=2)
        ax.scatter(xs, t[pcol], marker="_", s=420, color=INK, lw=2, zorder=3,
                   label="Top-order peers, same years & tier" if k == 0 else None)
        for xi, v in zip(xs, t[col]):
            ax.annotate(f"{v:.0f}", (xi, v), xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=8.5, color=INK)
    ax.set_xticks(x, ["Strongest third\nof attacks", "Middle third", "Weakest third\nof attacks"])
    ax.set_title(label)
axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.13), ncol=3)
finish(fig, "Against the strongest attacks, Kohli kept his edge in average; Sachin in tempo",
       "Attack strength = bowlers' previous-3-year records vs the league norm. "
       "Black tick = top-order peers facing the same tier, same years.",
       "05_attack_strength",
       note="Thirds are defined across all top-order innings, 1989–2023.")
