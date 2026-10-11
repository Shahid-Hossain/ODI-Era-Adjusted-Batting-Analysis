"""09 - Headline table, robustness check, and the verdict (written to outputs/summary.md).

The verdict rests on the two headline methods agreed up front:
  * the match-adjusted index (script 03), and
  * bowling-adjusted Average+ / SR+ (script 05),
each with its bootstrap 95% range (script 06). Every other variant is a robustness check.
"""
import pandas as pd

from common import CUTOFF, ROOT, TABLES, save_table, to_markdown

print("09 Summary")
boot = pd.read_csv(TABLES / "06_bootstrap_ci.csv")
mi = pd.read_csv(TABLES / "03_match_index.csv")
yp = pd.read_csv(TABLES / "04_yearly_plus_career.csv")
adj = pd.read_csv(TABLES / "05_bowling_adjusted_indexes.csv")
val = pd.read_csv(TABLES / "01_validation.csv").set_index("player")
span = {}
for name, r in val.iterrows():
    first, last, dob = (pd.to_datetime(r[c], format="%d %b %Y") for c in ("first", "last", "dob"))
    span[name] = {"first": first, "last": last, "debut_age": int((first - dob).days // 365.25),
                  "years": last.year - first.year}   # calendar span, e.g. 1989-2012 = 23

HEADLINE = ["Match index", "Average+ / SR+, bowling-adjusted"]
head = boot[boot["index"].isin(HEADLINE)].copy()


def fmt(e, lo, hi):
    return f"{e:.1f} ({lo:.1f}–{hi:.1f})"


head["Sachin (95% range)"] = [fmt(*r) for r in head[["sachin", "sachin_lo", "sachin_hi"]].values]
head["Kohli (95% range)"] = [fmt(*r) for r in head[["kohli", "kohli_lo", "kohli_hi"]].values]
head["Kohli minus Sachin"] = [f"{e:+.1f} ({lo:+.1f} to {hi:+.1f})" for e, lo, hi in
                              head[["gap_kohli_minus_sachin", "gap_lo", "gap_hi"]].values]
head["Chance Kohli is ahead"] = [f"{p:.0%}" for p in head.prob_kohli_ahead]
headline = head[["index", "measure", "Sachin (95% range)", "Kohli (95% range)",
                 "Kohli minus Sachin", "Chance Kohli is ahead"]]
save_table(headline, "09_headline")

# ---- robustness: every variant, point estimates
S, K = "Sachin Tendulkar", "Virat Kohli"
rob = []
for v in mi.variant.unique():
    d = mi[mi.variant == v].set_index("player")
    rob.append(("Match index: " + v, d.avg_index[S], d.avg_index[K], d.sr_index[S], d.sr_index[K]))
for v in yp.variant.unique():
    d = yp[yp.variant == v].set_index("player")
    rob.append(("Average+/SR+: " + v, d.average_plus[S], d.average_plus[K], d.sr_plus[S], d.sr_plus[K]))
for v in adj.variant.unique():
    d = adj[adj.variant == v].set_index("player")
    rob.append(("Bowling-adj. Average+/SR+: " + v, d.bowling_adj_average_plus[S],
                d.bowling_adj_average_plus[K], d.bowling_adj_sr_plus[S], d.bowling_adj_sr_plus[K]))
    rob.append(("Bowling-adj. match index: " + v, d.bowling_adj_match_avg_index[S],
                d.bowling_adj_match_avg_index[K], d.bowling_adj_match_sr_index[S],
                d.bowling_adj_match_sr_index[K]))
rob = pd.DataFrame(rob, columns=["variant", "sachin_avg_index", "kohli_avg_index",
                                 "sachin_sr_index", "kohli_sr_index"]).round(1)
rob["average_leader"] = (rob.kohli_avg_index > rob.sachin_avg_index).map({True: "Kohli", False: "Sachin"})
rob["sr_leader"] = (rob.sachin_sr_index > rob.kohli_sr_index).map({True: "Sachin", False: "Kohli"})
save_table(rob, "09_robustness")
print(rob.to_string(index=False))
n = len(rob)
k_avg = (rob.average_leader == "Kohli").sum()
s_sr = (rob.sr_leader == "Sachin").sum()

# ---- verdict (numbers pulled from the tables, wording from simple rules)
avg_rows = head[head.measure == "Average"]
sr_rows = head[head.measure == "Strike rate"]
p_avg = avg_rows.prob_kohli_ahead.agg(["min", "max"])
p_sr = 1 - sr_rows.prob_kohli_ahead.agg(["max", "min"])


def rng(lo, hi, pct=False):
    a, b = sorted((lo, hi))
    f = (lambda v: f"{v:.0%}") if pct else (lambda v: f"{v:.0f}")
    return f(a) if f(a) == f(b) else f"{f(a)}–{f(b)}"


def confidence(p):
    return "very confident" if p >= 0.99 else "fairly confident" if p >= 0.9 else "unsure"


lines = [
    "# Summary of findings",
    "",
    f"Analysis period: all ODIs to {CUTOFF}. Kohli's career is covered to the 2023 World Cup final "
    "(19 Nov 2023); Sachin's career is complete (1989–2012).",
    "",
    "## Validation",
    f"- Sachin: {val.loc[S, 'innings']} innings, {val.loc[S, 'runs']:,.0f} runs, average "
    f"{val.loc[S, 'average']}, SR {val.loc[S, 'strike_rate']} — matches his official record.",
    f"- Kohli: {val.loc[K, 'innings']} innings, {val.loc[K, 'runs']:,.0f} runs, average "
    f"{val.loc[K, 'average']}, SR {val.loc[K, 'strike_rate']}.",
    "",
    "## Headline indexes (100 = top-order peers)",
    "",
    to_markdown(headline),
    "",
    "## Verdict",
    f"- **Accumulating runs (average): Kohli.** Kohli's average-based indexes are "
    f"{rng(avg_rows.kohli.min(), avg_rows.kohli.max())} vs Sachin's "
    f"{rng(avg_rows.sachin.min(), avg_rows.sachin.max())}. Kohli comes out ahead in "
    f"{rng(p_avg['min'], p_avg['max'], True)} of bootstrap re-draws, so we can be "
    f"{confidence(p_avg['min'])} the gap is real, though its size is uncertain.",
    f"- **Scoring fast (strike rate): Sachin.** Sachin's SR indexes are "
    f"{rng(sr_rows.sachin.min(), sr_rows.sachin.max())} vs Kohli's "
    f"{rng(sr_rows.kohli.min(), sr_rows.kohli.max())}. Sachin comes out ahead in "
    f"{rng(p_sr['min'], p_sr['max'], True)} of re-draws — {confidence(p_sr['min'])}.",
    f"- **Robustness:** Kohli leads on average in {k_avg} of {n} variants; Sachin leads on strike "
    f"rate in {s_sr} of {n} variants (team-mates only, opposition only, Full Member matches only, "
    "bowling-adjusted, yearly peers).",
    f"- **What these indexes leave out: longevity and volume.** Every index here measures quality "
    f"per dismissal or per ball, so it says nothing about how long a player kept it up. Sachin "
    f"debuted at {span[S]['debut_age']}, had a {span[S]['years']}-year career "
    f"({span[S]['first']:%Y}–{span[S]['last']:%Y}) and scored {val.loc[S, 'runs']:,.0f} runs in "
    f"{val.loc[S, 'innings']} innings, staying above his peers in most of those years. Kohli's "
    f"{val.loc[K, 'runs']:,.0f} runs came in {val.loc[K, 'innings']} innings over "
    f"{span[K]['years']} years ({span[K]['first']:%Y}–{span[K]['last']:%Y}; debut at "
    f"{span[K]['debut_age']}; career still running at the "
    "cutoff). Sustained volume is a big part of Sachin's case and sits outside these numbers.",
]
(ROOT / "outputs" / "summary.md").write_text("\n".join(lines) + "\n")
print("  summary -> outputs/summary.md")
print("\n".join(lines[-4:]))
