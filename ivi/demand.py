"""Part 2 measures: which occupations are advertised for, and is that demand rising or cooling.

Every measure follows the Part 1 rules:
- occupation data are raw 3-month averages, so change is measured on 12-month averages
  (a full year, so the calendar cancels) or on the same month a year apart, never month on month;
- a growth rate is only shown when the base averages more than FLOOR ads a month;
- shares use the published total as the denominator; totals are never rebuilt from occupations;
- adjusted series (skill levels) are compared with themselves over time, never added up into mixes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 20.0  # ads a month in the base period, from Part 1 trap 5

MAJOR_GROUPS = {
    "1": "Managers",
    "2": "Professionals",
    "3": "Technicians and trades workers",
    "4": "Community and personal service workers",
    "5": "Clerical and administrative workers",
    "6": "Sales workers",
    "7": "Machinery operators and drivers",
    "8": "Labourers",
}

SKILL_LEVELS = {
    1: "Skill level 1 (bachelor degree or higher)",
    2: "Skill level 2 (advanced diploma or diploma)",
    3: "Skill level 3 (Certificate IV, or III with on-the-job training)",
    4: "Skill level 4 (Certificate II or III)",
    5: "Skill level 5 (Certificate I or secondary school)",
}


def shift_month(month: str, n: int) -> str:
    return (pd.Period(month, "M") + n).strftime("%Y-%m")


def window(end: str, n: int = 12) -> list[str]:
    """The n months ending at `end`, oldest first."""
    return [shift_month(end, -i) for i in range(n - 1, -1, -1)]


def _mean_over(wide: pd.DataFrame, months: list[str]) -> pd.Series:
    missing = [m for m in months if m not in wide.columns]
    if missing:
        raise ValueError(f"months missing from the data: {missing[0]} … ({len(missing)})")
    return wide[months].mean(axis=1)


def compare(wide: pd.DataFrame, end: str, floor: float = FLOOR) -> pd.DataFrame:
    """For each row of a (series x month) frame of 3-month averages:

    now          average of the 12 months ending `end`
    prev         average of the 12 months before that
    y2019        average of calendar 2019 (the pre-COVID baseline)
    yoy          now / prev - 1            (NaN when prev <= floor)
    vs_2019      now / y2019 - 1           (NaN when y2019 <= floor)
    latest       the `end` month itself
    latest_yoy   latest / same month a year earlier - 1 (NaN when that base <= floor)
    change       now - prev, in ads a month (shown whatever the base)
    """
    now = _mean_over(wide, window(end))
    prev = _mean_over(wide, window(shift_month(end, -12)))
    y2019 = _mean_over(wide, [f"2019-{m:02d}" for m in range(1, 13)])
    ago = wide[shift_month(end, -12)]
    out = pd.DataFrame({"now": now, "prev": prev, "y2019": y2019, "latest": wide[end],
                        "year_ago": ago})
    out["yoy"] = (out["now"] / out["prev"] - 1).where(out["prev"] > floor)
    out["vs_2019"] = (out["now"] / out["y2019"] - 1).where(out["y2019"] > floor)
    out["latest_yoy"] = (out["latest"] / out["year_ago"] - 1).where(out["year_ago"] > floor)
    out["change"] = out["now"] - out["prev"]
    return out


def turning(c: pd.DataFrame) -> pd.Series:
    """True where the latest month moves against the 12-month trend (one up, the other down)."""
    return (np.sign(c["yoy"]) * np.sign(c["latest_yoy"]) < 0).fillna(False)


def published(occ: pd.DataFrame) -> pd.DataFrame:
    return occ[(occ["level"] == "occupation") & ~occ["suppressed"]]


def titles(occ: pd.DataFrame) -> pd.Series:
    return published(occ).drop_duplicates("anzsco_code").set_index("anzsco_code")["anzsco_title"]


def national_wide(occ: pd.DataFrame) -> pd.DataFrame:
    """Published 4-digit occupations, Australia, one row per occupation, one column per month."""
    a = published(occ)
    return a[a["state"] == "AUST"].pivot_table(index="anzsco_code", columns="month", values="ads_3ma")


def totals_wide(occ: pd.DataFrame) -> pd.DataFrame:
    """Published state and Australia totals (these include the suppressed occupations)."""
    t = occ[occ["level"] == "total"]
    return t.pivot_table(index="state", columns="month", values="ads_3ma")


def major_group_wide(occ: pd.DataFrame, state: str | None = "AUST") -> pd.DataFrame:
    """Published occupations rolled up to the 8 ANZSCO major groups (first digit of the code).

    With state=None the index is (state, major group) for the 8 states and territories."""
    a = published(occ).assign(major=lambda d: d["anzsco_code"].str[0])
    if state is None:
        a = a[a["state"] != "AUST"]
        return a.groupby(["state", "major", "month"])["ads_3ma"].sum().unstack("month")
    a = a[a["state"] == state]
    return a.groupby(["major", "month"])["ads_3ma"].sum().unstack("month")


def contributions(c: pd.DataFrame, total_change: float) -> pd.DataFrame:
    """Each row's change in ads a month, and its share of the net change in the total."""
    d = c[["prev", "now", "change"]].copy()
    d["share_of_net"] = d["change"] / total_change
    return d.sort_values("change")


