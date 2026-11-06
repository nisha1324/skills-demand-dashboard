"""Checks on what the IVI numbers mean, used by scripts/profile_source.py.

Every function takes tidy frames (as written by scripts/build_snapshot.py) and
returns plain numbers or small frames, so tests can feed them tiny fixtures.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

STATES = ["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"]


def national_3ma(occ: pd.DataFrame) -> pd.Series:
    """Australia total, 3-month average of raw (unadjusted) ad counts, by month."""
    t = occ[(occ["level"] == "total") & (occ["state"] == "AUST")]
    return t.set_index("month")["ads_3ma"].sort_index()


def skill_series(skill: pd.DataFrame, series: str, state: str = "AUST", level: int = 0) -> pd.Series:
    s = skill[(skill["series"] == series) & (skill["state"] == state) & (skill["skill_level"] == level)]
    return s.set_index("month")["ads"].sort_index()


def year_avg(s: pd.Series, year: str) -> float:
    return float(s[s.index.str[:4] == year].mean())


def headline(occ: pd.DataFrame, skill: pd.DataFrame) -> dict:
    """The latest month three ways, and the comparisons JSA's release makes."""
    t3 = national_3ma(occ)
    sa = skill_series(skill, "seasonally_adjusted")
    tr = skill_series(skill, "trend")
    last = t3.index.max()
    if sa.index.max() != last or tr.index.max() != last:
        raise ValueError("files end in different months")
    prev = sa.index[sa.index.get_loc(last) - 1]
    months = t3.index
    last12 = t3[months > shift_month(last, -12)]
    prev12 = t3[(months > shift_month(last, -24)) & (months <= shift_month(last, -12))]
    if len(last12) != 12 or len(prev12) != 12:
        raise ValueError("need 24 months for the 12-month comparison")
    return {
        "month": last,
        "prev_month": prev,
        "ads_3ma": float(t3[last]),
        "ads_sa": float(sa[last]),
        "ads_trend": float(tr[last]),
        "sa_change": float(sa[last] - sa[prev]),
        "sa_change_pct": float(sa[last] / sa[prev] - 1),
        "sa_vs_2019": float(sa[last] / year_avg(sa, "2019") - 1),
        "ma3_vs_2019": float(t3[last] / year_avg(t3, "2019") - 1),
        "last12_avg": float(last12.mean()),
        "prev12_avg": float(prev12.mean()),
        "last12_vs_prev12": float(last12.mean() / prev12.mean() - 1),
        "last12_vs_2019": float(last12.mean() / year_avg(t3, "2019") - 1),
        "sa_peak_month": sa.idxmax(),
        "sa_peak": float(sa.max()),
        "sa_vs_peak": float(sa[last] / sa.max() - 1),
    }


def shift_month(month: str, n: int) -> str:
    return (pd.Period(month, "M") + n).strftime("%Y-%m")


def seasonal_ratio(occ: pd.DataFrame, skill: pd.DataFrame, start: str = "2010-01",
                   end: str = "2019-12") -> pd.DataFrame:
    """How far the raw 3-month average sits from the seasonally adjusted level, by calendar month.

    The SA series is averaged over the same 3 months, so the ratio isolates
    seasonality. The window defaults to 2010-2019, before COVID distorted it.
    """
    t3 = national_3ma(occ)
    sa3 = skill_series(skill, "seasonally_adjusted").rolling(3).mean()
    df = pd.DataFrame({"ma3": t3, "sa3": sa3}).dropna()
    df = df[(df.index >= start) & (df.index <= end)]
    df["ratio"] = df["ma3"] / df["sa3"]
    df["cal_month"] = df.index.str[5:7].astype(int)
    out = df.groupby("cal_month")["ratio"].agg(["mean", "min", "max", "size"]).reset_index()
    out.columns = ["cal_month", "ratio_mean", "ratio_min", "ratio_max", "years"]
    return out


