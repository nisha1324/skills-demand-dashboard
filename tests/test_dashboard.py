"""Part 4 data layer: hand-made frames with worked answers, then checks that the dashboard's
figures on the real data are the ones the Part 2 and Part 3 reports print."""
import numpy as np
import pandas as pd
import pytest

from ivi import dashboard as B
from ivi import demand as D
from ivi.load import load_occupation_state

NAN = np.nan


def occ_rows(rows):
    cols = ["anzsco_code", "anzsco_title", "now", "prev", "y2019", "latest", "year_ago", "yoy",
            "vs_2019", "latest_yoy", "change"]
    return pd.DataFrame(rows, columns=cols)


@pytest.fixture
def tiny():
    nat = occ_rows([
        ["2544", "Registered Nurses", 600.0, 500.0, 400.0, 610, 590, 0.2, 0.5, 0.0339, 100.0],
        ["2611", "ICT Analysts", 300.0, 400.0, 500.0, 290, 380, -0.25, -0.4, -0.2368, -100.0],
        ["7331", "Truck Drivers", 450.0, 400.0, 500.0, 460, 420, 0.125, -0.1, 0.0952, 50.0],
        ["1211", "Aquaculture Farmers", 6.0, 3.0, 2.0, 6, 3, NAN, NAN, NAN, 3.0],
        ["5311", "General Clerks", 800.0, 900.0, 700.0, 790, 910, -0.1111, 0.1429, -0.1319, -100.0],
    ])
    st = nat.assign(state="QLD")
    st.loc[0, "state"] = "NSW"
    return {"occupation_national": nat, "occupation_state": st}


def test_demand_state_quadrants_and_unrated(tiny):
    d = tiny["occupation_national"]
    got = list(B.demand_state(d["yoy"], d["vs_2019"]))
    assert got == ["Growing, above 2019", "Shrinking, below 2019", "Rising, still below 2019",
                   B.NOT_RATED, "Cooling, still above 2019"]


def test_zero_change_is_not_growth():
    s = B.demand_state(pd.Series([0.0]), pd.Series([0.0]))
    assert s.iloc[0] == "Shrinking, below 2019"


def test_most_ads_keeps_unrated_rows(tiny):
    d = B.occupations(tiny, sort="Most ads")
    assert list(d["anzsco_code"]) == ["5311", "2544", "7331", "2611", "1211"]


def test_rate_sorts_leave_out_small_bases(tiny):
    up = B.occupations(tiny, sort="Fastest rising on the year")
    assert list(up["anzsco_code"]) == ["2544", "7331", "5311", "2611"]
    down = B.occupations(tiny, sort="Fastest falling on the year")
    assert list(down["anzsco_code"]) == ["2611", "5311", "7331", "2544"]
    v19 = B.occupations(tiny, sort="Furthest below 2019")
    assert list(v19["anzsco_code"]) == ["2611", "7331", "5311", "2544"]


def test_change_sort_ties_broken_by_size(tiny):
    lost = B.occupations(tiny, sort="Most ads lost")
    # 2611 and 5311 both lost 100 ads a month; the bigger one (5311) comes first
    assert list(lost["anzsco_code"][:2]) == ["5311", "2611"]


def test_filters(tiny):
    assert list(B.occupations(tiny, major="2")["anzsco_code"]) == ["2544", "2611"]
    assert list(B.occupations(tiny, min_now=450)["anzsco_code"]) == ["5311", "2544", "7331"]
    assert list(B.occupations(tiny, search="NURSE")["anzsco_code"]) == ["2544"]
    assert list(B.occupations(tiny, search="(")["anzsco_code"]) == []  # plain text, not a regex
    qld = B.occupations(tiny, state="QLD")
    assert "2544" not in set(qld["anzsco_code"]) and len(qld) == 4
    assert list(B.occupations(tiny, state="NSW")["anzsco_code"]) == ["2544"]


def test_national_major_groups_sum_occupations(tiny):
    mg = B.major_groups(tiny).set_index("major")
    # group 2 = nurses + ICT analysts: now 900, prev 900, 2019 900
    assert mg.loc["2", "now"] == 900 and mg.loc["2", "yoy"] == 0 and mg.loc["2", "vs_2019"] == 0
    assert mg.loc["2", "name"] == "Professionals"
    # group 1 is aquaculture only (a tiny base); the rate is still computed at group level
    assert mg.loc["1", "yoy"] == pytest.approx(1.0)


