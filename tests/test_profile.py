"""The profile checks on small hand-made frames, where the right answer is known."""
import numpy as np
import pandas as pd
import pytest

from ivi import profile as P


def months(start, n):
    return [(pd.Period(start, "M") + i).strftime("%Y-%m") for i in range(n)]


def occ_frame(rows):
    """rows: (month, state, level, code, title, suppressed, ads_3ma)"""
    return pd.DataFrame(rows, columns=["month", "state", "level", "anzsco_code", "anzsco_title",
                                       "suppressed", "ads_3ma"])


def skill_frame(rows):
    """rows: (series, month, state, skill_level, ads)"""
    return pd.DataFrame(rows, columns=["series", "month", "state", "skill_level", "ads"])


def test_shift_month_crosses_years():
    assert P.shift_month("2026-01", -1) == "2025-12"
    assert P.shift_month("2026-08", -12) == "2025-08"


def test_headline_compares_like_with_like():
    ms = months("2019-01", 92)  # Jan 2019 to Aug 2026
    occ = occ_frame([(m, "AUST", "total", "0", "Australia Total", False, 100.0) for m in ms])
    # last 12 months at 120, the 12 before at 150, 2019 at 100
    occ.loc[occ["month"] > "2025-08", "ads_3ma"] = 120.0
    occ.loc[(occ["month"] > "2024-08") & (occ["month"] <= "2025-08"), "ads_3ma"] = 150.0
    sa = [("seasonally_adjusted", m, "AUST", 0, 200.0) for m in ms]
    sa[-1] = ("seasonally_adjusted", ms[-1], "AUST", 0, 210.0)
    sa[10] = ("seasonally_adjusted", ms[10], "AUST", 0, 400.0)  # the peak, Nov 2019
    tr = [("trend", m, "AUST", 0, 205.0) for m in ms]
    h = P.headline(occ, skill_frame(sa + tr))
    assert h["month"] == "2026-08" and h["prev_month"] == "2026-07"
    assert h["sa_change"] == 10.0
    assert h["last12_vs_prev12"] == pytest.approx(120 / 150 - 1)
    assert h["last12_vs_2019"] == pytest.approx(0.2)
    assert h["sa_peak_month"] == "2019-11"
    assert h["sa_vs_peak"] == pytest.approx(210 / 400 - 1)
    # 2019 average of SA includes the peak month
    assert h["sa_vs_2019"] == pytest.approx(210 / ((11 * 200 + 400) / 12) - 1)


def test_headline_refuses_files_that_end_in_different_months():
    ms = months("2024-01", 32)
    occ = occ_frame([(m, "AUST", "total", "0", "t", False, 1.0) for m in ms])
    sk = skill_frame([(s, m, "AUST", 0, 1.0) for s in ["seasonally_adjusted", "trend"] for m in ms[:-1]])
    with pytest.raises(ValueError, match="different months"):
        P.headline(occ, sk)


def test_seasonal_ratio_isolates_the_calendar():
    ms = months("2010-01", 24)
    # SA flat at 100; raw is 90 in Jan and 110 in Oct, 100 otherwise (3-month averages already)
    raw = {1: 90.0, 10: 110.0}
    occ = occ_frame([(m, "AUST", "total", "0", "t", False, raw.get(int(m[5:]), 100.0)) for m in ms])
    sk = skill_frame([("seasonally_adjusted", m, "AUST", 0, 100.0) for m in ms])
    sr = P.seasonal_ratio(occ, sk, start="2010-01", end="2011-12")
    by = sr.set_index("cal_month")["ratio_mean"]
    assert by[1] == pytest.approx(0.9) and by[10] == pytest.approx(1.1) and by[6] == pytest.approx(1.0)
    # the first two months have no 3-month SA average yet
    assert sr.set_index("cal_month").loc[1, "years"] == 1


def test_seasonal_ratio_only_uses_the_chosen_years():
    ms = months("2009-01", 36)  # 2009 to 2011
    # Jan is 90 inside 2010, but 50 in 2009 and 2011, which must be left out
    occ = occ_frame([(m, "AUST", "total", "0", "t", False,
                      (90.0 if m[:4] == "2010" else 50.0) if m[5:] == "01" else 100.0) for m in ms])
    sk = skill_frame([("seasonally_adjusted", m, "AUST", 0, 100.0) for m in ms])
    sr = P.seasonal_ratio(occ, sk, start="2010-01", end="2010-12").set_index("cal_month")
    assert sr.loc[1, "ratio_mean"] == pytest.approx(0.9) and sr.loc[1, "years"] == 1


