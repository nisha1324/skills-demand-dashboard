"""Part 3 report: where employers are advertising, capital cities vs regional Australia.

Reads the tidy snapshot in data/ and writes (to results/ by default):
- REGIONAL_DEMAND.md        the report (every figure comes from this script)
- ivi_regions.csv           the 37 IVI regions: 12-month averages, growth, vs 2019
- region_group.csv          37 regions x 48 occupation groups, same measures plus location quotient
- sa4_areas.csv             the 50 GCCSA/SA4 areas, year on year only
- regional_share.csv        regional share of placed ads, rolling 12 months, from Sep 2011
- charts/09-12 *.png
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ivi import demand as D  # noqa: E402
from ivi import regions as R  # noqa: E402
from ivi.load import load_ivi_region, load_occupation_state, load_sa4_region  # noqa: E402
from scripts.occupation_demand import ads, signed, signed_n  # noqa: E402
from scripts.profile_source import (BLUE, GRID, INK, INK_2, MUTED, ORANGE, SAVE, md_table,  # noqa: E402
                                    month_name, n, pct, style)

ROOT = Path(__file__).resolve().parents[1]
LIGHT_BLUE = "#9ec2ef"   # lighter step of the same blue, for "before" in the dumbbell
MIN_GROUP = 100.0        # ads a month for a region x group cell to be called a specialism
MIN_REGION_RISER = 500.0  # ads a month for a region to appear in the "fastest growing" read-out
TOP_GROUPS = 15
CMP_COLS = ["now", "prev", "y2019", "latest", "year_ago", "yoy", "vs_2019", "latest_yoy", "change"]


def pts(x: float) -> str:
    return f"{x:+.1f} points".replace("-", "−")


def and_list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def short(region: str) -> str:
    return region.replace(" and ", " & ")


def chart_share(share: pd.Series, bound: pd.Series, s2019: float, end: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    x = pd.PeriodIndex(share.index, freq="M").to_timestamp()
    ax.plot(x, share.values * 100, color=BLUE, linewidth=2, label="Share of ads placed in a region")
    xb = pd.PeriodIndex(bound.index, freq="M").to_timestamp()
    ax.plot(xb, bound.values * 100, color=ORANGE, linewidth=1.6,
            label="Lowest it could be: every unplaced ad counted as a capital's")
    ax.axhline(s2019 * 100, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(pd.Timestamp("2015-07-01").to_pydatetime(), s2019 * 100 + 0.35, f"2019 average: {s2019 * 100:.1f}%", color=INK_2,
            fontsize=9, ha="center")
    pad = timedelta(days=60)
    end_x, end_xb = x[-1].to_pydatetime(), xb[-1].to_pydatetime()
    ax.text(end_x + pad, share.iloc[-1] * 100 + 0.15, f"{share.iloc[-1] * 100:.1f}%", color=INK, fontsize=9,
            ha="left", va="center")
    ax.text(end_xb + pad, bound.iloc[-1] * 100 - 0.25, f"{bound.iloc[-1] * 100:.1f}%", color=INK, fontsize=9,
            ha="left", va="center")
    ax.set_xlim(x[0].to_pydatetime() - timedelta(days=120), end_x + timedelta(days=420))
    ax.set_ylim(15, 34)
    ax.set_ylabel("Regional share of ads (%)")
    ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK_2)
    style(ax, "Regional Australia's share of job ads",
          f"Ads outside the 8 capital-city regions, 12-month rolling average to {month_name(end)}. "
          "Source: JSA Internet Vacancy Index")
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_regions(c: pd.DataFrame, end: str, path: Path) -> None:
    d = c.sort_values("vs_2019")
    v = d["vs_2019"] * 100
    fig, ax = plt.subplots(figsize=(9, 10))
    colours = [ORANGE if a == "capital" else BLUE for a in d["area"]]
    y = np.arange(len(d))
    ax.barh(y, v, color=colours, height=0.66)
    ax.axvline(0, color=INK_2, linewidth=0.8)
    for i, x in enumerate(v):
        ax.text(x + (2 if x >= 0 else -2), i, f"{x:+.0f}%".replace("-", "−"), va="center",
                ha="left" if x >= 0 else "right", fontsize=8, color=INK)
    ax.set_yticks(y, [f"{short(r)} ({s})" for r, s in zip(d.index, d["state"])], fontsize=8.5)
    ax.set_xlim(v.min() - 22, v.max() + 18)
    ax.tick_params(length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Change in ads a month, 12-month average vs 2019 (%)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ORANGE, label="Capital-city region"),
                       Patch(color=BLUE, label="Regional")],
              loc="lower right", frameon=False, fontsize=9, labelcolor=INK_2)
    fig.text(0.01, 0.985, "Job ads by IVI region, against 2019", ha="left", va="top", fontsize=12,
             fontweight="bold", color=INK)
    fig.text(0.01, 0.962, va="top", s=f"12 months to {month_name(end)} vs the 2019 average. "
             "Source: JSA Internet Vacancy Index", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_dumbbell(g: pd.DataFrame, end: str, path: Path) -> None:
    d = g.sort_values("share_now")
    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    y = np.arange(len(d))
    for i, (a, b) in enumerate(zip(d["share_2019"] * 100, d["share_now"] * 100)):
        ax.plot([a, b], [i, i], color=GRID, linewidth=2.5, zorder=1)
    ax.scatter(d["share_2019"] * 100, y, s=46, color=LIGHT_BLUE, zorder=2, label="2019",
               edgecolor="white", linewidth=1)
    ax.scatter(d["share_now"] * 100, y, s=46, color=BLUE, zorder=3,
               label=f"12 months to {month_name(end)}", edgecolor="white", linewidth=1)
    for i, (a, b) in enumerate(zip(d["share_2019"] * 100, d["share_now"] * 100)):
        ax.text(max(a, b) + 1.2, i, f"{b:.0f}%", va="center", fontsize=8, color=INK)
    ax.set_yticks(y, d["title"], fontsize=8.5)
    ax.tick_params(length=0)
    ax.set_xlim(0, max(d["share_now"].max(), d["share_2019"].max()) * 100 + 8)
    ax.set_xlabel("Share of the group's placed ads outside the capital-city regions (%)")
    ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK_2)
    style(ax, f"Regional share of ads, the {len(d)} largest occupation groups",
          "Groups sorted by regional share now. Source: JSA Internet Vacancy Index")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    fig.tight_layout()
    fig.savefig(path, **SAVE)
    plt.close(fig)


def chart_sa4(c: pd.DataFrame, end: str, path: Path) -> None:
    d = c.sort_values("yoy")
    v = d["yoy"] * 100
    fig, ax = plt.subplots(figsize=(9, 11))
    y = np.arange(len(d))
    ax.barh(y, v, color=[ORANGE if lvl == "GCCSA" else BLUE for lvl in d["region_level"]], height=0.66)
    ax.axvline(0, color=INK_2, linewidth=0.8)
    for i, x in enumerate(v):
        ax.text(x + (0.5 if x >= 0 else -0.5), i, f"{x:+.1f}%".replace("-", "−"), va="center",
                ha="left" if x >= 0 else "right", fontsize=7.5, color=INK)
    ax.set_yticks(y, [f"{nm} ({s})" for nm, s in zip(d["region_name"], d["state"])], fontsize=8)
    ax.set_xlim(v.min() - 6, v.max() + 5)
    ax.tick_params(length=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_xlabel("Change in ads a month, 12-month average vs the year before (%)")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=ORANGE, label="Greater capital city (GCCSA)"),
                       Patch(color=BLUE, label="Regional area (SA4)")],
              loc="lower right", frameon=False, fontsize=9, labelcolor=INK_2)
    fig.text(0.01, 0.987, "Job ads by area, year on year", ha="left", va="top", fontsize=12,
             fontweight="bold", color=INK)
    fig.text(0.01, 0.966, va="top", s=f"GCCSA and SA4 areas, 12 months to {month_name(end)} vs the 12 months before. "
             "Source: JSA Internet Vacancy Index", fontsize=9, color=INK_2)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, **SAVE)
    plt.close(fig)


def main(out: Path | None = None) -> None:
    out = out or ROOT / "results"
    charts = out / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    occ = load_occupation_state()
    r = load_ivi_region()
    s = load_sa4_region()

    end = r["month"].max()
    if s["month"].max() != end or occ["month"].max() != end:
        raise ValueError("files end in different months")
    ago = D.shift_month(end, -12)
    nat = D.compare(D.totals_wide(occ), end).loc["AUST"]

    # capital vs regional
    aw = R.area_wide(r)
    ac = D.compare(aw, end)
    bounds = R.share_bounds(ac, nat)
    share = R.regional_share(aw)
    # the same rolling share against the national total: the lowest it could be
    roll_nat = D.totals_wide(occ).loc["AUST"].T.rolling(12).mean()
    roll_reg = aw.loc["regional"].T.rolling(12).mean()
    bound_series = (roll_reg / roll_nat).reindex(share.index)
    yearly = share[share.index.str.endswith("-12")]
    first_peak = share[share.index <= "2021-12"]
    trough = share[share.index > first_peak.idxmax()]
    trough_month = trough.idxmin()
    climb = share[share.index >= trough_month].diff().dropna()
    at_high = bool(share.iloc[-1] == share.max())
    capital_drop = ac.loc["capital", "change"]
    regional_change = ac.loc["regional", "change"]

    # the 37 regions
    states = R.region_states(r)
    rc = D.compare(R.region_wide(r), end)
    rc["state"] = states.reindex(rc.index).values
    rc["area"] = R.area_of(pd.Series(rc.index, index=rc.index))
    caps = rc[rc["area"] == "capital"].sort_values("vs_2019")
    regs = rc[rc["area"] == "regional"]
    below_2019 = rc[rc["vs_2019"] < 0].sort_values("vs_2019")
    regional_min = regs["vs_2019"].idxmin()
    regional_rise = regs[regs["now"] >= MIN_REGION_RISER].sort_values("yoy", ascending=False)

    # occupation groups, capital vs regional
    amg = D.compare(R.area_wide(r, level=2), end)
    a2 = D.compare(R.area_wide(r, level=3), end)
    titles = r[r["level"] == 3].drop_duplicates("anzsco_code").set_index("anzsco_code")["anzsco_title"]
    grp = pd.DataFrame({
        "title": titles,
        "regional_now": a2.loc["regional", "now"],
        "capital_now": a2.loc["capital", "now"],
        "regional_2019": a2.loc["regional", "y2019"],
        "capital_2019": a2.loc["capital", "y2019"],
        "regional_yoy": a2.loc["regional", "yoy"],
        "capital_yoy": a2.loc["capital", "yoy"],
        "regional_change": a2.loc["regional", "change"],
        "capital_change": a2.loc["capital", "change"],
    })
    grp["total_now"] = grp["regional_now"] + grp["capital_now"]
    grp["share_now"] = grp["regional_now"] / grp["total_now"]
    grp["share_2019"] = grp["regional_2019"] / (grp["regional_2019"] + grp["capital_2019"])
    top = grp.sort_values("total_now", ascending=False).head(TOP_GROUPS)
    reg_add = grp.sort_values("regional_change", ascending=False)
    cap_loss = grp.sort_values("capital_change")
    reg_up_cap_down = grp[(grp["regional_yoy"] > 0) & (grp["capital_yoy"] < 0)
                          & (grp["regional_now"] >= 1000)].sort_values("regional_now", ascending=False)

    # region x group
    rgw = R.region_wide(r, level=3)
    rg = D.compare(rgw, end)
    lq = R.location_quotient(rg["now"])
    rg["lq"] = lq
    leaders = R.region_leaders(rg, lq, titles, MIN_GROUP)
    spec = rg[rg["now"] >= MIN_GROUP].sort_values("lq", ascending=False)

    # GCCSA / SA4, year on year only
    sw = R.sa4_wide(s)
    sc = R.yoy_only(sw, end)
    sa4_state = s.drop_duplicates("region_name").set_index("region_name")["state"]
    sc_flat = sc.reset_index()
    sc_flat["state"] = sa4_state.reindex(sc_flat["region_name"]).values
    gcc_states = sc_flat[sc_flat["region_level"] == "GCCSA"].set_index("region_name")["state"]
    cross = R.capital_crosscheck(rc, sc, gcc_states)
    sa4_only = sc_flat[sc_flat["region_level"] == "SA4"]
    sa4_up = int((sa4_only["yoy"] > 0).sum())
    gcc_up = int((sc_flat[sc_flat["region_level"] == "GCCSA"]["yoy"] > 0).sum())
    level_tot = sc_flat.groupby("region_level")[["now", "prev", "latest", "year_ago"]].sum()
    level_tot["yoy"] = level_tot["now"] / level_tot["prev"] - 1
    level_tot["latest_yoy"] = level_tot["latest"] / level_tot["year_ago"] - 1
    same_sign = int((np.sign(cross["ivi_yoy"]) == np.sign(cross["gccsa_yoy"])).sum())
    max_gap = cross["gap_points"].abs().max()

    # CSVs: every row, as inputs for the dashboard (Part 4)
    rc_csv = rc[["state", "area"] + CMP_COLS].copy()
    rc_csv[CMP_COLS] = rc_csv[CMP_COLS].round(4)
    rc_csv.reset_index().to_csv(out / "ivi_regions.csv", index=False, lineterminator="\n")
    rg_csv = rg[CMP_COLS + ["lq"]].round(4).reset_index()
    rg_csv.insert(1, "state", states.reindex(rg_csv["region"]).values)
    rg_csv.insert(3, "group_title", titles.reindex(rg_csv["anzsco_code"]).values)
    rg_csv.to_csv(out / "region_group.csv", index=False, lineterminator="\n")
    sc_csv = sc_flat[["region_level", "region_name", "state", "now", "prev", "latest", "year_ago", "yoy",
                      "latest_yoy", "change"]].copy()
    sc_csv.iloc[:, 3:] = sc_csv.iloc[:, 3:].round(4)
    sc_csv.to_csv(out / "sa4_areas.csv", index=False, lineterminator="\n")
    pd.DataFrame({"month": share.index, "regional_share": share.round(5).values,
                  "lower_bound": bound_series.round(5).values}).to_csv(
        out / "regional_share.csv", index=False, lineterminator="\n")

    # charts
    chart_share(share, bound_series, bounds.loc["2019", "share_of_placed"], end, charts / "09_regional_share.png")
    chart_regions(rc, end, charts / "10_regions_vs_2019.png")
    chart_dumbbell(top, end, charts / "11_group_regional_share.png")
    chart_sa4(sc_flat, end, charts / "12_sa4_year_on_year.png")

    # tables
    def area_row(name, row, share_now, share19):
        return {"": name, "Ads a month (12-mo avg)": n(row["now"]), "vs year before": signed(row["yoy"]),
                "Change (ads a month)": signed_n(row["change"]),
                "Latest 3 months vs a year earlier": signed(row["latest_yoy"]), "vs 2019": signed(row["vs_2019"]),
                "Share of placed ads": pct(share_now, 1), "Share in 2019": pct(share19, 1)}

    b = bounds
    shift = (b.loc["now", "share_of_placed"] - b.loc["2019", "share_of_placed"]) * 100
    b_shift = (b.loc["now", "share_lower_bound"] - b.loc["2019", "share_lower_bound"]) * 100
    area_tab = pd.DataFrame([
        area_row("8 capital-city regions", ac.loc["capital"], 1 - b.loc["now", "share_of_placed"],
                 1 - b.loc["2019", "share_of_placed"]),
        area_row("29 regional areas", ac.loc["regional"], b.loc["now", "share_of_placed"],
                 b.loc["2019", "share_of_placed"]),
    ])
    bound_tab = pd.DataFrame({
        "": ["Ads placed in a region", "National total", "Not placed in any region",
             "Regional share of placed ads", "Regional share if every unplaced ad were a capital's"],
        "2019": [n(b.loc["2019", "placed"]), n(b.loc["2019", "national"]), n(b.loc["2019", "unplaced"]),
                 pct(b.loc["2019", "share_of_placed"], 1), pct(b.loc["2019", "share_lower_bound"], 1)],
        f"12 months to {month_name(end)}": [n(b.loc["now", "placed"]), n(b.loc["now", "national"]),
                                           n(b.loc["now", "unplaced"]), pct(b.loc["now", "share_of_placed"], 1),
                                           pct(b.loc["now", "share_lower_bound"], 1)],
    })
    year_tab = pd.DataFrame({"12 months to": [month_name(m) for m in yearly.index] + [month_name(end)],
                             "Regional share": [pct(v, 1) for v in yearly] + [pct(share.iloc[-1], 1)]})
    year_tab = year_tab.drop_duplicates("12 months to")
    mg_tab = pd.DataFrame({
        "Major group": [D.MAJOR_GROUPS[k] for k in D.MAJOR_GROUPS],
        "Capitals: ads a month": [n(amg.loc[("capital", k), "now"]) for k in D.MAJOR_GROUPS],
        "Capitals vs year before": [signed(amg.loc[("capital", k), "yoy"]) for k in D.MAJOR_GROUPS],
        "Capitals vs 2019": [signed(amg.loc[("capital", k), "vs_2019"]) for k in D.MAJOR_GROUPS],
        "Regional: ads a month": [n(amg.loc[("regional", k), "now"]) for k in D.MAJOR_GROUPS],
        "Regional vs year before": [signed(amg.loc[("regional", k), "yoy"]) for k in D.MAJOR_GROUPS],
        "Regional vs 2019": [signed(amg.loc[("regional", k), "vs_2019"]) for k in D.MAJOR_GROUPS],
    })
    reg_mg = amg.loc["regional"]
    cap_mg = amg.loc["capital"]
    groups_reg_above = int((reg_mg["vs_2019"] > 0).sum())
    cap_below = [D.MAJOR_GROUPS[k] for k in cap_mg.index if cap_mg.loc[k, "vs_2019"] < 0]
    grp_tab = pd.DataFrame({
        "Occupation group": top["title"].values,
        "Ads a month (all regions)": [n(v) for v in top["total_now"]],
        "Regional share 2019": [pct(v, 1) for v in top["share_2019"]],
        "Regional share now": [pct(v, 1) for v in top["share_now"]],
        "Regional vs year before": [signed(v) for v in top["regional_yoy"]],
        "Capitals vs year before": [signed(v) for v in top["capital_yoy"]],
    })
    reg_t = rc.sort_values("vs_2019", ascending=False)
    region_tab = pd.DataFrame({
        "Region": reg_t.index, "State": reg_t["state"].values,
        "Type": ["Capital" if a == "capital" else "Regional" for a in reg_t["area"]],
        "Ads a month (12-mo avg)": [n(v) for v in reg_t["now"]],
        "vs year before": [signed(v) for v in reg_t["yoy"]],
        "Latest 3 months vs a year earlier": [signed(v) for v in reg_t["latest_yoy"]],
        "vs 2019": [signed(v) for v in reg_t["vs_2019"]],
    })
    lead_tab = pd.DataFrame({
        "Region": leaders.index,
        "Largest group (ads a month)": [f"{a} ({ads(v)})" for a, v in zip(leaders["largest"], leaders["largest_now"])],
        f"Fastest rising (base above {D.FLOOR:.0f})": [
            "–" if t is None else f"{t} ({ads(p)} to {ads(v)}, {signed(y, 0)})"
            for t, p, v, y in zip(leaders["riser"], leaders["riser_prev"], leaders["riser_now"], leaders["riser_yoy"])],
        f"Most over-represented ({MIN_GROUP:.0f}+ ads)": [
            "–" if t is None else f"{t} ({lqv:.1f}×)" for t, lqv in zip(leaders["special"], leaders["special_lq"])],
    }).sort_values("Region")
    spec_tab = pd.DataFrame({
        "Region": [i[0] for i in spec.head(12).index],
        "Occupation group": [titles[i[1]] for i in spec.head(12).index],
        "Ads a month": [n(v) for v in spec.head(12)["now"]],
        "Location quotient": [f"{v:.1f}×" for v in spec.head(12)["lq"]],
        "vs year before": [signed(v) for v in spec.head(12)["yoy"]],
    })
    cross_tab = pd.DataFrame({
        "State": cross.index, "IVI region": cross["ivi_region"].values, "GCCSA": cross["gccsa"].values,
        "IVI: ads a month": [n(v) for v in cross["ivi_now"]], "GCCSA: ads a month": [n(v) for v in cross["gccsa_now"]],
        "IVI vs year before": [signed(v) for v in cross["ivi_yoy"]],
        "GCCSA vs year before": [signed(v) for v in cross["gccsa_yoy"]],
        "Gap": [pts(v) for v in cross["gap_points"]],
    })

    def sa4_tab(d):
        return md_table(pd.DataFrame({
            "Area": d["region_name"].values, "State": d["state"].values,
            "Ads a month (12-mo avg)": [n(v) for v in d["now"]], "Year before": [n(v) for v in d["prev"]],
            "vs year before": [signed(v) for v in d["yoy"]],
            "Latest 3 months vs a year earlier": [signed(v) for v in d["latest_yoy"]],
        }))

    sa4_rank = sa4_only[sa4_only["prev"] > D.FLOOR]
    sa4_top = sa4_rank.sort_values("yoy", ascending=False).head(10)
    sa4_bottom = sa4_rank.sort_values("yoy").head(5)
    gcc_rows = sc_flat[sc_flat["region_level"] == "GCCSA"].sort_values("yoy")
    health = grp.loc["2H"] if "2H" in grp.index else None
    health_regions = rg.xs("2H", level=1).sort_values("change", ascending=False) if health is not None else None

    lines = [
        "# Part 3: regional demand",
        "",
        "_Generated by `scripts/regional_demand.py` from the snapshot in `data/`. Do not edit by hand._",
        "",
        "How every number here is measured (the rules come from Part 1, `SOURCE_PROFILE.md`, trap 4):",
        "",
        f"- **Two geographies, kept apart.** The 37 **IVI regions** (JSA's best-fit labour markets) are used "
        f"from {month_name(R.START)}, the first month they hold 99% of national ads, and carry the 2019 "
        "comparison. The 50 **GCCSA/SA4 areas** (8 greater capital cities, 42 regional SA4s) were backcast to "
        "2019 and are rough there, so they are used **year on year only**.",
        "- **Regions are compared with regions.** About 3% of ads are coded to a state but to no region, so a "
        "region is never compared with the national or state total. Shares are shares of ads placed in a region.",
        "- **Capital-city regions** are the 8 IVI regions containing a capital: "
        + ", ".join(f"{v} ({k})" for k, v in R.CAPITALS.items())
        + ". IVI regions aren't the ABS capital-city boundaries: Hobart's region takes in the south-east, "
        "and Canberra's is the whole territory. The other 29 regions are \"regional\".",
        f"- **12-month averages** to {month_name(end)} vs the 12 months before and vs calendar 2019; the latest "
        f"3 months vs the same 3 months a year earlier; no growth rate on a base of {D.FLOOR:.0f} ads a month "
        "or fewer (Part 2's method).",
        "",
        "## Capital cities vs regional Australia",
        "",
        md_table(area_tab),
        "",
        f"Regional ads are {signed(ac.loc['regional', 'vs_2019'])} on 2019, against "
        f"{signed(ac.loc['capital', 'vs_2019'])} for the capital-city regions. Over the last year the capitals "
        f"lost {n(-capital_drop)} ads a month ({signed(ac.loc['capital', 'yoy'])}) while regional areas "
        f"{'gained' if regional_change > 0 else 'lost'} {n(abs(regional_change))} ({signed(ac.loc['regional', 'yoy'])}). "
        f"**Regional Australia now holds {pct(b.loc['now', 'share_of_placed'], 1)} of placed ads, up from "
        f"{pct(b.loc['2019', 'share_of_placed'], 1)} in 2019.**",
        "",
        "**Is that a coding effect?** Part 1 found that the share of ads placed in any region fell after 2019. "
        "If every unplaced ad belonged to a capital, the regional share would still be "
        f"{pct(b.loc['now', 'share_lower_bound'], 1)}, against {pct(b.loc['2019', 'share_lower_bound'], 1)} in 2019 "
        f"on the same basis: a shift of {b_shift:.1f} points, against {shift:.1f} on placed ads. So unplaced ads can "
        f"explain at most {shift - b_shift:.1f} points of the shift; the rest is a move in where ads are placed.",
        "",
        md_table(bound_tab),
        "",
        "![Regional share](charts/09_regional_share.png)",
        "",
        f"The shift came in two steps. The rolling share jumped in 2020 and peaked at {pct(first_peak.max(), 1)} in "
        f"{month_name(first_peak.idxmax())}, fell back to {pct(trough.min(), 1)} in {month_name(trough_month)}, then "
        f"rose in {int((climb > 0).sum())} of the {len(climb)} months since, to {pct(share.iloc[-1], 1)}"
        + (f", the highest since the rolling series starts in {month_name(share.index[0])}" if at_high else "")
        + ". Rolling 12-month share, at each December:",
        "",
        md_table(year_tab),
        "",
        "## By occupation group",
        "",
        md_table(mg_tab),
        "",
        ("Regional ads are above 2019 in all 8 major groups" if groups_reg_above == 8 else
         f"Regional ads are above 2019 in {groups_reg_above} of the 8 major groups")
        + (f"; in the capitals, {' and '.join(cap_below)} are below 2019" if cap_below else "")
        + ". The 15 largest 2-digit groups, and how much of each is advertised outside the capitals:",
        "",
        md_table(grp_tab),
        "",
        "![Regional share by group](charts/11_group_regional_share.png)",
        "",
        "The groups that added the most regional ads on the year: "
        + "; ".join(f"{r_['title']} ({signed_n(r_['regional_change'])} a month, {signed(r_['regional_yoy'])})"
                    for _, r_ in reg_add.head(3).iterrows())
        + ". Those that lost the most in the capitals: "
        + "; ".join(f"{r_['title']} ({signed_n(r_['capital_change'])}, {signed(r_['capital_yoy'])})"
                    for _, r_ in cap_loss.head(3).iterrows()) + ".",
        "",
        f"{len(reg_up_cap_down)} groups with 1,000+ regional ads a month rose in the regions while falling in the "
        "capitals: " + "; ".join(f"{r_['title']} (regional {signed(r_['regional_yoy'])}, capitals "
                                 f"{signed(r_['capital_yoy'])})" for _, r_ in reg_up_cap_down.iterrows()) + ".",
        "",
        "## The 37 IVI regions",
        "",
        ("Every one of the 29 regional areas is above 2019"
         if (regs["vs_2019"] > 0).all() else "Not every regional area is above 2019")
        + f" (the least is {regional_min}, {signed(regs.loc[regional_min, 'vs_2019'])}). "
        + (and_list([f"{r_} ({signed(below_2019.loc[r_, 'vs_2019'])})" for r_ in below_2019.index])
           + (" are" if len(below_2019) > 1 else " is") + " below it"
           + (", all capital-city regions." if (below_2019["area"] == "capital").all() else ".")
           if len(below_2019) else "No region is below 2019."),
        "",
        "![Regions vs 2019](charts/10_regions_vs_2019.png)",
        "",
        md_table(region_tab),
        "",
        f"Regional areas with {MIN_REGION_RISER:,.0f}+ ads a month that grew most on the year: "
        + "; ".join(f"{r_} ({regional_rise.loc[r_, 'state']}, {n(regional_rise.loc[r_, 'now'])} a month, "
                    f"{signed(regional_rise.loc[r_, 'yoy'])})" for r_ in regional_rise.head(5).index) + ".",
        "",
        "## What each region advertises for",
        "",
        "**Location quotient** (LQ): a group's share of a region's ads over its share of all regions' ads. "
        "2.0× means the group is twice as common in that region's ads as across Australia: a sign of what "
        f"the local economy runs on. Pairs with {MIN_GROUP:.0f}+ ads a month, most over-represented first:",
        "",
        md_table(spec_tab),
        "",
        md_table(lead_tab),
        "",
        "## Year on year in the GCCSA/SA4 areas",
        "",
        f"The 8 greater capital cities together are {signed(level_tot.loc['GCCSA', 'yoy'])} on the year and the 42 "
        f"regional SA4s {signed(level_tot.loc['SA4', 'yoy'])}; {gcc_up} of the 8 capitals and {sa4_up} of the 42 "
        "regional areas grew.",
        "",
        "**The two geographies agree on the capitals.** They use different boundaries, so the levels differ, "
        f"but the year-on-year change has the same sign in {same_sign} of 8 and differs by at most "
        f"{max_gap:.1f} points:",
        "",
        md_table(cross_tab),
        "",
        "![SA4 year on year](charts/12_sa4_year_on_year.png)",
        "",
        "### Regional SA4s growing fastest",
        "",
        sa4_tab(sa4_top),
        "",
        f"{int((sa4_top['state'] == 'NSW').sum())} of the 10 are in NSW. (\"Capital Region\" is the regional NSW SA4 "
        "around the ACT, not a capital city.)" if "Capital Region" in set(sa4_top["region_name"]) else
        f"{int((sa4_top['state'] == 'NSW').sum())} of the 10 are in NSW.",
        "",
        "### Regional SA4s falling most",
        "",
        sa4_tab(sa4_bottom),
        "",
        "### Greater capital cities",
        "",
        sa4_tab(gcc_rows),
        "",
        "## So what for the business?",
        "",
        f"- **Recruiters:** 3 in 10 placed ads are now outside the capitals "
        f"({pct(b.loc['now', 'share_of_placed'], 1)}, from {pct(b.loc['2019', 'share_of_placed'], 1)} in 2019), and "
        f"that part of the market held up on the year ({signed(ac.loc['regional', 'yoy'])}) while the capitals fell "
        f"({signed(ac.loc['capital', 'yoy'])}). A desk that only covers the capitals is working the shrinking part. "
        "The fastest-growing big regional markets: "
        + ", ".join(f"{r_} ({signed(regional_rise.loc[r_, 'yoy'])})" for r_ in regional_rise.head(3).index) + ".",
        ]
    if health is not None:
        lines.append(
            f"- **Training providers:** {pct(health['share_now'], 0)} of ads for medical practitioners and nurses are "
            f"regional (from {pct(health['share_2019'], 0)} in 2019), and regional ads for them rose "
            f"{signed(health['regional_yoy'])} on the year while the capitals' were {signed(health['capital_yoy'])}. "
            "The regions adding the most: "
            + ", ".join(f"{r_} ({signed_n(health_regions.loc[r_, 'change'])} a month)"
                        for r_ in health_regions.head(3).index)
            + f". Across all placed ads the group changed by {signed_n(health['regional_change'] + health['capital_change'])} "
            f"a month, of which regional areas {signed_n(health['regional_change'])} and the capitals "
            f"{signed_n(health['capital_change'])}. Check single jumps before acting: {health_regions.index[0]}'s "
            f"rose from {ads(health_regions.iloc[0]['prev'])} to {ads(health_regions.iloc[0]['now'])} a month in a year, "
            "which a few large employers can cause. Health and care courses have a case for regional campuses or placements; ICT courses don't "
            f"(only {pct(grp.loc['26', 'share_now'], 1)} of ICT professional ads are regional).")
    lines += [
        "- **Employers and workforce planners:** "
        + and_list([f"{r_} ({signed(caps.loc[r_, 'vs_2019'])})" for r_ in below_2019.index])
        + " have fewer ads than in 2019, so employers there are competing with fewer other ads for staff. "
        + ("Every regional area has more ads than in 2019" if (regs["vs_2019"] > 0).all()
           else "Most regional areas have more ads than in 2019")
        + ": a regional employer should plan for more competition for the same local workers than before COVID.",
        "- **A caution:** about 3% of ads aren't placed in any region, and IVI regions are labour-market "
        "areas, not council areas. Use the region figures to rank and compare places, not as exact counts.",
        "",
    ]
    (out / "REGIONAL_DEMAND.md").write_text("\n".join(lines))
    print(f"wrote {out / 'REGIONAL_DEMAND.md'}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
