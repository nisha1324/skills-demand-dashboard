"""The README's Part 2 figures must come from the generated report, not be typed in by hand."""
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
REPORT = (ROOT / "results" / "OCCUPATION_DEMAND.md").read_text()
NAT = pd.read_csv(ROOT / "results" / "occupation_national.csv", dtype={"anzsco_code": str}).set_index("anzsco_code")
MG_STATE = pd.read_csv(ROOT / "results" / "major_group_state.csv", dtype={"major": str})

NUMBER = re.compile(r"[−+]?\d+(?:,\d{3})*(?:\.\d+)?[%×]?")
# Figures that come from a CSV rather than the report text; each is checked below.
FROM_CSV = {"+18%", "+14%", "6"}
# Method words, not results: "12-month", "3 months", "20 ads", years and "Part 2".
METHOD = {"12", "3", "20", "2", "2019", "2025", "2026", "1", "5", "8", "500"}


def part2():
    return README.split("## Part 2:")[1].split("## Part 3:")[0]


def test_every_part2_figure_is_in_the_report():
    missing = [t for t in NUMBER.findall(part2())
               if t not in FROM_CSV and t not in METHOD and t not in REPORT]
    assert not missing, missing


def test_heatmap_figures_match_the_csv():
    m = MG_STATE[MG_STATE["major"] == "7"].set_index("state")["yoy"]
    assert round(m["SA"] * 100) == 18 and round(m["WA"] * 100) == 14
    assert (m > 0).sum() == 6 and m.idxmax() == "SA"
    assert "rose in 6 of the 8 states" in part2()


@pytest.mark.parametrize("phrase, code, now, yoy", [
    ("registered nurses (6,883 ads a month, +6.1%)", "2544", 6883, 0.061),
    ("GPs\n  (5,105, +36.4%)", "2531", 5105, 0.364),
    ("electricians (3,064, +9.3%)", "3411", 3064, 0.093),
    ("truck drivers (2,807, +2.0%)", "7331", 2807, 0.020),
    ("child carers (−12.9%)", "4211", None, -0.129),
    ("aged and disabled carers (−3.1%)", "4231", None, -0.031),
])
def test_named_occupations_match_their_rows(phrase, code, now, yoy):
    assert phrase in part2()
    r = NAT.loc[code]
    if now is not None:
        assert round(r["now"]) == now
    assert round(r["yoy"], 3) == yoy


@pytest.mark.parametrize("phrase, code, col, value", [
    ("software programmers −46.6%", "2613", "vs_2019", -0.466),
    ("ICT business and systems analysts\n  −41.0%", "2611", "vs_2019", -0.410),
    ("GPs\n  4.8×", "2531", "ratio", 4.8),
    ("vets 5.1×", "2347", "ratio", 5.1),
])
def test_named_comparisons_with_2019_match_their_rows(phrase, code, col, value):
    assert phrase in part2()
    r = NAT.loc[code]
    got = r["now"] / r["y2019"] if col == "ratio" else r[col]
    assert round(got, 1 if col == "ratio" else 3) == value


def flat(text):
    return re.sub(r"\s+", " ", text)


def signed(x, nd=1):
    return f"{x * 100:+.{nd}f}%".replace("-", "−")


@pytest.fixture(scope="module")
def facts():
    from ivi import demand as D
    from ivi.load import load_occupation_state, load_skill_level
    occ = load_occupation_state()
    tot = D.compare(D.totals_wide(occ), "2026-08")
    mg = D.compare(D.major_group_wide(occ), "2026-08")
    sk = D.skill_level_compare(load_skill_level(), "2026-08")
    nat = D.compare(D.national_wide(occ), "2026-08")
    q = D.quadrant(nat, 500)
    multi = nat[(nat["vs_2019"] >= 2) & (nat["now"] >= 100)]
    return {"tot": tot, "mg": mg, "sk": sk, "q": q, "multi": multi}


def test_table_rows_are_copied_from_the_report():
    rows = [ln for ln in part2().splitlines() if ln.startswith("| ") and not ln.startswith("| Demand")]
    assert len(rows) == 4
    for ln in rows:
        assert ln in REPORT.splitlines(), ln


def test_headline_sentences_match_the_data(facts):
    t, mg, sk, q, multi = facts["tot"], facts["mg"], facts["sk"], facts["q"], facts["multi"]
    a = t.loc["AUST"]
    text = flat(part2())
    expected = [
        f"Ads averaged {a['now']:,.0f} a month in the 12 months to August 2026, {signed(a['yoy'])} on the year before.",
        f"the latest 3 months are {signed(a['latest_yoy'])} on a year earlier",
        f"seasonally adjusted August figure is {signed(sk.loc[0, 'latest_yoy'])} on August 2025",
        f"Machinery operators and drivers is the only major group up on the year ({signed(mg.loc['7', 'yoy'])}) "
        f"and the furthest above 2019 ({signed(mg.loc['7', 'vs_2019'])})",
        f"Clerical and administrative workers are barely above 2019 ({signed(mg.loc['5', 'vs_2019'])})",
        f"SA is {signed(t.loc['SA', 'vs_2019'])} on 2019; VIC ({signed(t.loc['VIC', 'vs_2019'])}) and ACT "
        f"({signed(t.loc['ACT', 'vs_2019'])}) are below it, and ACT fell most on the year ({signed(t.loc['ACT', 'yoy'])})",
        f"{(q['quadrant'] == 'Shrinking, below 2019').sum()} big occupations are below 2019 and still falling",
        f"{len(multi)} occupations with 100+ ads a month are at least 3 times their 2019 level",
        f"the {len(q)} occupations with 500+ ads a month",
        "most of all in SA (+18%) and WA (+14%)",
    ]
    for e in expected:
        assert e in text, e
    # the claims behind the wording
    assert (mg["yoy"] > 0).sum() == 1 and mg["vs_2019"].idxmax() == "7"
    states = t.drop("AUST")
    assert states["vs_2019"].idxmax() == "SA" and states["yoy"].idxmin() == "ACT"
    assert sorted(states.index[states["vs_2019"] < 0]) == ["ACT", "VIC"]
