"""Part 3 measures: where in Australia employers are advertising, and how that is shifting.

The Part 1 rules for regions, applied here:
- a region is compared with other regions (or with the sum of regions), never with the national or
  state total, because about 3% of ads are coded to a state but not to any region;
- the two regional geographies are kept apart. The 37 IVI regions are used from October 2010 (the
  first month above 99% coverage) and carry the 2019 baseline; the GCCSA/SA4 areas (backcast to
  2019, and rough there) are used for year-on-year change only;
- change is measured on 12-month averages or the same months a year apart (the data are raw,
  seasonal 3-month averages), and no growth rate is shown on a base of FLOOR ads a month or fewer.
"""
from __future__ import annotations

import pandas as pd

from ivi import demand as D

START = "2010-10"  # first month the IVI regions hold 99%+ of national ads (Part 1, trap 4)

# IVI regions that contain a state or territory capital. JSA's regions are best-fit labour
# markets, so these aren't the ABS Greater Capital City areas: "Hobart & Southeast Tasmania"
# takes in the south-east, and "Canberra & ACT" is the whole territory.
CAPITALS = {
    "NSW": "Sydney",
    "VIC": "Melbourne",
    "QLD": "Brisbane",
    "SA": "Adelaide",
    "WA": "Perth",
    "TAS": "Hobart & Southeast Tasmania",
    "NT": "Darwin",
    "ACT": "Canberra & ACT",
}
AREAS = ["capital", "regional"]


def area_of(region: pd.Series) -> pd.Series:
    """"capital" for the 8 capital-city IVI regions, "regional" for the other 29."""
    return region.isin(set(CAPITALS.values())).map({True: "capital", False: "regional"})


def _from_start(r: pd.DataFrame, start: str = START) -> pd.DataFrame:
    return r[r["month"] >= start]


def region_states(r: pd.DataFrame) -> pd.Series:
    return r.drop_duplicates("region").set_index("region")["state"]


def region_wide(r: pd.DataFrame, level: int = 1, start: str = START) -> pd.DataFrame:
    """IVI regions, one column per month. level 1: index region (the region totals);
    level 2 or 3: index (region, anzsco_code) for major groups or 2-digit groups."""
    a = _from_start(r[r["level"] == level], start)
    idx = "region" if level == 1 else ["region", "anzsco_code"]
    return a.pivot_table(index=idx, columns="month", values="ads_3ma")


def area_wide(r: pd.DataFrame, level: int = 1, start: str = START) -> pd.DataFrame:
    """Capital-city regions vs the rest, summed. level 1: index area; else (area, anzsco_code)."""
    a = _from_start(r[r["level"] == level], start).assign(area=lambda d: area_of(d["region"]))
    keys = ["area"] if level == 1 else ["area", "anzsco_code"]
    return a.groupby(keys + ["month"])["ads_3ma"].sum().unstack("month")


def regional_share(area: pd.DataFrame, n: int = 12) -> pd.Series:
    """Regional (non-capital) share of all ads placed in a region, on n-month rolling averages.

    `area` is area_wide(level=1). A rolling year cancels the seasonal swing in the share
    (regional ads peak relative to the capitals in the 3 months to January)."""
    roll = area.T.rolling(n).mean().dropna()
    return (roll["regional"] / roll.sum(axis=1)).rename("regional_share")


def share_bounds(area_c: pd.DataFrame, national: pd.Series) -> pd.DataFrame:
    """Regional share now and in 2019, two ways.

    `area_c` is compare() on area_wide(level=1); `national` is compare() on the Australia total.
    "of placed ads" divides by the sum of regions (the Part 1 rule). "if every unplaced ad were in
    a capital" divides regional ads by the national total instead: the lowest the share could be
    if the ads that JSA couldn't place in a region all belonged to capitals."""
    rows = {}
    for col, label in [("y2019", "2019"), ("now", "now")]:
        placed = area_c[col].sum()
        rows[label] = {
            "regional": area_c.loc["regional", col],
            "placed": placed,
            "national": national[col],
            "unplaced": national[col] - placed,
            "share_of_placed": area_c.loc["regional", col] / placed,
            "share_lower_bound": area_c.loc["regional", col] / national[col],
        }
    return pd.DataFrame(rows).T


