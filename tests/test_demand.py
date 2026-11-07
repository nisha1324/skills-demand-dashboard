"""Part 2 measures on small hand-made frames, where the right answer is known."""
import numpy as np
import pandas as pd
import pytest

from ivi import demand as D


def months(start, n):
    return [(pd.Period(start, "M") + i).strftime("%Y-%m") for i in range(n)]


MS = months("2019-01", 92)  # Jan 2019 to Aug 2026


def wide(rows):
    """rows: {name: function(month) -> value} -> (series x month) frame."""
    return pd.DataFrame({m: {k: f(m) for k, f in rows.items()} for m in MS})


def occ_frame(rows):
    """rows: (month, state, level, code, title, suppressed, ads_3ma)"""
    return pd.DataFrame(rows, columns=["month", "state", "level", "anzsco_code", "anzsco_title",
                                       "suppressed", "ads_3ma"])


def test_window_is_the_12_months_ending_at_end():
    w = D.window("2026-08")
    assert w[0] == "2025-09" and w[-1] == "2026-08" and len(w) == 12


def test_compare_uses_12_month_averages_2019_and_the_same_month():
    def f(m):
        if m.startswith("2019"):
            return 50.0
        if m > "2025-08":
            return 120.0
        if m > "2024-08":
            return 100.0
        return 70.0
    w = wide({"a": f})
    w.loc["a", "2025-08"] = 80.0  # only moves the year-before average and the same-month base
    c = D.compare(w, "2026-08").loc["a"]
    assert c["now"] == 120.0
    assert c["prev"] == pytest.approx((11 * 100 + 80) / 12)
    assert c["yoy"] == pytest.approx(120 / ((11 * 100 + 80) / 12) - 1)
    assert c["vs_2019"] == pytest.approx(120 / 50 - 1)
    assert c["latest_yoy"] == pytest.approx(120 / 80 - 1)
    assert c["change"] == pytest.approx(c["now"] - c["prev"])


def test_compare_floor_is_strictly_above_20():
    w = wide({"at": lambda m: 20.0 if m <= "2025-08" else 40.0,
              "above": lambda m: 20.5 if m <= "2025-08" else 41.0})
    c = D.compare(w, "2026-08")
    assert np.isnan(c.loc["at", "yoy"]) and np.isnan(c.loc["at", "vs_2019"])
    assert np.isnan(c.loc["at", "latest_yoy"])
    assert c.loc["above", "yoy"] == pytest.approx(1.0)
    # the change in ads is still shown for a small base
    assert c.loc["at", "change"] == pytest.approx(20.0)


def test_compare_refuses_a_short_history():
    w = wide({"a": lambda m: 1.0}).drop(columns=["2025-01"])
    with pytest.raises(ValueError, match="missing"):
        D.compare(w, "2026-08")


def test_turning_needs_opposite_signs():
    c = pd.DataFrame({"yoy": [-0.1, 0.1, 0.1, 0.0, np.nan],
                      "latest_yoy": [0.05, 0.2, -0.01, 0.3, 0.3]})
    assert D.turning(c).tolist() == [True, False, True, False, False]


def test_major_groups_sum_published_occupations_by_first_digit():
    rows = []
    for m in ["2026-08"]:
        rows += [(m, "AUST", "total", "0", "Total", False, 1000.0),
                 (m, "AUST", "occupation", "2544", "Registered Nurses", False, 300.0),
                 (m, "AUST", "occupation", "2613", "Programmers", False, 200.0),
                 (m, "AUST", "occupation", "", "Judicial", True, np.nan),
                 (m, "AUST", "occupation", "3411", "Electricians", False, 100.0),
                 (m, "NSW", "occupation", "2544", "Registered Nurses", False, 120.0),
                 (m, "VIC", "occupation", "2544", "Registered Nurses", False, 90.0),
                 (m, "VIC", "occupation", "3411", "Electricians", False, 40.0)]
    occ = occ_frame(rows)
    g = D.major_group_wide(occ)
    assert g.loc["2", "2026-08"] == 500.0 and g.loc["3", "2026-08"] == 100.0
    assert set(g.index) == {"2", "3"}  # no total, no suppressed row
    s = D.major_group_wide(occ, state=None)
    assert s.loc[("VIC", "2"), "2026-08"] == 90.0 and ("AUST", "2") not in s.index
    assert D.national_wide(occ).loc["2544", "2026-08"] == 300.0


def test_contributions_are_sorted_and_share_the_net_change():
    c = pd.DataFrame({"prev": [10.0, 50.0, 30.0], "now": [20.0, 20.0, 30.0]}, index=["a", "b", "c"])
    c["change"] = c["now"] - c["prev"]
    d = D.contributions(c, total_change=-20.0)
    assert list(d.index) == ["b", "c", "a"]
    assert d.loc["b", "share_of_net"] == pytest.approx(1.5)
    assert d.loc["a", "share_of_net"] == pytest.approx(-0.5)


def test_quadrant_needs_size_and_both_rates():
    c = pd.DataFrame({
        "now": [600, 600, 600, 600, 600, 499, 600],
        "yoy": [0.1, -0.1, 0.1, -0.1, 0.0, 0.5, np.nan],
        "vs_2019": [0.2, 0.2, -0.2, -0.2, 0.3, 0.5, 0.1],
    }, index=list("abcdefg"))
    q = D.quadrant(c, 500)
    assert list(q.index) == list("abcde")  # f too small, g has no year-on-year rate
    assert q["quadrant"].tolist() == ["Growing, above 2019", "Cooling, still above 2019",
                                      "Rising, still below 2019", "Shrinking, below 2019",
                                      "Cooling, still above 2019"]  # exactly 0 is not growing


def test_ranked_leaves_out_rows_without_a_rate():
    c = pd.DataFrame({"now": [5, 50, 60, 70], "yoy": [np.nan, 0.3, -0.2, 0.3]}, index=list("abcd"))
    assert list(D.ranked(c, "yoy", 2).index) == ["d", "b"]  # ties: bigger first
    assert list(D.ranked(c, "yoy", 1, ascending=True).index) == ["c"]
    # asking for more than there are: unrated rows must not fill the list
    assert list(D.ranked(c, "yoy", 10).index) == ["d", "b", "c"]


def test_state_leaders_apply_the_floor_to_risers_only():
    idx = pd.MultiIndex.from_tuples([("NSW", "1111"), ("NSW", "2222"), ("NSW", "3333")],
                                    names=["state", "anzsco_code"])
    c = pd.DataFrame({"now": [900.0, 12.0, 30.0], "prev": [1000.0, 2.0, 25.0],
                      "yoy": [-0.1, np.nan, 0.2]}, index=idx)
    L = D.state_leaders(c, k=2)
    big = L[L["list"] == "largest"]["anzsco_code"].tolist()
    up = L[L["list"] == "fastest rising"]["anzsco_code"].tolist()
    assert big == ["1111", "3333"]
    assert up == ["3333", "1111"]  # 2222 rose 6x from 2 ads but has no rate


def test_skill_levels_use_the_seasonally_adjusted_series_only():
    rows = []
    for m in MS:
        for series, v in [("seasonally_adjusted", 100.0), ("trend", 999.0)]:
            rows.append((series, m, "AUST", 1, v if m > "2025-08" or series == "trend" else 80.0))
    sk = pd.DataFrame(rows, columns=["series", "month", "state", "skill_level", "ads"])
    c = D.skill_level_compare(sk, "2026-08").loc[1]
    assert c["now"] == 100.0 and c["yoy"] == pytest.approx(0.25)
    assert c["vs_2019"] == pytest.approx(0.25)
