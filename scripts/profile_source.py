"""Part 1 report: what the IVI numbers mean, and the rules that follow.

Reads the tidy snapshot in data/ and writes:
- results/SOURCE_PROFILE.md          the report (every figure comes from this script)
- results/seasonal_ratio.csv          raw 3-month average vs seasonally adjusted, by calendar month
- results/regional_coverage.csv       share of national ads placed in a region, by month
- results/noise_by_base.csv           how often small cells swing by more than 50% a year
- results/charts/01-04 *.png
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from ivi import profile as P  # noqa: E402
from ivi.load import load_all  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
CHARTS = RESULTS / "charts"

# Reference palette (validated: 2 slots, light mode, all checks pass)
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK_2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1", "#fcfcfb"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.titlecolor": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "svg.hashsalt": "ivi", "path.simplify": False,
})
SAVE = {"dpi": 150, "metadata": {"Software": None}}


def month_name(m: str) -> str:
    p = pd.Period(m, "M")
    return f"{p.strftime('%B')} {p.year}"


def pct(x: float, nd: int = 1, sign: bool = False) -> str:
    s = f"{x * 100:+.{nd}f}%" if sign else f"{x * 100:.{nd}f}%"
    return s.replace("-", "−") if sign else s


def n(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}"


def style(ax, title: str, subtitle: str | None = None) -> None:
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", pad=22 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=INK_2)


def chart_national(sa: pd.Series, t3: pd.Series, avg2019: float, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x_sa = pd.PeriodIndex(sa.index, freq="M").to_timestamp()
    x_3 = pd.PeriodIndex(t3.index, freq="M").to_timestamp()
    ax.plot(x_3, t3.values / 1000, color=ORANGE, linewidth=1.4, label="Raw, 3-month average")
    ax.plot(x_sa, sa.values / 1000, color=BLUE, linewidth=2, label="Seasonally adjusted")
    ax.axhline(avg2019 / 1000, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(x_sa[0], avg2019 / 1000 + 4, "2019 average", color=INK_2, fontsize=9)
    ax.text(x_sa[-1].to_pydatetime() + dt.timedelta(days=60), sa.values[-1] / 1000, f"{sa.values[-1] / 1000:.1f}k\n{month_name(sa.index[-1])}",
            color=INK, fontsize=9, ha="left", va="center")
    ax.set_xlim(x_sa[0].to_pydatetime() - dt.timedelta(days=90), x_sa[-1].to_pydatetime() + dt.timedelta(days=720))
    ax.set_xticks([dt.datetime(y, 1, 1) for y in range(2006, 2027, 4)], [str(y) for y in range(2006, 2027, 4)])
    ax.set_ylabel("Job ads a month (thousands)")
    ax.set_ylim(0, None)
    ax.legend(loc="lower left", frameon=False, ncol=2, fontsize=9, labelcolor=INK_2)
    style(ax, "Online job ads in Australia, 2006 to 2026",
          "Seasonally adjusted and raw 3-month average. Source: JSA Internet Vacancy Index")
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_seasonal(sr: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    dev = (sr["ratio_mean"] - 1) * 100
    ax.bar(MONTHS, dev, color=BLUE, width=0.6)
    ax.axhline(0, color=INK_2, linewidth=0.8)
    for i in [int(dev.idxmin()), int(dev.idxmax())]:
        v = dev.iloc[i]
        ax.text(i, v + (0.6 if v > 0 else -0.6), f"{v:+.1f}%".replace("-", "−"), ha="center",
                va="bottom" if v > 0 else "top", fontsize=9, color=INK)
    ax.set_ylabel("Raw 3-month average vs\nseasonally adjusted (%)")
    lo, hi = dev.min(), dev.max()
    ax.set_ylim(lo - 3, hi + 3)
    style(ax, "The raw 3-month average swings with the calendar",
          "Average gap, by the month the 3 months end in, 2010 to 2019")
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_coverage(cov_ivi: pd.Series, cov_sa4: pd.Series, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for s, colour, label, lw in [(cov_ivi, BLUE, "37 IVI regions (from May 2010)", 2),
                                 (cov_sa4, ORANGE, "GCCSA and SA4 regions (from Jan 2019)", 1.6)]:
        x = pd.PeriodIndex(s.index, freq="M").to_timestamp()
        ax.plot(x, s.values * 100, color=colour, linewidth=lw, label=label)
    ax.set_ylabel("Share of national ads placed\nin a region (%)")
    ax.set_ylim(94, 101)
    ax.legend(loc="lower left", frameon=False, fontsize=9, labelcolor=INK_2)
    last = cov_ivi.index[-1]
    x_last = pd.Period(last, "M").to_timestamp()
    ax.text(x_last, cov_ivi.iloc[-1] * 100 - 0.7, f"{cov_ivi.iloc[-1] * 100:.1f}%", ha="right",
            fontsize=9, color=INK)
    style(ax, "Since 2023 about 3% of ads aren't placed in any region",
          "Sum of regions as a share of the national 3-month average. A region's growth vs the nation is biased down")
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_noise(nb: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    v = nb["share_big_swing"] * 100
    ax.bar(nb["bin"].astype(str), v, color=BLUE, width=0.6)
    for i, val in enumerate(v):
        ax.text(i, val + 1, f"{val:.0f}%" if val >= 1 else f"{val:.1f}%", ha="center", va="bottom",
                fontsize=9, color=INK)
    ax.set_xlabel("Ads a month in the base year (3-month average)")
    ax.set_ylabel("Cells that rose or fell\nby more than 50% (%)")
    ax.set_ylim(0, max(v) + 8)
    style(ax, "Growth rates on small cells are mostly noise",
          f"State x occupation cells, year on year to {month_name(nb['years'].iloc[0][-7:])}, by base size")
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    snap = json.loads((ROOT / "data" / "SNAPSHOT.json").read_text())
    occ, ivi_region, sa4, skill = load_all()

    h = P.headline(occ, skill)
    last = h["month"]
    year_ago = P.shift_month(last, -12)
    sa = P.skill_series(skill, "seasonally_adjusted")
    t3 = P.national_3ma(occ)
    avg2019_sa = P.year_avg(sa, "2019")

    sr = P.seasonal_ratio(occ, skill)
    add = P.additivity(skill, occ, last)
    sup = P.suppressed(occ)
    cov_ivi = P.regional_coverage(occ, ivi_region)
    cov_sa4 = P.regional_coverage(occ, sa4)
    cov_state = P.regional_coverage_by_state(occ, ivi_region, last)
    wide = P.occupation_wide(occ)
    sizes = P.cell_sizes(wide, last)
    noise = pd.concat([P.noise_by_base(wide, year_ago, last),
                       P.noise_by_base(wide, "2018-08", "2019-08")], ignore_index=True)
    risers_all = P.top_risers(wide, year_ago, last)
    risers_20 = P.top_risers(wide, year_ago, last, min_base=20)
    titles = occ[occ["level"] == "occupation"].drop_duplicates("anzsco_code").set_index("anzsco_code")["anzsco_title"]
    occ_title = lambda code: titles[code]  # noqa: E731
    noise_now = noise[noise["years"] == f"{year_ago} to {last}"].reset_index(drop=True)

    # CSV outputs
    sr.round(4).to_csv(RESULTS / "seasonal_ratio.csv", index=False, lineterminator="\n")
    pd.DataFrame({"month": cov_ivi.index, "ivi_regions": cov_ivi.round(5).values}).merge(
        pd.DataFrame({"month": cov_sa4.index, "gccsa_sa4": cov_sa4.round(5).values}), how="left", on="month"
    ).to_csv(RESULTS / "regional_coverage.csv", index=False, lineterminator="\n")
    noise.round(4).to_csv(RESULTS / "noise_by_base.csv", index=False, lineterminator="\n")

    chart_national(sa, t3, avg2019_sa, CHARTS / "01_national_ads.png")
    chart_seasonal(sr, CHARTS / "02_seasonality.png")
    chart_coverage(cov_ivi, cov_sa4, CHARTS / "03_regional_coverage.png")
    chart_noise(noise_now, CHARTS / "04_small_cell_noise.png")

    # numbers used in the text
    jan = sr.loc[sr["cal_month"] == 1, "ratio_mean"].iloc[0] - 1
    low = sr.loc[sr["ratio_mean"].idxmin()]
    high = sr.loc[sr["ratio_mean"].idxmax()]
    sup_first = sup["unpublished_share"].iloc[0]
    sup_last = sup["unpublished_share"].iloc[-1]
    pre = cov_ivi[(cov_ivi.index >= "2011-01") & (cov_ivi.index <= "2017-12")]
    since = cov_ivi[cov_ivi.index >= "2023-01"]
    first_good = cov_ivi[cov_ivi >= 0.99].index[0]
    early = cov_ivi[cov_ivi.index < first_good]
    sa4_2019 = cov_sa4[cov_sa4.index.str[:4] == "2019"]
    cov_now = cov_ivi.iloc[-1]
    nat_growth = t3[last] / P.year_avg(t3, "2019") - 1
    reg = ivi_region[ivi_region["level"] == 1].groupby("month")["ads_3ma"].sum()
    reg_growth = reg[last] / P.year_avg(reg, "2019") - 1
    small = sizes.loc[sizes["ads_3ma"].isin(["0", "over 0 to 5", "over 5 to 10", "over 10 to 20"]), "cells"].sum()
    total_cells = sizes["cells"].sum()
    under20_big = noise_now.loc[noise_now["bin"].isin(["over 0 to 5", "over 5 to 10", "over 10 to 20"])]
    big = lambda b: noise_now.loc[noise_now["bin"] == b, "share_big_swing"].iloc[0]  # noqa: E731
    n_occ = occ.loc[(occ["level"] == "occupation") & ~occ["suppressed"], "anzsco_code"].nunique()
    n_regions = ivi_region.loc[ivi_region["level"] == 1, "region"].nunique()
    n_sa4 = sa4.loc[sa4["level"] == 1, "region_code"].nunique()
    n_groups = ivi_region.loc[ivi_region["level"] == 3, "anzsco_code"].nunique()
    custom = sorted(c for c in ivi_region.loc[ivi_region["level"] == 3, "anzsco_code"].unique()
                    if not c.isdigit())

    add_t = add.assign(
        sum_of_parts=add["sum_of_parts"].map(lambda v: n(v)),
        published_total=add["published_total"].map(lambda v: n(v)),
        gap=add["gap"].map(lambda v: n(v).replace("-", "−")),
        gap_pct=add["gap_pct"].map(lambda v: pct(v, 2, sign=True)),
    ).rename(columns={"series": "Series", "check": "Check", "sum_of_parts": "Sum of parts",
                      "published_total": "Published total", "gap": "Gap", "gap_pct": "Gap %"})
    sr_t = pd.DataFrame({
        "3 months ending": MONTHS,
        "Raw vs SA (mean)": [pct(v - 1, 1, sign=True) for v in sr["ratio_mean"]],
        "Lowest year": [pct(v - 1, 1, sign=True) for v in sr["ratio_min"]],
        "Highest year": [pct(v - 1, 1, sign=True) for v in sr["ratio_max"]],
    })
    cov_state_t = pd.DataFrame({"State": cov_state.index,
                                "Placed in an IVI region": [pct(v, 1) for v in cov_state.values]})
    sizes_t = sizes.assign(share=sizes["share"].map(lambda v: pct(v, 1))).rename(
        columns={"ads_3ma": f"Ads a month, {month_name(last)}", "cells": "Cells", "share": "Share"})
    noise_t = noise.assign(
        share_big_swing=noise["share_big_swing"].map(lambda v: pct(v, 1)),
        iqr_change=noise["iqr_change"].map(lambda v: f"{v * 100:.0f} pts"),
    ).rename(columns={"years": "Years", "bin": "Base (ads a month)", "cells": "Cells",
                      "share_big_swing": "Moved more than ±50%", "iqr_change": "Middle 50% of changes spans"})
    snap_t = pd.DataFrame([
        {"Table": f"`{v['file']}`", "Rows": n(v["rows"]), "Months": f"{v['first_month']} to {v['last_month']}",
         "Empty values": n(v["empty_values"])} for v in snap["tables"].values()])

    lines = [
        "# Part 1: source profile",
        "",
        "_Generated by `scripts/profile_source.py` from the snapshot in `data/`. Do not edit by hand._",
        "",
        f"Source: {snap['source']}. Licence: {snap['licence']}.",
        "",
        "## Snapshot",
        "",
        md_table(snap_t),
        "",
        f"- {n(n_occ)} published 4-digit ANZSCO occupations by state and territory, plus "
        f"{len(sup.attrs['titles'])} suppressed ones.",
        f"- {n_regions} IVI regions and {n_sa4} GCCSA/SA4 areas, each split into {n_groups} 2-digit occupation "
        f"groups. {len(custom)} of the group codes contain a letter ({', '.join(custom[:4])} …): they are "
        "JSA's custom groups, not standard ANZSCO, so they can't be joined to the 4-digit file by code.",
        "",
        f"## The latest month, three ways ({month_name(last)})",
        "",
        "| Measure | Ads | Use it for |",
        "|---|---|---|",
        f"| Seasonally adjusted | {n(h['ads_sa'])} | JSA's headline; month-on-month change |",
        f"| Trend | {n(h['ads_trend'])} | Direction, smoothed |",
        f"| Raw, 3-month average | {n(h['ads_3ma'])} | The only measure for occupations and regions; "
        "compare the same month a year apart |",
        "",
        f"Reconciliation with JSA's release: the seasonally adjusted series changed by {n(h['sa_change'])} ads "
        f"({pct(h['sa_change_pct'], 1, sign=True)}) from {month_name(h['prev_month'])}; the release says "
        "\"increased by 0.3% (or 560 job advertisements) … to stand at 212,400\". "
        f"It is {pct(h['sa_vs_2019'], 1)} above the 2019 monthly average (the release says \"around 25%\"); "
        f"the raw 3-month average is {pct(h['ma3_vs_2019'], 1)} above its own 2019 average.",
        "",
        f"- **Demand is cooling, from a high level.** The 12 months to {month_name(last)} averaged "
        f"{n(h['last12_avg'])} ads a month (raw), {pct(h['last12_vs_prev12'], 1, sign=True)} on the 12 months "
        f"before, but still {pct(h['last12_vs_2019'], 1)} above 2019.",
        f"- **It is not a record.** The seasonally adjusted peak was {n(h['sa_peak'])} in "
        f"{month_name(h['sa_peak_month'])}; the latest month is {pct(-h['sa_vs_peak'], 1)} below it.",
        "",
        "![National job ads](charts/01_national_ads.png)",
        "",
        "## Traps in the data, and the rule each one sets",
        "",
        "### 1. The raw 3-month average is seasonal",
        "",
        f"Occupation and regional data come only as raw 3-month averages. Against the seasonally adjusted "
        f"series (averaged over the same 3 months, 2010 to 2019), the raw figure runs "
        f"{pct(low['ratio_mean'] - 1, 1, sign=True)} in the 3 months ending {MONTHS[int(low['cal_month']) - 1]} "
        f"and {pct(high['ratio_mean'] - 1, 1, sign=True)} in the 3 months ending "
        f"{MONTHS[int(high['cal_month']) - 1]}. So the raw figure falls about "
        f"{abs(low['ratio_mean'] / high['ratio_mean'] - 1) * 100:.0f}% from "
        f"{MONTHS[int(high['cal_month']) - 1]} to {MONTHS[int(low['cal_month']) - 1]} in a normal year: "
        "that is the calendar, not the market.",
        "",
        "**Rule:** occupation and regional changes are measured year on year on the same month, or as "
        "12-month averages. Never month on month.",
        "",
        md_table(sr_t),
        "",
        "![Seasonality](charts/02_seasonality.png)",
        "",
        "### 2. Seasonally adjusted and trend series don't add up",
        "",
        "JSA adjusts each series separately, so the parts of an adjusted series don't sum to its total. The "
        "raw 3-month averages do add up across states, but not across occupations (see trap 3).",
        "",
        md_table(add_t),
        "",
        "**Rule:** shares and mixes (an occupation's share of a state, a state's share of the nation) are "
        "computed on raw 3-month averages only, never on adjusted series.",
        "",
        "### 3. Suppressed occupations hold a growing slice of ads",
        "",
        f"JSA suppresses {len(sup.attrs['titles'])} occupations as too unreliable: "
        f"{', '.join(sup.attrs['titles'])}. They have no figures at all, so the published occupations add "
        f"to less than the total. The gap (the suppressed occupations, plus rounding) rose from {pct(sup_first, 2)} in "
        f"{sup['year'].iloc[0]} to {pct(sup_last, 2)} in {sup['year'].iloc[-1]} (January to {pd.Period(last, 'M').strftime('%B')}).",
        "",
        "**Rule:** an occupation's share uses the published total as the denominator, and the report says "
        f"the suppressed {pct(sup_last, 1)} is excluded. Totals are never rebuilt by adding occupations.",
        "",
        "### 4. Regions miss about 3% of ads, and the gap opened after 2019",
        "",
        f"The 37 IVI regions held {pct(pre.min(), 1)} to {pct(pre.max(), 1)} of national ads in 2011-2017. "
        f"Since 2023 they hold {pct(since.min(), 1)} to {pct(since.max(), 1)} ({pct(cov_now, 1)} in "
        f"{month_name(last)}); the GCCSA/SA4 file shows the same drop. The rest are ads coded to a state but "
        f"not a region. So the regions' combined ads rose {pct(reg_growth, 1)} from the 2019 average to "
        f"{month_name(last)}, against {pct(nat_growth, 1)} for the nation: about "
        f"{(nat_growth - reg_growth) * 100:.0f} points of apparent regional lag is coding, not demand.",
        "",
        f"Each regional file is also rough where it was backcast: the IVI regions held {pct(early.min(), 1)} "
        f"to {pct(early.max(), 1)} of national ads in {month_name(early.index[0])} to "
        f"{month_name(early.index[-1])} (the series was built in September 2010 and backcast to May), and "
        f"the GCCSA/SA4 areas swung between {pct(sa4_2019.min(), 1)} and {pct(sa4_2019.max(), 1)} in 2019 "
        "(built in 2024 and backcast to 2019), more than 100% in some months.",
        "",
        "The gap also differs by state, so it isn't spread evenly. IVI regions are best-fit labour markets, "
        "so a state's regions needn't add to exactly its total (ACT's one region holds slightly more):",
        "",
        md_table(cov_state_t),
        "",
        "**Rule:** a region is compared with other regions (or with the sum of regions), never with the "
        "national or state total. The two regional geographies are kept apart: they use different "
        f"boundaries and start in different years. IVI region series are used from {month_name(first_good)}, "
        "the first month above 99%, and give the pre-COVID (2019) baseline; the GCCSA/SA4 areas are used "
        "for year-on-year views only.",
        "",
        "![Regional coverage](charts/03_regional_coverage.png)",
        "",
        "### 5. Most state × occupation cells are small, and small cells are noisy",
        "",
        f"Of the {n(total_cells)} published state × occupation cells in {month_name(last)}, {n(small)} "
        f"({pct(small / total_cells, 0)}) have 20 or fewer ads a month. Year on year, "
        f"{pct(big('over 0 to 5'), 0)} of cells with more than 0 and up to 5 ads moved by more than 50%, against "
        f"{pct(big('over 20 to 50'), 0)} of cells with 20 to 50 and {pct(big('over 100'), 1)} of cells "
        "over 100. The pattern is the same in 2018-19, before COVID.",
        "",
        f"Without a floor, a \"fastest growing\" list is all noise: the top {len(risers_all)} year-on-year "
        f"risers all started from {n(risers_all['base'].max(), 2)} ads a month or fewer, led by "
        f"{risers_all['state'].iloc[0]} {occ_title(risers_all['anzsco_code'].iloc[0])} "
        f"({n(risers_all['base'].iloc[0], 2)} to {n(risers_all['now'].iloc[0], 2)}, "
        f"{pct(risers_all['change'].iloc[0], 0, sign=True)}). With the floor, the top riser is "
        f"{risers_20['state'].iloc[0]} {occ_title(risers_20['anzsco_code'].iloc[0])} "
        f"({n(risers_20['base'].iloc[0], 2)} to {n(risers_20['now'].iloc[0], 2)}, "
        f"{pct(risers_20['change'].iloc[0], 0, sign=True)}), a change big enough to look into.",
        "",
        "**Rule:** growth rankings only include cells averaging more than 20 ads a month in the base "
        "period; smaller cells are shown as counts, not percentages. State × occupation results are "
        "shown with their base size.",
        "",
        md_table(sizes_t),
        "",
        md_table(noise_t),
        "",
        "![Small-cell noise](charts/04_small_cell_noise.png)",
        "",
        "### 6. Job ads are not jobs",
        "",
        "From JSA's methodology: the IVI counts new ads on SEEK, CareerOne and Workforce Australia only, "
        "after removing duplicates. It misses jobs filled by word of mouth, employer sites and social "
        "media, counts a multi-position ad once, and leans towards higher-skilled roles.",
        "",
        "**Rule:** results are described as *online job ads* (a demand signal), never as vacancies or hires.",
        "",
    ]
    (RESULTS / "SOURCE_PROFILE.md").write_text("\n".join(lines))
    print(f"wrote {RESULTS / 'SOURCE_PROFILE.md'}")


if __name__ == "__main__":
    main()
