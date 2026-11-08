"""Part 4: the data behind the Streamlit dashboard, as small testable functions.

The dashboard reads the tables that Parts 2 and 3 wrote to `results/` (so every number on screen
is one a report already cites), plus the committed snapshot for the monthly series. It keeps the
Part 1 rules:
- change is shown on 12-month averages (vs the year before and vs 2019) or the latest 3 months
  vs the same months a year earlier, never month on month;
- no growth rate on a base of FLOOR ads a month or fewer (those cells are blank in the CSVs, and
  rate sorts leave them out rather than ranking them);
- regions are compared with regions; the GCCSA/SA4 areas have no 2019 comparison;
- job ads are a demand signal, not a count of jobs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ivi import demand as D

RESULTS = Path(__file__).resolve().parents[1] / "results"

STATE_NAMES = {
    "AUST": "Australia",
    "NSW": "New South Wales",
    "VIC": "Victoria",
    "QLD": "Queensland",
    "SA": "South Australia",
    "WA": "Western Australia",
    "TAS": "Tasmania",
    "NT": "Northern Territory",
    "ACT": "Australian Capital Territory",
}
STATES = list(STATE_NAMES)  # Australia first, then the usual state order

# label -> (column, ascending). Rate columns drop rows without a rate (base at or under the floor).
SORTS = {
    "Most ads": ("now", False),
    "Fastest rising on the year": ("yoy", False),
    "Fastest falling on the year": ("yoy", True),
    "Most ads gained": ("change", False),
    "Most ads lost": ("change", True),
    "Furthest above 2019": ("vs_2019", False),
    "Furthest below 2019": ("vs_2019", True),
}
RATE_COLS = {"yoy", "vs_2019", "latest_yoy"}
NOT_RATED = "Not rated (small base)"
RAW, AVG = "3-month average", "12-month average"  # series names in monthly()

_CODE_COLS = {"anzsco_code": str, "major": str}


def load_results(results: Path = RESULTS) -> dict[str, pd.DataFrame]:
    """The Part 2 and Part 3 CSVs the dashboard needs, with codes kept as text ("1A", "0111")."""
    names = ["occupation_national", "occupation_state", "major_group_state", "ivi_regions",
             "region_group", "sa4_areas", "regional_share"]
    return {n: pd.read_csv(results / f"{n}.csv", dtype=_CODE_COLS) for n in names}


def demand_state(yoy: pd.Series, vs_2019: pd.Series) -> pd.Series:
    """The Part 2 demand matrix label for each row; rows missing either rate aren't rated."""
    out = pd.Series(NOT_RATED, index=yoy.index, dtype=object)
    both = yoy.notna() & vs_2019.notna()
    for (up, above), label in D.QUADRANTS.items():
        out[both & ((yoy > 0) == up) & ((vs_2019 > 0) == above)] = label
    return out


def sort_rows(d: pd.DataFrame, sort: str) -> pd.DataFrame:
    col, asc = SORTS[sort]
    if col in RATE_COLS:
        d = d[d[col].notna()]
    return d.sort_values([col, "now"], ascending=[asc, False], kind="mergesort")


def occupations(t: dict[str, pd.DataFrame], state: str = "AUST", major: str | None = None,
                sort: str = "Most ads", min_now: float = 0.0, search: str = "") -> pd.DataFrame:
    """4-digit occupations for Australia or one state, filtered and sorted for the table."""
    if state == "AUST":
        d = t["occupation_national"].copy()
    else:
        d = t["occupation_state"][t["occupation_state"]["state"] == state].copy()
    if major:
        d = d[d["anzsco_code"].str[0] == major]
    if min_now:
        d = d[d["now"] >= min_now]
    if search:
        d = d[d["anzsco_title"].str.contains(search, case=False, regex=False)]
    d["demand_state"] = demand_state(d["yoy"], d["vs_2019"])
    return sort_rows(d, sort).reset_index(drop=True)


