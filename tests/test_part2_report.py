"""Part 2 on the committed snapshot: the report regenerates exactly and its totals reconcile."""
from pathlib import Path

import pandas as pd
import pytest

from ivi import demand as D
from ivi import profile as P
from ivi.load import load_occupation_state, load_skill_level

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUTS = ["OCCUPATION_DEMAND.md", "occupation_national.csv", "occupation_state.csv",
           "major_group_state.csv", "charts/05_major_groups.png", "charts/06_contributions.png",
           "charts/07_demand_matrix.png", "charts/08_state_heatmap.png"]


@pytest.fixture(scope="module")
def occ():
    return load_occupation_state()


@pytest.fixture(scope="module")
def regenerated(tmp_path_factory):
    from scripts import occupation_demand
    out = tmp_path_factory.mktemp("part2")
    occupation_demand.main(out)
    return out


@pytest.mark.parametrize("name", OUTPUTS)
def test_report_regenerates_byte_for_byte(regenerated, name):
    assert (regenerated / name).read_bytes() == (RESULTS / name).read_bytes(), name


def test_national_12_month_average_matches_part_1(occ):
    h = P.headline(occ, load_skill_level())
    c = D.compare(D.totals_wide(occ), h["month"]).loc["AUST"]
    assert c["now"] == pytest.approx(h["last12_avg"])
    assert c["yoy"] == pytest.approx(h["last12_vs_prev12"])


def test_major_groups_add_up_to_the_published_occupations(occ):
    end = "2026-08"
    g = D.major_group_wide(occ)[end]
    assert list(g.index) == list(D.MAJOR_GROUPS)
    assert g.sum() == pytest.approx(D.national_wide(occ)[end].sum())


def test_states_add_up_to_australia_on_12_month_averages(occ):
    c = D.compare(D.totals_wide(occ), "2026-08")
    assert c.loc[P.STATES, "now"].sum() == pytest.approx(c.loc["AUST", "now"], rel=1e-4)


def test_csv_has_every_published_occupation(occ):
    nat = pd.read_csv(RESULTS / "occupation_national.csv", dtype={"anzsco_code": str})
    assert len(nat) == D.national_wide(occ).shape[0] == 351
    assert nat["anzsco_code"].str.fullmatch(r"\d{4}").all()
    # the floor: no rate on a base of 20 ads or fewer
    assert nat.loc[nat["prev"] <= D.FLOOR, "yoy"].isna().all()
    assert nat.loc[nat["y2019"] <= D.FLOOR, "vs_2019"].isna().all()
