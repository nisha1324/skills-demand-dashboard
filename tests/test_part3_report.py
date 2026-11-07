"""Part 3 on the committed snapshot: the report regenerates exactly and its totals reconcile."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ivi import demand as D
from ivi import regions as R
from ivi.load import load_ivi_region, load_occupation_state, load_sa4_region

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUTS = ["REGIONAL_DEMAND.md", "ivi_regions.csv", "region_group.csv", "sa4_areas.csv",
           "regional_share.csv", "charts/09_regional_share.png", "charts/10_regions_vs_2019.png",
           "charts/11_group_regional_share.png", "charts/12_sa4_year_on_year.png"]
END = "2026-08"


@pytest.fixture(scope="module")
def r():
    return load_ivi_region()


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory):
    from scripts import regional_demand
    out = tmp_path_factory.mktemp("part3")
    regional_demand.main(out)
    return out


@pytest.mark.parametrize("name", OUTPUTS)
def test_report_regenerates_byte_for_byte(regenerated, name):
    assert (regenerated / name).read_bytes() == (RESULTS / name).read_bytes(), name


def test_37_regions_8_of_them_capitals(r):
    regions = R.region_states(r)
    assert len(regions) == 37
    assert set(R.CAPITALS.values()) <= set(regions.index)
    for state, cap in R.CAPITALS.items():
        assert regions[cap] == state
    assert (R.area_of(pd.Series(regions.index)) == "regional").sum() == 29


def test_capital_and_regional_add_up_to_the_37_regions(r):
    a = R.area_wide(r)
    w = R.region_wide(r)
    assert a[END].sum() == pytest.approx(w[END].sum())
    assert w.columns.min() == R.START


@pytest.mark.parametrize("level", [2, 3])
def test_groups_add_up_to_region_totals(r, level):
    tot = R.region_wide(r)[END]
    parts = R.region_wide(r, level=level)[END].groupby(level=0).sum()
    assert np.allclose(parts.reindex(tot.index), tot, atol=0.01)


def test_share_bound_is_below_the_share_and_the_unplaced_gap_opened_after_2019(r):
    occ = load_occupation_state()
    nat = D.compare(D.totals_wide(occ), END).loc["AUST"]
    b = R.share_bounds(D.compare(R.area_wide(r), END), nat)
    assert (b["share_lower_bound"] <= b["share_of_placed"]).all()
    assert b.loc["2019", "unplaced"] / b.loc["2019", "national"] < 0.01
    assert b.loc["now", "unplaced"] / b.loc["now", "national"] > 0.02


def test_csv_region_shares_match_the_table():
    s = pd.read_csv(RESULTS / "regional_share.csv")
    reg = pd.read_csv(RESULTS / "ivi_regions.csv")
    assert s["month"].iloc[0] == "2011-09" and s["month"].iloc[-1] == END
    last = reg.groupby("area")["now"].sum()
    assert round(last["regional"] / last.sum(), 5) == s["regional_share"].iloc[-1]


def test_location_quotients_average_to_one_on_the_real_data():
    g = pd.read_csv(RESULTS / "region_group.csv", dtype={"anzsco_code": str})
    w = g.groupby("region")["now"].transform("sum") / g["now"].sum()
    mean_lq = (g["lq"] * w).groupby(g["anzsco_code"]).sum()
    assert np.allclose(mean_lq, 1.0, atol=1e-3)


def test_sa4_file_is_used_year_on_year_only():
    sa4 = pd.read_csv(RESULTS / "sa4_areas.csv")
    assert len(sa4) == 50 and (sa4["region_level"] == "GCCSA").sum() == 8
    assert not any("2019" in c for c in sa4.columns)
    report = (RESULTS / "REGIONAL_DEMAND.md").read_text()
    sa4_part = report.split("## Year on year in the GCCSA/SA4 areas")[1].split("## So what")[0]
    assert "2019" not in sa4_part


def test_floor_applies_to_region_group_cells():
    g = pd.read_csv(RESULTS / "region_group.csv", dtype={"anzsco_code": str})
    assert g.loc[g["prev"] <= D.FLOOR, "yoy"].isna().all()
    assert g.loc[g["y2019"] <= D.FLOOR, "vs_2019"].isna().all()
    assert g.loc[g["prev"] > D.FLOOR, "yoy"].notna().all()


def test_the_two_geographies_agree_on_the_capitals():
    reg = pd.read_csv(RESULTS / "ivi_regions.csv").set_index("region")
    sa4 = pd.read_csv(RESULTS / "sa4_areas.csv")
    g = sa4[sa4["region_level"] == "GCCSA"].set_index("state")
    for state, cap in R.CAPITALS.items():
        assert np.sign(reg.loc[cap, "yoy"]) == np.sign(g.loc[state, "yoy"]), state
        assert abs(reg.loc[cap, "yoy"] - g.loc[state, "yoy"]) < 0.01, state


def test_every_regional_area_is_above_2019_and_only_capitals_are_below():
    reg = pd.read_csv(RESULTS / "ivi_regions.csv")
    assert (reg.loc[reg["area"] == "regional", "vs_2019"] > 0).all()
    assert sorted(reg.loc[reg["vs_2019"] < 0, "region"]) == ["Canberra & ACT", "Melbourne", "Sydney"]