def major_groups(t: dict[str, pd.DataFrame], occ_national: pd.DataFrame | None = None,
                 state: str = "AUST") -> pd.DataFrame:
    """The 8 major groups for one state (from major_group_state.csv), or for Australia (summed
    from the published 4-digit occupations, as Part 2 does)."""
    if state != "AUST":
        d = t["major_group_state"][t["major_group_state"]["state"] == state].copy()
    else:
        n = t["occupation_national"].assign(major=lambda x: x["anzsco_code"].str[0])
        sums = n.groupby("major")[["now", "prev", "y2019", "latest", "year_ago", "change"]].sum()
        d = sums.reset_index()
        d["yoy"] = d["now"] / d["prev"] - 1
        d["vs_2019"] = d["now"] / d["y2019"] - 1
        d["latest_yoy"] = d["latest"] / d["year_ago"] - 1
    d["name"] = d["major"].map(D.MAJOR_GROUPS)
    return d.sort_values("major").reset_index(drop=True)


def headline(totals: pd.DataFrame, state: str = "AUST") -> pd.Series:
    """KPI tiles for one state: compare() on the published total (which includes the
    suppressed occupations), so the national figure matches Parts 1 and 2."""
    end = totals.columns.max()
    return D.compare(totals.loc[[state]], end).iloc[0]


def monthly(wide_row: pd.Series, start: str | None = None) -> pd.DataFrame:
    """One series' raw 3-month averages with its 12-month rolling average (which removes the
    seasonal swing), as a long frame for charting."""
    s = wide_row.dropna().sort_index()
    out = pd.DataFrame({"month": pd.PeriodIndex(s.index, freq="M").to_timestamp(),
                        RAW: s.values,
                        AVG: s.rolling(12).mean().values})
    if start:
        out = out[out["month"] >= pd.Timestamp(start)]
    return out.melt("month", var_name="series", value_name="ads").dropna()


def regions(t: dict[str, pd.DataFrame], area: str | None = None, state: str | None = None,
            sort: str = "Furthest above 2019") -> pd.DataFrame:
    """The 37 IVI regions, filtered by capital/regional and state."""
    d = t["ivi_regions"].copy()
    if area:
        d = d[d["area"] == area]
    if state and state != "AUST":
        d = d[d["state"] == state]
    return sort_rows(d, sort).reset_index(drop=True)


def region_groups(t: dict[str, pd.DataFrame], region: str, sort: str = "Most ads",
                  floor: float = D.FLOOR) -> pd.DataFrame:
    """The 48 two-digit occupation groups in one region, with the location quotient (how much
    more common the group is there than across all regions). The LQ is blanked where the group
    has FLOOR ads a month or fewer, for the same reason growth rates are: tiny cells swing."""
    d = t["region_group"][t["region_group"]["region"] == region].copy()
    d["lq"] = d["lq"].where(d["now"] > floor)
    if sort == "Most over-represented":
        d = d[d["lq"].notna()].sort_values(["lq", "now"], ascending=[False, False], kind="mergesort")
    else:
        d = sort_rows(d, sort)
    return d.reset_index(drop=True)


def area_summary(t: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Capital-city regions vs regional areas: ads a month now, the year before and in 2019."""
    s = t["ivi_regions"].groupby("area")[["now", "prev", "y2019", "change"]].sum()
    s["yoy"] = s["now"] / s["prev"] - 1
    s["vs_2019"] = s["now"] / s["y2019"] - 1
    s["share"] = s["now"] / s["now"].sum()
    s["share_2019"] = s["y2019"] / s["y2019"].sum()
    return s


def sa4(t: dict[str, pd.DataFrame], state: str | None = None, level: str | None = None,
        sort: str = "Fastest rising on the year") -> pd.DataFrame:
    """GCCSA (greater capital) and SA4 (rest of state) areas, year on year only."""
    d = t["sa4_areas"].copy()
    if state and state != "AUST":
        d = d[d["state"] == state]
    if level:
        d = d[d["region_level"] == level]
    if SORTS[sort][0] == "vs_2019":
        raise ValueError("the GCCSA/SA4 file has no 2019 comparison (its 2019 is backcast)")
    return sort_rows(d, sort).reset_index(drop=True)


def pct(x: float, digits: int = 1) -> str:
    """+4.8% / −3.3% with a real minus sign; a dash when there is no rate."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    return f"{x * 100:+.{digits}f}%".replace("-", "−")