def additivity(skill: pd.DataFrame, occ: pd.DataFrame, month: str) -> pd.DataFrame:
    """Do the parts add to the published total? One row per check."""
    rows = []
    for series in ["seasonally_adjusted", "trend"]:
        s = skill[(skill["series"] == series) & (skill["month"] == month)]
        aust = s[(s["state"] == "AUST")]
        total = float(aust.loc[aust["skill_level"] == 0, "ads"].iloc[0])
        rows.append((series, "5 skill levels vs Australia total",
                     float(aust.loc[aust["skill_level"] > 0, "ads"].sum()), total))
        states = s[(s["state"] != "AUST") & (s["skill_level"] == 0)]
        rows.append((series, "8 states vs Australia total", float(states["ads"].sum()), total))
    m = occ[(occ["month"] == month) & (occ["level"] == "total")]
    total = float(m.loc[m["state"] == "AUST", "ads_3ma"].iloc[0])
    rows.append(("3-month average", "8 states vs Australia total",
                 float(m.loc[m["state"] != "AUST", "ads_3ma"].sum()), total))
    occs = occ[(occ["month"] == month) & (occ["state"] == "AUST") & (occ["level"] == "occupation")]
    rows.append(("3-month average", "published 4-digit occupations vs Australia total",
                 float(occs["ads_3ma"].sum()), total))
    df = pd.DataFrame(rows, columns=["series", "check", "sum_of_parts", "published_total"])
    df["gap"] = df["sum_of_parts"] - df["published_total"]
    df["gap_pct"] = df["gap"] / df["published_total"]
    return df


def suppressed(occ: pd.DataFrame) -> pd.DataFrame:
    """Occupations JSA suppresses, and the share of ads they hold (the published total less
    the published occupations), by year."""
    sup = sorted(occ.loc[occ["suppressed"], "anzsco_title"].unique())
    a = occ[occ["state"] == "AUST"]
    total = a[a["level"] == "total"].set_index("month")["ads_3ma"]
    pub = a[(a["level"] == "occupation") & ~a["suppressed"]].groupby("month")["ads_3ma"].sum()
    share = 1 - pub / total
    by_year = share.groupby(share.index.str[:4]).mean().rename("unpublished_share").reset_index()
    by_year.columns = ["year", "unpublished_share"]
    by_year.attrs["titles"] = sup
    return by_year


def regional_coverage(occ: pd.DataFrame, region: pd.DataFrame, level_col: str = "level") -> pd.Series:
    """Share of national ads (3-month average) that the regional file places in a region, by month."""
    national = national_3ma(occ)
    regions = region[region[level_col] == 1].groupby("month")["ads_3ma"].sum()
    return (regions / national).dropna()


def regional_coverage_by_state(occ: pd.DataFrame, region: pd.DataFrame, month: str) -> pd.Series:
    t = occ[(occ["month"] == month) & (occ["level"] == "total") & (occ["state"] != "AUST")]
    state_total = t.set_index("state")["ads_3ma"]
    r = region[(region["month"] == month) & (region["level"] == 1)].groupby("state")["ads_3ma"].sum()
    return (r / state_total).reindex(STATES)


def occupation_wide(occ: pd.DataFrame) -> pd.DataFrame:
    """State x 4-digit occupation cells (published only), one column per month."""
    c = occ[(occ["level"] == "occupation") & ~occ["suppressed"] & (occ["state"] != "AUST")]
    return c.pivot_table(index=["state", "anzsco_code"], columns="month", values="ads_3ma")


BASE_BINS = [0, 5, 10, 20, 50, 100, np.inf]
BASE_LABELS = ["over 0 to 5", "over 5 to 10", "over 10 to 20", "over 20 to 50", "over 50 to 100", "over 100"]


def noise_by_base(wide: pd.DataFrame, base_month: str, month: str, swing: float = 0.5) -> pd.DataFrame:
    """For state x occupation cells, how often the year-on-year change exceeds +/- swing,
    by the size of the base. Big swings on small bases are mostly noise."""
    d = pd.DataFrame({"base": wide[base_month], "now": wide[month]}).dropna()
    d = d[d["base"] > 0]
    d["change"] = d["now"] / d["base"] - 1
    d["bin"] = pd.cut(d["base"], BASE_BINS, labels=BASE_LABELS)
    g = d.groupby("bin", observed=False)["change"]
    out = pd.DataFrame({
        "cells": g.size(),
        "share_big_swing": g.apply(lambda x: float((x.abs() > swing).mean()) if len(x) else np.nan),
        "iqr_change": g.quantile(0.75) - g.quantile(0.25),
    }).reset_index()
    out.insert(0, "years", f"{base_month} to {month}")
    return out


def cell_sizes(wide: pd.DataFrame, month: str) -> pd.DataFrame:
    v = wide[month].dropna()
    bins = [-np.inf, 0, 5, 10, 20, 50, 100, np.inf]
    labels = ["0", "over 0 to 5", "over 5 to 10", "over 10 to 20", "over 20 to 50",
              "over 50 to 100", "over 100"]
    out = pd.cut(v, bins, labels=labels).value_counts().reindex(labels).rename("cells").reset_index()
    out.columns = ["ads_3ma", "cells"]
    out["share"] = out["cells"] / out["cells"].sum()
    return out