def location_quotient(cells: pd.Series) -> pd.Series:
    """How over-represented each group is in each region: the group's share of the region's ads
    over its share of all regions' ads. 1 = the same mix as all regions; 2 = twice as common.

    `cells` is indexed (region, anzsco_code); both shares come from these cells, so a group the
    data doesn't place in any region can't distort it."""
    region_tot = cells.groupby(level=0).transform("sum")
    group_tot = cells.groupby(level=1).transform("sum")
    return (cells / region_tot) / (group_tot / cells.sum())


def sa4_wide(s: pd.DataFrame, level: int = 1) -> pd.DataFrame:
    """GCCSA (capital) and SA4 (rest of state) areas, one column per month.
    level 1: index (region_level, region_name); else adds anzsco_code."""
    a = s[s["level"] == level]
    idx = ["region_level", "region_name"] + ([] if level == 1 else ["anzsco_code"])
    return a.pivot_table(index=idx, columns="month", values="ads_3ma")


def yoy_only(wide: pd.DataFrame, end: str, floor: float = D.FLOOR) -> pd.DataFrame:
    """compare() without the 2019 columns: for the GCCSA/SA4 file, whose 2019 is backcast."""
    return D.compare(wide, end, floor).drop(columns=["y2019", "vs_2019"])


def capital_crosscheck(ivi_c: pd.DataFrame, sa4_c: pd.DataFrame, states: pd.Series) -> pd.DataFrame:
    """Year-on-year change in each capital from both geographies. They use different boundaries,
    so the levels differ, but if both are coded consistently the direction and size should agree.

    `ivi_c` is compare() on region_wide(level=1); `sa4_c` is yoy_only() on sa4_wide(level=1);
    `states` maps GCCSA name -> state."""
    g = sa4_c.loc["GCCSA"]
    rows = []
    for name, st in states.items():
        cap = CAPITALS[st]
        rows.append({"state": st, "ivi_region": cap, "gccsa": name,
                     "ivi_now": ivi_c.loc[cap, "now"], "gccsa_now": g.loc[name, "now"],
                     "ivi_yoy": ivi_c.loc[cap, "yoy"], "gccsa_yoy": g.loc[name, "yoy"]})
    out = pd.DataFrame(rows).set_index("state")
    out["gap_points"] = (out["gccsa_yoy"] - out["ivi_yoy"]) * 100
    return out


def region_leaders(rg: pd.DataFrame, lq: pd.Series, titles: pd.Series, min_now: float = 100.0) -> pd.DataFrame:
    """Per region: the largest 2-digit group, the fastest riser on the year (base above the
    floor) and the most over-represented group with at least `min_now` ads a month.

    `rg` is compare() on region_wide(level=3), indexed (region, anzsco_code)."""
    rows = []
    for region, g in rg.groupby(level=0, sort=False):
        big = g["now"].idxmax()[1]
        up = D.ranked(g, "yoy", 1)
        l = lq.loc[region].loc[g.loc[region].index]
        l = l[g.loc[region, "now"] >= min_now]
        rows.append({
            "region": region,
            "largest": titles[big], "largest_now": g.loc[(region, big), "now"],
            "riser": titles[up.index[0][1]] if len(up) else None,
            "riser_prev": up["prev"].iloc[0] if len(up) else None,
            "riser_now": up["now"].iloc[0] if len(up) else None,
            "riser_yoy": up["yoy"].iloc[0] if len(up) else None,
            "special": titles[l.idxmax()] if len(l) else None,
            "special_lq": l.max() if len(l) else None,
        })
    return pd.DataFrame(rows).set_index("region")
