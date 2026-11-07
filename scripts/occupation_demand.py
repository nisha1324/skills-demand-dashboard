"""Part 2 report: which occupations employers are advertising for, and where demand is moving.

Reads the tidy snapshot in data/ and writes (to results/ by default):
- OCCUPATION_DEMAND.md                the report (every figure comes from this script)
- occupation_national.csv             every published occupation: 12-month averages and growth
- occupation_state.csv                every state x occupation cell, same measures
- major_group_state.csv               8 states x 8 major groups
- charts/05-08 *.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

from ivi import demand as D  # noqa: E402
from ivi.load import load_occupation_state, load_skill_level  # noqa: E402
from ivi.profile import STATES  # noqa: E402
from scripts.profile_source import (BLUE, GRID, INK, INK_2, MUTED, SAVE, md_table,  # noqa: E402
                                    month_name, n, pct, style)

ROOT = Path(__file__).resolve().parents[1]
RED = "#e34948"        # diverging pole for "falling" (reference palette, red)
NEUTRAL = "#f0efec"    # diverging midpoint (reference palette)
DIVERGING = LinearSegmentedColormap.from_list("fall_rise", [RED, NEUTRAL, BLUE])
MIN_MATRIX = 500.0     # ads a month for the demand matrix: big enough to matter to a recruiter


def signed(x: float, nd: int = 1) -> str:
    return "–" if pd.isna(x) else pct(x, nd, sign=True)


def signed_n(x: float) -> str:
    return f"{x:+,.0f}".replace("-", "−")


def ads(x: float) -> str:
    return n(x) if x >= 100 else n(x, 1)


def chart_major_groups(mg: pd.DataFrame, end: str, path: Path) -> None:
    d = mg.sort_values("vs_2019")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
    for ax, col, title in [(axes[0], "yoy", "vs the 12 months before"),
                           (axes[1], "vs_2019", "vs 2019 (pre-COVID)")]:
        v = d[col] * 100
        ax.barh(d["name"], v, color=[BLUE if x > 0 else RED for x in v], height=0.6)
        ax.axvline(0, color=INK_2, linewidth=0.8)
        span = max(abs(v.min()), abs(v.max()))
        for i, x in enumerate(v):
            ax.text(x + (span * 0.03 if x >= 0 else -span * 0.03), i, f"{x:+.1f}%".replace("-", "−"),
                    va="center", ha="left" if x >= 0 else "right", fontsize=9, color=INK)
        lo = min(v.min(), 0) - span * 0.5
        hi = max(v.max(), 0) + span * 0.3
        ax.set_xlim(lo, hi)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
        ax.set_xticks([])
        ax.set_title(title, loc="left", fontsize=10, color=INK_2)
    fig.suptitle(f"Job ads by occupation group, 12 months to {month_name(end)}", x=0.01, ha="left",
                 fontsize=12, fontweight="bold", color=INK)
    fig.text(0.01, 0.905, "Change in the 12-month average of ads a month. Blue: up. Red: down. "
             "Source: JSA Internet Vacancy Index", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_contributions(con: pd.DataFrame, names: pd.Series, net: float, end: str, path: Path,
                        k: int = 8) -> None:
    d = pd.concat([con.head(k), con.tail(k)])
    fig, ax = plt.subplots(figsize=(9, 5.6))
    y = np.arange(len(d))
    ax.barh(y, d["change"], color=[BLUE if x > 0 else RED for x in d["change"]], height=0.62)
    ax.axvline(0, color=INK_2, linewidth=0.8)
    span = d["change"].abs().max()
    for i, (code, r) in enumerate(d.iterrows()):
        x = r["change"]
        label = f"{x:+,.0f}".replace("-", "−")
        ax.text(x + (span * 0.02 if x > 0 else -span * 0.02), i, label, va="center",
                ha="left" if x > 0 else "right", fontsize=8.5, color=INK)
        ax.text(span * 0.04 if x < 0 else -span * 0.04, i, names[code], va="center",
                ha="left" if x < 0 else "right", fontsize=8.5, color=INK_2)
    ax.set_yticks([])
    ax.set_xlim(-span * 1.9, span * 1.9)
    ax.set_xlabel("Change in ads a month (12-month average)")
    style(ax, "Where the change in job ads came from",
          f"Occupations adding and losing the most ads, 12 months to {month_name(end)} vs the year before. "
          f"Net: {net:+,.0f}".replace("-", "−"))
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_matrix(q: pd.DataFrame, names: pd.Series, labels: list[str], end: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 6.2))
    ratio = q["now"] / q["y2019"]
    size = 20 + q["now"] / q["now"].max() * 380
    ax.scatter(ratio, q["yoy"] * 100, s=size, color=BLUE, alpha=0.55, edgecolor="white", linewidth=1)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.axvline(1, color=INK_2, linewidth=0.8)
    ax.set_xscale("log")
    ticks = [0.5, 0.75, 1, 1.5, 2, 3, 5]
    ax.set_xticks(ticks, [f"{t:g}×" for t in ticks])
    ax.minorticks_off()
    ax.set_xlim(0.45, 6)
    ylo, yhi = q["yoy"].min() * 100 - 4, q["yoy"].max() * 100 + 6
    ax.set_ylim(ylo, yhi)
    for code in labels:
        r = q.loc[code]
        x, yv = r["now"] / r["y2019"], r["yoy"] * 100
        right = x > 3
        ax.annotate(names[code], (x, yv), xytext=(-12, -12) if right else (6, 6), textcoords="offset points",
                    fontsize=8, color=INK, ha="right" if right else "left", va="top" if right else "baseline")
    corners = [(0.47, yhi - 1.5, "Rising, still below 2019", "left"),
               (5.8, yhi - 1.5, "Growing, above 2019", "right"),
               (0.47, ylo + 1.5, "Shrinking, below 2019", "left"),
               (5.8, ylo + 1.5, "Cooling, still above 2019", "right")]
    for x, yv, text, ha in corners:
        ax.text(x, yv, text, fontsize=9, color=MUTED, ha=ha, va="top" if yv > 0 else "bottom",
                fontweight="bold")
    ax.set_xlabel("Ads a month now, as a multiple of the 2019 average (log scale)")
    ax.set_ylabel("Change on the year before (%)")
    style(ax, f"Demand matrix: occupations with {MIN_MATRIX:,.0f}+ ads a month",
          f"12-month average to {month_name(end)}. Bubble size: ads a month")
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_heatmap(h: pd.DataFrame, end: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    v = h.values * 100
    lim = np.nanmax(np.abs(v))
    ax.imshow(v, cmap=DIVERGING, norm=TwoSlopeNorm(0, -lim, lim), aspect="auto")
    for i in range(v.shape[0]):
        for j in range(v.shape[1]):
            r = 0 if np.isnan(v[i, j]) else int(round(v[i, j]))
            ax.text(j, i, "–" if np.isnan(v[i, j]) else ("0%" if r == 0 else f"{r:+d}%".replace("-", "−")),
                    ha="center", va="center", fontsize=8.5, color=INK)
    ax.set_xticks(range(len(h.columns)), h.columns, fontsize=9)
    ax.set_yticks(range(len(h.index)), h.index, fontsize=9)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-0.5, len(h.columns)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(h.index)), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", length=0)
    ax.set_title(f"Change in job ads by state and occupation group, 12 months to {month_name(end)}",
                 loc="left", fontsize=12, fontweight="bold", pad=22, color=INK)
    ax.text(0, 1.02, "vs the 12 months before. Blue: up. Red: down. Source: JSA Internet Vacancy Index",
            transform=ax.transAxes, fontsize=9, color=INK_2)
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


SHORT_GROUP = {"1": "Managers", "2": "Professionals", "3": "Technicians,\ntrades",
               "4": "Community,\npersonal service", "5": "Clerical,\nadmin", "6": "Sales",
               "7": "Machinery,\ndrivers", "8": "Labourers"}


def occ_table(d: pd.DataFrame, names: pd.Series) -> str:
    t = pd.DataFrame({
        "Occupation": [names[c] for c in d.index],
        "Ads a month (12-mo avg)": [ads(v) for v in d["now"]],
        "Year before": [ads(v) for v in d["prev"]],
        "vs year before": [signed(v) for v in d["yoy"]],
        f"Latest 3 months vs a year earlier": [signed(v) for v in d["latest_yoy"]],
        "vs 2019": [signed(v) for v in d["vs_2019"]],
    })
    return md_table(t)


def main(out: Path | None = None) -> None:
    out = out or ROOT / "results"
    charts = out / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    occ = load_occupation_state()
    skill = load_skill_level()
    names = D.titles(occ)

    tot = D.totals_wide(occ)
    end = tot.columns.max()
    ct = D.compare(tot, end)
    aus = ct.loc["AUST"]

    nat = D.compare(D.national_wide(occ), end)
    pub_change = nat["change"].sum()
    mg = D.compare(D.major_group_wide(occ), end)
    mg["name"] = [D.MAJOR_GROUPS[k] for k in mg.index]
    mg["share"] = mg["now"] / aus["now"]

    con = D.contributions(nat, aus["change"])
    q = D.quadrant(nat, MIN_MATRIX)
    q_counts = q.groupby("quadrant").agg(occupations=("now", "size"), ads=("now", "sum"))
    q_counts = q_counts.reindex(list(D.QUADRANTS.values())).fillna(0)

    risers = D.ranked(nat, "yoy", 10)
    fallers = D.ranked(nat, "yoy", 10, ascending=True)
    big = nat.sort_values("now", ascending=False).head(15)
    n_rated = int(nat["yoy"].notna().sum())
    n_turning = int(D.turning(nat[nat["now"] >= MIN_MATRIX]).sum())
    turn_list = nat[(nat["now"] >= MIN_MATRIX) & D.turning(nat)].sort_values("now", ascending=False)

    so = D.compare(D.state_occupation_wide(occ), end)
    leaders = D.state_leaders(so, 3)
    smg = D.compare(D.major_group_wide(occ, state=None), end)
    heat = smg["yoy"].unstack("major").reindex(STATES)
    heat.columns = [SHORT_GROUP[c] for c in heat.columns]
    sk = D.skill_level_compare(skill, end)

    # CSVs: every row, so the dashboard (Part 4) and readers can check any figure
    cols = ["now", "prev", "y2019", "latest", "year_ago", "yoy", "vs_2019", "latest_yoy", "change"]
    nat_csv = nat[cols].round(4).assign(anzsco_title=names.reindex(nat.index).values)
    nat_csv.reset_index().to_csv(out / "occupation_national.csv", index=False, lineterminator="\n")
    so_csv = so[cols].round(4).reset_index()
    so_csv.insert(2, "anzsco_title", names.reindex(so_csv["anzsco_code"]).values)
    so_csv.to_csv(out / "occupation_state.csv", index=False, lineterminator="\n")
    smg[cols].round(4).reset_index().to_csv(out / "major_group_state.csv", index=False,
                                            lineterminator="\n")

    # charts
    chart_major_groups(mg, end, charts / "05_major_groups.png")
    chart_contributions(con, names, aus["change"], end, charts / "06_contributions.png")
    labels = list(q.sort_values("now", ascending=False).head(6).index)
    for extreme in [q["yoy"].idxmax(), q["yoy"].idxmin(), (q["now"] / q["y2019"]).idxmax(),
                    (q["now"] / q["y2019"]).idxmin()]:
        if extreme not in labels:
            labels.append(extreme)
    chart_matrix(q, names, labels, end, charts / "07_demand_matrix.png")
    chart_heatmap(heat, end, charts / "08_state_heatmap.png")

    # numbers used in the text
    ago = D.shift_month(end, -12)
    top_up, top_down = con.iloc[-1], con.iloc[0]
    up_code, down_code = con.index[-1], con.index[0]
    adders = con[con["change"] > 0]
    losers = con[con["change"] < 0]
    ict = [c for c in ["2613", "2611", "2632", "2612"] if c in nat.index]
    states_t = ct.reindex(["AUST"] + STATES)
    gm = mg.sort_values("vs_2019")
    mg_best_yoy, mg_worst_yoy = mg["yoy"].idxmax(), mg["yoy"].idxmin()
    sk_t = sk.loc[[1, 2, 3, 4, 5]]
    below_2019 = [s for s in STATES if states_t.loc[s, "vs_2019"] < 0]
    groups_up = mg[mg["yoy"] > 0]
    sk_all_above_2019 = bool((sk_t["vs_2019"] > 0).all())
    sk_all_up_latest = bool((sk_t["latest_yoy"] > 0).all())
    without_top = aus["change"] - top_up["change"]
    gap_other = aus["change"] - pub_change
    # occupations a training provider in health, care and trades would follow (ANZSCO codes)
    feeders = [c for c in ["2544", "4233", "4231", "3411", "4211"] if c in nat.index]
    q_of = q["quadrant"].to_dict()

    mg_t = pd.DataFrame({
        "Major group": gm["name"].iloc[::-1].values,
        "Ads a month (12-mo avg)": [n(v) for v in gm["now"].iloc[::-1]],
        "Share of all ads": [pct(v, 1) for v in gm["share"].iloc[::-1]],
        "vs year before": [signed(v) for v in gm["yoy"].iloc[::-1]],
        "Latest 3 months vs a year earlier": [signed(v) for v in gm["latest_yoy"].iloc[::-1]],
        "vs 2019": [signed(v) for v in gm["vs_2019"].iloc[::-1]],
    })
    states_tab = pd.DataFrame({
        "State": ["Australia" if s == "AUST" else s for s in states_t.index],
        "Ads a month (12-mo avg)": [n(v) for v in states_t["now"]],
        "vs year before": [signed(v) for v in states_t["yoy"]],
        "Latest 3 months vs a year earlier": [signed(v) for v in states_t["latest_yoy"]],
        "vs 2019": [signed(v) for v in states_t["vs_2019"]],
    })
    con_t = pd.concat([con.tail(10).iloc[::-1], con.head(10)])
    con_tab = pd.DataFrame({
        "Occupation": [names[c] for c in con_t.index],
        "Year before": [ads(v) for v in con_t["prev"]],
        "12 months to " + month_name(end): [ads(v) for v in con_t["now"]],
        "Change (ads a month)": [f"{v:+,.0f}".replace("-", "−") for v in con_t["change"]],
    })
    q_tab = pd.DataFrame({
        "Demand state": q_counts.index,
        "Occupations": [int(v) for v in q_counts["occupations"]],
        "Ads a month": [n(v) for v in q_counts["ads"]],
        "Largest": [", ".join(names[c] for c in q[q["quadrant"] == k].sort_values("now", ascending=False)
                              .head(4).index) for k in q_counts.index],
    })
    lead_rows = []
    for s in STATES:
        L = leaders[leaders["state"] == s]
        big3 = L[L["list"] == "largest"]
        up3 = L[L["list"] == "fastest rising"]
        lead_rows.append({
            "State": s,
            "Largest (ads a month)": "; ".join(f"{names[c]} ({ads(v)})" for c, v in zip(big3["anzsco_code"], big3["now"])),
            "Fastest rising (base above 20)": "; ".join(
                f"{names[c]} ({ads(p)} to {ads(v)}, {signed(y, 0)})"
                for c, p, v, y in zip(up3["anzsco_code"], up3["prev"], up3["now"], up3["yoy"])),
        })
    sk_tab = pd.DataFrame({
        "Skill level": [D.SKILL_LEVELS[i] for i in sk_t.index],
        f"{month_name(end)} (SA)": [n(v) for v in sk_t["latest"]],
        "12-mo avg vs year before": [signed(v) for v in sk_t["yoy"]],
        f"{month_name(end)} vs {month_name(ago)}": [signed(v) for v in sk_t["latest_yoy"]],
        "12-mo avg vs 2019": [signed(v) for v in sk_t["vs_2019"]],
    })
    sk_tot = sk.loc[0]

    best_q = q[q["quadrant"] == "Growing, above 2019"].sort_values("now", ascending=False)
    cool_q = q[q["quadrant"] == "Cooling, still above 2019"].sort_values("change")
    shrink_q = q[q["quadrant"] == "Shrinking, below 2019"].sort_values("now", ascending=False)
    hi_state = states_t.drop("AUST")["vs_2019"].idxmax()
    lo_state = states_t.drop("AUST")["yoy"].idxmin()
    multi = nat[(nat["vs_2019"] >= 2) & (nat["now"] >= 100)].sort_values("now", ascending=False)

    lines = [
        "# Part 2: occupation demand",
        "",
        "_Generated by `scripts/occupation_demand.py` from the snapshot in `data/`. Do not edit by hand._",
        "",
        "How every number here is measured (the rules come from Part 1, `SOURCE_PROFILE.md`):",
        "",
        f"- **12-month average:** the mean of the 12 monthly 3-month averages ending {month_name(end)}. "
        "A full year, so the seasonal swing cancels. \"vs year before\" compares it with the 12 months "
        f"ending {month_name(ago)}; \"vs 2019\" with the calendar-2019 average (pre-COVID).",
        f"- **Latest 3 months vs a year earlier:** the 3-month average to {month_name(end)} against the "
        f"one to {month_name(ago)}. The same 3 calendar months, so no seasonal bias; it shows whether "
        "the 12-month trend is still going or turning.",
        f"- **Floor:** a growth rate is only shown when its base averages more than {D.FLOOR:.0f} ads a "
        "month (\"–\" otherwise).",
        "- **Shares** use the published total, which includes the 7 suppressed occupations. Major groups "
        "are built from the published 4-digit occupations, so Managers, Professionals and Community and "
        "personal service workers are slightly understated (the suppressed ones belong to those groups).",
        "",
        "## The whole market",
        "",
        f"Australia averaged {n(aus['now'])} ads a month in the 12 months to {month_name(end)}, "
        f"{signed(aus['yoy'])} on the year before and {signed(aus['vs_2019'])} on 2019. "
        + (f"But the latest 3 months are {signed(aus['latest_yoy'])} on the same 3 months a year earlier, "
           f"and JSA's seasonally adjusted {month_name(end)} figure is {signed(sk_tot['latest_yoy'])} on "
           f"{month_name(ago)}. **The 12-month average is still falling, but the year-on-year fall has "
           "stopped**, for now."
           if aus["yoy"] < 0 and aus["latest_yoy"] > 0 and sk_tot["latest_yoy"] > 0 else
           f"The latest 3 months are {signed(aus['latest_yoy'])} on the same 3 months a year earlier."),
        "",
        md_table(states_tab),
        "",
        f"States split sharply. {hi_state} is furthest above 2019 ({signed(states_t.loc[hi_state, 'vs_2019'])}); "
        + (" and ".join(f"{s} ({signed(states_t.loc[s, 'vs_2019'])})" for s in below_2019)
           + (" are" if len(below_2019) > 1 else " is") + " below it" if below_2019 else "every state is above it")
        + f", and {lo_state} fell most on the year ({signed(states_t.loc[lo_state, 'yoy'])}). State totals come "
        "straight from JSA (they add up; Part 1, trap 2).",
        "",
        "## By major occupation group",
        "",
        md_table(mg_t),
        "",
        (f"{mg.loc[mg_best_yoy, 'name']} is the only group up on the year "
         if len(groups_up) == 1 else f"{mg.loc[mg_best_yoy, 'name']} grew most on the year ")
        + f"({signed(mg.loc[mg_best_yoy, 'yoy'])})"
        + (f" and the furthest above 2019 ({signed(mg.loc[mg_best_yoy, 'vs_2019'])})"
           if mg["vs_2019"].idxmax() == mg_best_yoy else "")
        + f". {mg.loc[mg_worst_yoy, 'name']} fell most ({signed(mg.loc[mg_worst_yoy, 'yoy'])}). "
        f"{gm['name'].iloc[0]} are the least above 2019 ({signed(gm['vs_2019'].iloc[0])}).",
        "",
        "![Major groups](charts/05_major_groups.png)",
        "",
        "## Where the change came from",
        "",
        f"All ads fell by {n(-aus['change'])} a month on the year (12-month averages). The published "
        f"occupations fell by {n(-pub_change)}, so the suppressed occupations and rounding "
        f"{'added' if gap_other > 0 else 'lost'} {n(abs(gap_other))}. {len(adders)} occupations added ads and {len(losers)} lost them. "
        f"The biggest single move was {names[up_code]}: {signed_n(top_up['change'])} ads a month "
        f"({signed(top_up['change'] / top_up['prev'])}). Without it the fall would have been "
        f"{n(-without_top)} a month, not {n(-aus['change'])}. The biggest fall was {names[down_code]} "
        f"({signed_n(top_down['change'])}).",
        "",
        md_table(con_tab),
        "",
        "![Contributions](charts/06_contributions.png)",
        "",
        "## The 15 largest occupations",
        "",
        occ_table(big, names),
        "",
        f"## Fastest rising and falling (of {n_rated} occupations with more than {D.FLOOR:.0f} ads a month "
        "a year earlier)",
        "",
        "### Rising",
        "",
        occ_table(risers, names),
        "",
        "### Falling",
        "",
        occ_table(fallers, names),
        "",
        f"## Demand matrix ({len(q)} occupations with {MIN_MATRIX:,.0f}+ ads a month)",
        "",
        "Each occupation is placed by two questions: is it up on the year, and is it above 2019? "
        "The four answers call for different actions.",
        "",
        md_table(q_tab),
        "",
        "![Demand matrix](charts/07_demand_matrix.png)",
        "",
        f"In {n_turning} of these {len(q)} occupations the latest 3 months move against the 12-month trend "
        "(down on the year but up on the same months a year earlier, or the reverse). The largest: "
        + "; ".join(f"{names[c]} ({signed(r['yoy'])} on the year, {signed(r['latest_yoy'])} in the latest 3 months)"
                    for c, r in turn_list.head(5).iterrows()) + ".",
        "",
        f"**Read multi-fold rises with care.** {len(multi)} occupations with 100+ ads a month are at "
        "least 3 times their 2019 level (largest first): "
        + ", ".join(f"{names[c]} ({r['now'] / r['y2019']:.1f}×)" for c, r in multi.head(5).iterrows())
        + ". Some will be real shortages, but a step that big can also come from a change in how ads are "
        "coded to occupations, which this data can't rule out. Check the monthly series before acting on one.",
        "",
        "## By state",
        "",
        "Change in each state's major groups on the year before (12-month averages):",
        "",
        "![State heatmap](charts/08_state_heatmap.png)",
        "",
        "Largest and fastest-rising occupations in each state (12-month averages; risers need more than "
        f"{D.FLOOR:.0f} ads a month a year earlier, so small-cell noise can't top the list):",
        "",
        md_table(pd.DataFrame(lead_rows)),
        "",
        "## By skill level",
        "",
        "JSA publishes skill levels only as seasonally adjusted and trend series, and those don't add up "
        "(Part 1, trap 2), so each level is compared only with itself. No shares.",
        "",
        md_table(sk_tab),
        "",
        ("Every level is above 2019" if sk_all_above_2019 else "Not every level is above 2019")
        + f"; {D.SKILL_LEVELS[int(sk_t['vs_2019'].idxmax())].split(' (')[0].lower()} is furthest above "
        f"({signed(sk_t['vs_2019'].max())}) and {D.SKILL_LEVELS[int(sk_t['vs_2019'].idxmin())].split(' (')[0].lower()} "
        f"least ({signed(sk_t['vs_2019'].min())}). "
        + (f"In {month_name(end)} all five are above {month_name(ago)}." if sk_all_up_latest else ""),
        "",
        "## So what for the business?",
        "",
        "- **Recruiters:** the strongest markets are the big occupations still growing and above 2019: "
        + ", ".join(f"{names[c]} ({ads(r['now'])} a month, {signed(r['yoy'])})" for c, r in best_q.head(5).iterrows())
        + ". The big occupations losing the most ads, where placement volumes are most at risk: "
        + ", ".join(f"{names[c]} ({signed_n(r['change'])} a month, {signed(r['yoy'])})"
                    for c, r in q.sort_values("change").head(3).iterrows()) + ".",
        "- **Training providers:** health, care and electrical courses feed occupations that are "
        + ("all above 2019, though not all still growing: " if (nat.loc[feeders, "vs_2019"] > 0).all()
           else "mixed against 2019: ")
        + "; ".join(f"{names[c]} ({q_of.get(c, 'under ' + n(MIN_MATRIX) + ' ads a month').lower()}, "
                    f"{signed(nat.loc[c, 'yoy'])} on the year)" for c in feeders)
        + ". ICT courses face a market "
        + ("well below 2019: " if (nat.loc[ict, "vs_2019"] < -0.25).all() else "that has moved since 2019: ")
        + ", ".join(f"{names[c]} {signed(nat.loc[c, 'vs_2019'])}" for c in ict) + ".",
        f"- **Workforce planners:** {len(shrink_q)} big occupations are below 2019 and still falling, "
        "the largest being " + ", ".join(names[c] for c in shrink_q.head(3).index) + ". A plan that "
        "assumes these will bounce back to 2019 levels isn't supported by the data so far.",
        "- **Everyone:** the national 12-month average still says \"cooling\", but the latest 3 months are "
        "up on a year earlier. Check the same-month comparison in each new release before planning cuts.",
        "",
    ]
    (out / "OCCUPATION_DEMAND.md").write_text("\n".join(lines))
    print(f"wrote {out / 'OCCUPATION_DEMAND.md'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