QUADRANTS = {
    (True, True): "Growing, above 2019",
    (False, True): "Cooling, still above 2019",
    (True, False): "Rising, still below 2019",
    (False, False): "Shrinking, below 2019",
}


def quadrant(c: pd.DataFrame, min_now: float = 500.0) -> pd.DataFrame:
    """Occupations with at least `min_now` ads a month, sorted into four demand states.

    An occupation needs both growth rates (both bases above the floor); a change of exactly
    zero counts as not growing."""
    d = c[(c["now"] >= min_now) & c["yoy"].notna() & c["vs_2019"].notna()].copy()
    d["quadrant"] = [QUADRANTS[(y > 0, v > 0)] for y, v in zip(d["yoy"], d["vs_2019"])]
    return d


def ranked(c: pd.DataFrame, col: str, k: int = 10, ascending: bool = False) -> pd.DataFrame:
    """Top k by a growth column; rows without a rate (base at or under the floor) are left out."""
    d = c[c[col].notna()]
    return d.sort_values([col, "now"], ascending=[ascending, False]).head(k)


def state_occupation_wide(occ: pd.DataFrame) -> pd.DataFrame:
    a = published(occ)
    a = a[a["state"] != "AUST"]
    return a.pivot_table(index=["state", "anzsco_code"], columns="month", values="ads_3ma")


def state_leaders(c: pd.DataFrame, k: int = 3) -> pd.DataFrame:
    """Per state: the k biggest occupations and the k fastest risers (base above the floor).

    `c` is compare() on state x occupation rows (index: state, anzsco_code)."""
    rows = []
    for state, g in c.groupby(level="state", sort=False):
        for kind, d in [("largest", g.sort_values("now", ascending=False).head(k)),
                        ("fastest rising", ranked(g, "yoy", k))]:
            for rank, (idx, r) in enumerate(d.iterrows(), start=1):
                rows.append({"state": state, "list": kind, "rank": rank, "anzsco_code": idx[1],
                             "now": r["now"], "prev": r["prev"], "yoy": r["yoy"]})
    return pd.DataFrame(rows)


def skill_level_compare(skill: pd.DataFrame, end: str, state: str = "AUST") -> pd.DataFrame:
    """Each skill level's seasonally adjusted series against itself: 12-month average vs the year
    before and vs 2019, and the latest month vs a year earlier. No shares (they don't add up)."""
    s = skill[(skill["series"] == "seasonally_adjusted") & (skill["state"] == state)]
    wide = s.pivot_table(index="skill_level", columns="month", values="ads")
    return compare(wide, end, floor=0.0)