def test_additivity_reports_the_gap_on_each_series():
    m = "2026-08"
    sk = skill_frame([
        ("seasonally_adjusted", m, "AUST", 0, 100.0), ("seasonally_adjusted", m, "AUST", 1, 60.0),
        ("seasonally_adjusted", m, "AUST", 2, 45.0), ("seasonally_adjusted", m, "NSW", 0, 70.0),
        ("seasonally_adjusted", m, "VIC", 0, 29.0),
        ("trend", m, "AUST", 0, 100.0), ("trend", m, "AUST", 1, 100.0), ("trend", m, "NSW", 0, 100.0),
    ])
    occ = occ_frame([
        (m, "AUST", "total", "0", "t", False, 100.0), (m, "NSW", "total", "0", "t", False, 60.0),
        (m, "VIC", "total", "0", "t", False, 40.0),
        (m, "AUST", "occupation", "1111", "a", False, 90.0), (m, "AUST", "occupation", "", "b", True, np.nan),
    ])
    a = P.additivity(sk, occ, m).set_index(["series", "check"])["gap"]
    assert a[("seasonally_adjusted", "5 skill levels vs Australia total")] == 5.0
    assert a[("seasonally_adjusted", "8 states vs Australia total")] == -1.0
    assert a[("trend", "8 states vs Australia total")] == 0.0
    assert a[("3-month average", "8 states vs Australia total")] == 0.0
    assert a[("3-month average", "published 4-digit occupations vs Australia total")] == -10.0


def test_suppressed_share_is_total_less_published():
    occ = occ_frame([
        ("2025-01", "AUST", "total", "0", "t", False, 100.0),
        ("2025-01", "AUST", "occupation", "1111", "a", False, 98.0),
        ("2025-01", "AUST", "occupation", "", "Legislators", True, np.nan),
        ("2026-01", "AUST", "total", "0", "t", False, 200.0),
        ("2026-01", "AUST", "occupation", "1111", "a", False, 190.0),
        ("2026-01", "AUST", "occupation", "", "Legislators", True, np.nan),
        ("2026-01", "NSW", "occupation", "1111", "a", False, 999.0),  # states are ignored
    ])
    s = P.suppressed(occ).set_index("year")["unpublished_share"]
    assert s["2025"] == pytest.approx(0.02) and s["2026"] == pytest.approx(0.05)
    assert P.suppressed(occ).attrs["titles"] == ["Legislators"]


def test_regional_coverage_uses_level_1_only():
    occ = occ_frame([("2026-08", "AUST", "total", "0", "t", False, 200.0),
                     ("2026-08", "NSW", "total", "0", "t", False, 120.0),
                     ("2026-08", "VIC", "total", "0", "t", False, 80.0)])
    reg = pd.DataFrame({
        "month": ["2026-08"] * 4, "state": ["NSW", "NSW", "VIC", "VIC"],
        "level": [1, 2, 1, 2], "ads_3ma": [108.0, 50.0, 86.0, 999.0],
    })
    assert P.regional_coverage(occ, reg)["2026-08"] == pytest.approx(194 / 200)
    by_state = P.regional_coverage_by_state(occ, reg, "2026-08")
    assert by_state["NSW"] == pytest.approx(0.9) and by_state["VIC"] == pytest.approx(86 / 80)
    assert np.isnan(by_state["TAS"])


def test_noise_by_base_bins_on_the_base_month_and_drops_zero_bases():
    w = pd.DataFrame({
        "2025-08": [0.0, 3.0, 4.0, 30.0, 200.0, 200.0],
        "2026-08": [5.0, 6.0, 4.0, 31.0, 90.0, 210.0],
    })
    nb = P.noise_by_base(w, "2025-08", "2026-08").set_index("bin")
    assert nb.loc["over 0 to 5", "cells"] == 2  # the zero base is left out
    assert nb.loc["over 0 to 5", "share_big_swing"] == 0.5  # 3 -> 6 is +100%, 4 -> 4 is 0
    assert nb.loc["over 20 to 50", "share_big_swing"] == 0.0
    assert nb.loc["over 100", "share_big_swing"] == 0.5  # 200 -> 90 is -55%
    assert nb.loc["over 5 to 10", "cells"] == 0


def test_cell_sizes_put_exact_bin_edges_in_the_lower_bin():
    w = pd.DataFrame({"2026-08": [0.0, 5.0, 5.00001, 20.0, 150.0, np.nan]})
    s = P.cell_sizes(w, "2026-08").set_index("ads_3ma")["cells"]
    assert s["0"] == 1 and s["over 0 to 5"] == 1 and s["over 5 to 10"] == 1
    assert s["over 10 to 20"] == 1 and s["over 100"] == 1 and s.sum() == 5
