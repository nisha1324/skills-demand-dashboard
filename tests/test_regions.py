"""Part 3 measures on small hand-made frames, with the answers worked by hand."""
import numpy as np
import pandas as pd
import pytest

from ivi import demand as D
from ivi import regions as R


def months(start, n):
    return [D.shift_month(start, i) for i in range(n)]


def ivi_rows(region, state, level, code, values, start):
    return [{"month": m, "state": state, "region": region, "level": level, "anzsco_code": code,
             "anzsco_title": code, "ads_3ma": v} for m, v in zip(months(start, len(values)), values)]


def test_capitals_are_one_per_state():
    assert sorted(R.CAPITALS) == sorted(["NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"])
    a = R.area_of(pd.Series(["Sydney", "Dubbo & Western NSW", "Hobart & Southeast Tasmania", "Gold Coast"]))
    assert list(a) == ["capital", "regional", "capital", "regional"]


def test_region_wide_starts_in_october_2010():
    r = pd.DataFrame(ivi_rows("Sydney", "NSW", 1, "0", [1.0] * 8, "2010-05"))
    w = R.region_wide(r)
    assert list(w.columns) == months("2010-10", 3)


def test_area_wide_sums_capitals_and_the_rest():
    rows = (ivi_rows("Sydney", "NSW", 2, "1", [10, 20], "2011-01")
            + ivi_rows("Melbourne", "VIC", 2, "1", [5, 5], "2011-01")
            + ivi_rows("Gold Coast", "QLD", 2, "1", [3, 4], "2011-01")
            + ivi_rows("Gold Coast", "QLD", 2, "2", [1, 1], "2011-01"))
    w = R.area_wide(pd.DataFrame(rows), level=2)
    assert w.loc[("capital", "1")].tolist() == [15, 25]
    assert w.loc[("regional", "1")].tolist() == [3, 4]
    assert w.loc[("regional", "2")].tolist() == [1, 1]
    assert ("capital", "2") not in w.index


def test_regional_share_uses_rolling_years():
    cols = months("2011-01", 14)
    # capital flat at 300; regional 100 except a seasonal bump of +120 every January
    reg = [220 if c.endswith("-01") else 100 for c in cols]
    area = pd.DataFrame([[300] * 14, reg], index=["capital", "regional"], columns=cols)
    s = R.regional_share(area)
    assert list(s.index) == cols[11:]
    # 12 months ending Dec 2011: regional 110 (one bump), capital 300 -> 110 / 410
    assert s.iloc[0] == pytest.approx(110 / 410)
    # ending Jan 2012: still one January in the window -> unchanged; the swing has cancelled
    assert s.iloc[1] == pytest.approx(110 / 410)


def test_share_bounds():
    c = pd.DataFrame({"y2019": [80.0, 20.0], "now": [70.0, 30.0]}, index=["capital", "regional"])
    nat = pd.Series({"y2019": 100.0, "now": 105.0})
    b = R.share_bounds(c, nat)
    assert b.loc["2019", "share_of_placed"] == pytest.approx(0.2)
    assert b.loc["2019", "unplaced"] == pytest.approx(0.0)
    assert b.loc["now", "share_of_placed"] == pytest.approx(0.3)
    assert b.loc["now", "unplaced"] == pytest.approx(5.0)
    assert b.loc["now", "share_lower_bound"] == pytest.approx(30 / 105)


def test_location_quotient_worked_example():
    # A: x 30, y 10 (40 ads); B: x 10, y 50 (60 ads); all regions: x 40 of 100 = 0.4
    cells = pd.Series([30.0, 10.0, 10.0, 50.0],
                      index=pd.MultiIndex.from_tuples([("A", "x"), ("A", "y"), ("B", "x"), ("B", "y")]))
    lq = R.location_quotient(cells)
    assert lq[("A", "x")] == pytest.approx((30 / 40) / 0.4)   # 1.875
    assert lq[("A", "y")] == pytest.approx((10 / 40) / 0.6)
    assert lq[("B", "x")] == pytest.approx((10 / 60) / 0.4)
    assert lq[("B", "y")] == pytest.approx((50 / 60) / 0.6)
    # weighted by each region's share of all ads, the mean LQ is exactly 1 for every group
    w = cells.groupby(level=0).transform("sum") / cells.sum()
    assert (lq * w).groupby(level=1).sum().tolist() == pytest.approx([1.0, 1.0])


def wide_2019_to(end, rows):
    cols = months("2019-01", (pd.Period(end, "M") - pd.Period("2019-01", "M")).n + 1)
    return pd.DataFrame({k: [v] * len(cols) for k, v in rows.items()}, index=cols).T


def test_yoy_only_has_no_2019_columns():
    w = wide_2019_to("2026-08", {"a": 50.0})
    c = R.yoy_only(w, "2026-08")
    assert "vs_2019" not in c.columns and "y2019" not in c.columns
    assert c.loc["a", "yoy"] == pytest.approx(0.0)


def test_capital_crosscheck_gap_in_points():
    ivi = pd.DataFrame({"now": [100.0], "yoy": [-0.05]}, index=["Sydney"])
    sa4 = pd.DataFrame({"now": [110.0], "yoy": [-0.04]},
                       index=pd.MultiIndex.from_tuples([("GCCSA", "Greater Sydney")]))
    x = R.capital_crosscheck(ivi, sa4, pd.Series({"Greater Sydney": "NSW"}))
    assert x.loc["NSW", "ivi_region"] == "Sydney"
    assert x.loc["NSW", "gap_points"] == pytest.approx(1.0)


def test_region_leaders_respect_the_floor_and_size():
    idx = pd.MultiIndex.from_tuples([("A", "x"), ("A", "y"), ("A", "z")])
    rg = pd.DataFrame({"now": [500.0, 150.0, 40.0], "prev": [490.0, 100.0, 10.0]}, index=idx)
    rg["yoy"] = (rg["now"] / rg["prev"] - 1).where(rg["prev"] > D.FLOOR)
    lq = pd.Series([0.9, 1.5, 4.0], index=idx)
    titles = pd.Series({"x": "X", "y": "Y", "z": "Z"})
    L = R.region_leaders(rg, lq, titles, min_now=100)
    a = L.loc["A"]
    assert a["largest"] == "X"
    # z rose 300% but from a base of 10 ads: under the floor, so y (+50%) leads
    assert a["riser"] == "Y" and a["riser_yoy"] == pytest.approx(0.5)
    # z is the most over-represented but has under 100 ads a month, so y
    assert a["special"] == "Y" and a["special_lq"] == pytest.approx(1.5)


def test_region_leaders_when_nothing_is_rated():
    idx = pd.MultiIndex.from_tuples([("A", "x")])
    rg = pd.DataFrame({"now": [30.0], "prev": [10.0], "yoy": [np.nan]}, index=idx)
    L = R.region_leaders(rg, pd.Series([1.0], index=idx), pd.Series({"x": "X"}))
    assert L.loc["A", "riser"] is None and L.loc["A", "special"] is None
