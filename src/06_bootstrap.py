"""06 - Uncertainty: bootstrap 95% confidence ranges for the main indexes.

A career is a sample of innings. Re-drawing each player's matches at random (with
replacement) 2,000 times and recomputing every index shows how much each number could move
by luck alone. For the match index the same-match peers travel with each re-drawn match.

Reports, for each index: estimate and 95% range for each player, the Kohli-minus-Sachin gap
with its own 95% range, and the share of re-draws in which Kohli comes out ahead.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (COLORS, INK, INK2, KOHLI, N_BOOT, PLAYERS, PROCESSED, SACHIN, SEED, SHORT,
                    SURFACE, finish, match_table, plus_arrays, save_table, set_style)

print(f"06 Bootstrap ({N_BOOT:,} re-draws per player)")
set_style()
inn = pd.read_pickle(PROCESSED / "innings_adj.pkl")
rng = np.random.default_rng(SEED)


def boot_match(pid, avg_col, sr_col):
    mt = match_table(inn, pid, avg_col, sr_col)
    idx = rng.integers(0, len(mt), (N_BOOT, len(mt)))
    s = {c: mt[c].to_numpy()[idx].sum(1) for c in mt.columns}
    t = mt.sum()
    est = ((t.p_ra / t.p_out) / (t.q_ra / t.q_out) * 100,
           (t.p_rs / t.p_balls) / (t.q_rs / t.q_balls) * 100)
    draws = ((s["p_ra"] / s["p_out"]) / (s["q_ra"] / s["q_out"]) * 100,
             (s["p_rs"] / s["p_balls"]) / (s["q_rs"] / s["q_balls"]) * 100)
    return est, draws


def boot_plus(pid, avg_col, sr_col):
    a = plus_arrays(inn, pid, avg_col, sr_col)
    n = len(a["ra"])
    idx = rng.integers(0, n, (N_BOOT, n))
    est = ((a["ra"].sum() / a["out"].sum()) / a["pa"].mean() * 100,
           (a["rs"].sum() / a["balls"].sum() * 100) / a["ps"].mean() * 100)
    draws = ((a["ra"][idx].sum(1) / a["out"][idx].sum(1)) / a["pa"][idx].mean(1) * 100,
             (a["rs"][idx].sum(1) / a["balls"][idx].sum(1) * 100) / a["ps"][idx].mean(1) * 100)
    return est, draws


families = [
    ("Match index", boot_match, "runs", "runs"),
    ("Match index, bowling-adjusted", boot_match, "runs_adj_avg", "runs_adj_sr"),
    ("Average+ / SR+", boot_plus, "runs", "runs"),
    ("Average+ / SR+, bowling-adjusted", boot_plus, "runs_adj_avg", "runs_adj_sr"),
]
rows = []
for fam, fn, ac, sc in families:
    res = {pid: fn(pid, ac, sc) for pid in (SACHIN, KOHLI)}
    for k, kind in enumerate(("Average", "Strike rate")):
        s_est, k_est = res[SACHIN][0][k], res[KOHLI][0][k]
        s_d, k_d = res[SACHIN][1][k], res[KOHLI][1][k]
        diff = k_d - s_d
        rows.append({
            "index": fam, "measure": kind,
            "sachin": s_est, "sachin_lo": np.percentile(s_d, 2.5), "sachin_hi": np.percentile(s_d, 97.5),
            "kohli": k_est, "kohli_lo": np.percentile(k_d, 2.5), "kohli_hi": np.percentile(k_d, 97.5),
            "gap_kohli_minus_sachin": k_est - s_est,
            "gap_lo": np.percentile(diff, 2.5), "gap_hi": np.percentile(diff, 97.5),
            "prob_kohli_ahead": (diff > 0).mean(),
        })
boot = pd.DataFrame(rows).round(3)
save_table(boot, "06_bootstrap_ci")
show = boot.copy()
for p in ("sachin", "kohli"):
    show[p] = [f"{e:.1f} ({lo:.1f}–{hi:.1f})" for e, lo, hi in
               zip(boot[p], boot[f"{p}_lo"], boot[f"{p}_hi"])]
show["gap"] = [f"{e:+.1f} ({lo:+.1f} to {hi:+.1f})" for e, lo, hi in
               zip(boot.gap_kohli_minus_sachin, boot.gap_lo, boot.gap_hi)]
print(show[["index", "measure", "sachin", "kohli", "gap", "prob_kohli_ahead"]].to_string(index=False))

# ---- chart: forest plot, one panel per measure
fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
fig.subplots_adjust(top=0.8, bottom=0.17, left=0.25, right=0.98, wspace=0.08)
labels = [f[0] for f in families]
for ax, kind in zip(axes, ("Average", "Strike rate")):
    d = boot[boot.measure == kind].reset_index(drop=True)
    ax.axvline(100, color=INK, lw=1)
    for k, pid in enumerate((SACHIN, KOHLI)):
        key = "sachin" if pid == SACHIN else "kohli"
        y = np.arange(len(d))[::-1] + (0.15 if pid == SACHIN else -0.15)
        ax.hlines(y, d[f"{key}_lo"], d[f"{key}_hi"], color=COLORS[pid], lw=2.5)
        ax.scatter(d[key], y, s=70, color=COLORS[pid], edgecolor=SURFACE, lw=2, zorder=3,
                   label=SHORT[pid])
        for yi, v in zip(y, d[key]):
            ax.annotate(f"{v:.0f}", (v, yi), xytext=(0, 6), textcoords="offset points",
                        ha="center", fontsize=8, color=INK)
    ax.set_title(f"{kind} indexes (100 = peers)")
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.set_xlim(95, 180)   # same scale in both panels so gaps compare honestly
    ax.set_yticks(np.arange(len(d))[::-1], labels, color=INK)
    ax.set_ylim(-0.6, len(d) - 0.4)
axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.08), ncol=2)
finish(fig, "Sachin's strike-rate edge is clear; Kohli's larger average edge is likely, "
       "but less certain",
       "Dot = estimate; line = 95% bootstrap range (2,000 re-draws of each career's matches). "
       "Averages are noisier than strike rates.",
       "06_headline_indexes")