def test_monthly_rolling_average():
    months = [D.shift_month("2024-01", i) for i in range(14)]
    row = pd.Series([12.0] * 12 + [24.0, 24.0], index=months)
    m = B.monthly(row)
    avg = m[m["series"] == B.AVG].set_index("month")["ads"]
    assert len(avg) == 3  # first full year ends in month 12
    assert list(avg.round(4)) == [12.0, 13.0, 14.0]
    assert len(m[m["series"] == B.RAW]) == 14
    late = B.monthly(row, start="2025-01")
    assert late["month"].min() == pd.Timestamp("2025-01-01")


def test_headline_uses_published_total():
    months = [D.shift_month("2018-09", i) for i in range(96)]
    totals = pd.DataFrame([[100.0] * 96, [10.0] * 96], index=["AUST", "ACT"], columns=months)
    totals.loc["AUST", months[-12:]] = 150.0
    h = B.headline(totals, "AUST")
    assert h["now"] == 150 and h["prev"] == 100 and h["yoy"] == pytest.approx(0.5)
    assert B.headline(totals, "ACT")["now"] == 10


@pytest.fixture
def regions_tiny():
    reg = pd.DataFrame({
        "region": ["Sydney", "Dubbo", "Perth", "Pilbara"],
        "state": ["NSW", "NSW", "WA", "WA"],
        "area": ["capital", "regional", "capital", "regional"],
        "now": [900.0, 100.0, 450.0, 50.0], "prev": [1000.0, 80.0, 400.0, 50.0],
        "y2019": [1000.0, 50.0, 300.0, 40.0], "change": [-100.0, 20.0, 50.0, 0.0],
        "yoy": [-0.1, 0.25, 0.125, 0.0], "vs_2019": [-0.1, 1.0, 0.5, 0.25],
        "latest_yoy": [0.0, 0.0, 0.0, 0.0]})
    rg = pd.DataFrame({
        "region": ["Dubbo"] * 3, "state": ["NSW"] * 3, "anzsco_code": ["25", "73", "11"],
        "group_title": ["Nurses", "Drivers", "CEOs"], "now": [60.0, 25.0, 15.0],
        "prev": [40.0, 25.0, 15.0], "change": [20.0, 0.0, 0.0], "yoy": [0.5, 0.0, NAN],
        "vs_2019": [1.0, NAN, NAN], "lq": [2.0, 1.1, 3.5]})
    return {"ivi_regions": reg, "region_group": rg}


def test_area_summary_worked(regions_tiny):
    a = B.area_summary(regions_tiny)
    assert a.loc["regional", "now"] == 150 and a.loc["capital", "now"] == 1350
    assert a.loc["regional", "share"] == pytest.approx(0.1)
    assert a.loc["regional", "share_2019"] == pytest.approx(90 / 1390)
    assert a.loc["capital", "yoy"] == pytest.approx(1350 / 1400 - 1)


def test_regions_filters(regions_tiny):
    assert list(B.regions(regions_tiny)["region"]) == ["Dubbo", "Perth", "Pilbara", "Sydney"]
    assert list(B.regions(regions_tiny, area="capital")["region"]) == ["Perth", "Sydney"]
    assert list(B.regions(regions_tiny, state="WA", sort="Most ads")["region"]) == ["Perth", "Pilbara"]
    assert len(B.regions(regions_tiny, state="AUST")) == 4


def test_region_groups_blank_lq_on_small_cells(regions_tiny):
    g = B.region_groups(regions_tiny, "Dubbo").set_index("anzsco_code")
    assert g.loc["25", "lq"] == 2.0 and g.loc["73", "lq"] == 1.1
    assert np.isnan(g.loc["11", "lq"])  # 15 ads a month: at or under the floor
    over = B.region_groups(regions_tiny, "Dubbo", "Most over-represented")
    assert list(over["anzsco_code"]) == ["25", "73"]


def test_sa4_refuses_2019():
    t = {"sa4_areas": pd.DataFrame({"region_level": ["SA4"], "region_name": ["X"], "state": ["NSW"],
                                    "now": [1.0], "prev": [1.0], "yoy": [0.0], "change": [0.0]})}
    with pytest.raises(ValueError, match="2019"):
        B.sa4(t, sort="Furthest above 2019")


def test_pct():
    assert B.pct(-0.0326) == "−3.3%"
    assert B.pct(0.06627, 0) == "+7%"
    assert B.pct(0.212) == "+21.2%"
    assert B.pct(float("nan")) == "–"
    assert B.pct(None) == "–"


