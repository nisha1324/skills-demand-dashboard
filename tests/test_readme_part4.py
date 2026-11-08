"""The README's Part 4 section: every figure must come from the dashboard's own data layer."""
import re
from pathlib import Path

from ivi import dashboard as B

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()


def part4():
    return re.sub(r"\s+", " ", README.split("## Part 4:")[1].split("## How to run")[0])


def test_screenshots_exist():
    for name in re.findall(r"\]\((docs/[^)]+\.png)\)", part4()):
        assert (ROOT / name).exists(), name


def test_counts_in_the_tab_table():
    t = B.load_results()
    text = part4()
    n = len(B.occupations(t))
    assert f"All {n} published occupations" in text
    lv = t["sa4_areas"]["region_level"].value_counts()
    assert f"The {lv['GCCSA']} greater capital cities and {lv['SA4']} regional SA4s" in text
    assert f"the {len(t['ivi_regions'])} IVI regions" in text


def test_worked_example():
    t = B.load_results()
    top = B.occupations(t, "QLD", "2", "Fastest rising on the year", 100).iloc[0]
    text = part4()
    assert "Queensland, Professionals and \"Fastest rising on the year\" with at least 100 ads" in text
    assert top["anzsco_title"] == "Primary School Teachers"
    assert (f"primary school teachers, from {top['prev']:.0f} to {top['now']:.0f} ads a month "
            f"({B.pct(top['yoy'])})") in text
    assert f"that's {1 + top['vs_2019']:.1f} times its 2019 level" in text


def test_floor_stated_matches_code():
    from ivi import demand as D
    assert D.FLOOR == 20.0 and "base of 20 ads a month or fewer" in part4()