# ---------------------------------------------------------------- the real data

@pytest.fixture(scope="module")
def t():
    return B.load_results()


@pytest.fixture(scope="module")
def totals():
    return D.totals_wide(load_occupation_state())


def test_codes_stay_text(t):
    assert t["occupation_national"]["anzsco_code"].map(type).eq(str).all()
    assert "1A" in set(t["region_group"]["anzsco_code"])
    assert t["major_group_state"]["major"].map(type).eq(str).all()


def test_headline_matches_parts_1_and_2(totals):
    assert totals.columns.max() == "2026-08"
    h = B.headline(totals)
    assert round(h["now"]) == 209655 and round(h["change"]) == -7051
    assert B.pct(h["yoy"]) == "−3.3%" and B.pct(h["vs_2019"]) == "+21.2%"
    assert B.pct(h["latest_yoy"]) == "+0.9%"


def test_state_headline_matches_part_2(totals):
    assert B.pct(B.headline(totals, "SA")["vs_2019"]) == "+82.5%"
    assert B.pct(B.headline(totals, "ACT")["yoy"]) == "−15.8%"


def test_major_groups_match_part_2(t):
    mg = B.major_groups(t).set_index("name")
    assert B.pct(mg.loc["Machinery operators and drivers", "yoy"]) == "+6.6%"
    assert B.pct(mg.loc["Machinery operators and drivers", "vs_2019"]) == "+62.0%"
    assert (mg["yoy"] > 0).sum() == 1
    # state groups come straight from the Part 2 CSV
    sa = B.major_groups(t, state="SA").set_index("major")
    assert B.pct(sa.loc["7", "yoy"], 0) == "+18%"


def test_occupation_table_matches_part_2(t):
    gained = B.occupations(t, sort="Most ads gained").iloc[0]
    assert gained["anzsco_title"].startswith("General Practitioners")
    assert round(gained["change"]) == 1362
    lost = B.occupations(t, sort="Most ads lost")
    assert list(lost["anzsco_title"][:2]) == ["General Clerks", "Waiters"]
    big = B.occupations(t, min_now=500)
    rated = big[big["demand_state"] != B.NOT_RATED]
    assert rated["demand_state"].value_counts().to_dict() == {
        "Cooling, still above 2019": 52, "Growing, above 2019": 32,
        "Shrinking, below 2019": 22, "Rising, still below 2019": 2}


def test_no_rate_on_small_bases_anywhere(t):
    for name in ["occupation_national", "occupation_state", "ivi_regions", "region_group"]:
        d = t[name]
        assert d.loc[d["prev"] <= D.FLOOR, "yoy"].isna().all(), name
        assert d.loc[d["y2019"] <= D.FLOOR, "vs_2019"].isna().all(), name
    ranked = B.occupations(t, state="TAS", sort="Fastest rising on the year")
    assert (ranked["prev"] > D.FLOOR).all()


def test_regions_match_part_3(t):
    a = B.area_summary(t)
    assert round(a.loc["regional", "now"]) == 61229
    assert B.pct(a.loc["regional", "vs_2019"]) == "+67.1%"
    assert B.pct(a.loc["capital", "vs_2019"]) == "+4.9%"
    assert f"{a.loc['regional', 'share']:.1%}" == "30.1%"
    assert f"{a.loc['regional', 'share_2019']:.1%}" == "21.2%"
    below = B.regions(t, sort="Furthest below 2019")
    below = below[below["vs_2019"] < 0]
    assert list(below["region"]) == ["Canberra & ACT", "Sydney", "Melbourne"]
    assert len(B.regions(t, area="regional")) == 29


def test_region_groups_match_part_3(t):
    g = B.region_groups(t, "NSW North Coast", "Most over-represented").iloc[0]
    assert g["group_title"] == "Medical Practitioners and Nurses"
    assert round(g["now"]) == 541 and f"{g['lq']:.1f}" == "2.7" and B.pct(g["yoy"]) == "+62.0%"
    assert len(B.region_groups(t, "Sydney")) == 48


def test_sa4_matches_part_3(t):
    top = B.sa4(t, level="SA4").iloc[0]
    assert top["region_name"] == "New England and North West" and B.pct(top["yoy"]) == "+21.3%"
    assert len(B.sa4(t)) == 50 and len(B.sa4(t, level="GCCSA")) == 8
    assert "vs_2019" not in t["sa4_areas"].columns
