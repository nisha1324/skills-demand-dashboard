"""The README's Part 3 figures must come from the generated report and match the CSVs behind it."""
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
README = (ROOT / "README.md").read_text()
REPORT = (RES / "REGIONAL_DEMAND.md").read_text()
REG = pd.read_csv(RES / "ivi_regions.csv").set_index("region")
RG = pd.read_csv(RES / "region_group.csv", dtype={"anzsco_code": str})
SA4 = pd.read_csv(RES / "sa4_areas.csv")
SHARE = pd.read_csv(RES / "regional_share.csv").set_index("month")

NUMBER = re.compile(r"[−+]?\d+(?:,\d{3})*(?:\.\d+)?[%×]?")
# Method words and labels, not results: years, "37 IVI regions", "8 capital-city regions",
# "Part 1", "12 months", "3 in 10", "6 of the 10" (checked below).
METHOD = {"1", "2", "3", "8", "10", "12", "29", "37", "42", "2010", "2019", "2020", "2022", "2026", "6"}


def part3():
    return README.split("## Part 3:")[1].split("## How to run")[0]


def flat(text):
    return re.sub(r"\s+", " ", text)


def signed(x, nd=1):
    return f"{x * 100:+.{nd}f}%".replace("-", "−")


def pct(x, nd=1):
    return f"{x * 100:.{nd}f}%"


def test_every_part3_figure_is_in_the_report():
    missing = [t for t in NUMBER.findall(part3()) if t not in METHOD and t not in REPORT]
    assert not missing, missing


@pytest.fixture(scope="module")
def areas():
    a = REG.groupby("area")[["now", "prev", "y2019", "change"]].sum()
    a["yoy"] = a["now"] / a["prev"] - 1
    a["vs_2019"] = a["now"] / a["y2019"] - 1
    return a


def group(code):
    g = RG[RG["anzsco_code"] == code].copy()
    g["area"] = g["region"].map(REG["area"])
    a = g.groupby("area")[["now", "prev", "y2019", "change"]].sum()
    return {
        "share_now": a.loc["regional", "now"] / a["now"].sum(),
        "share_2019": a.loc["regional", "y2019"] / a["y2019"].sum(),
        "reg_yoy": a.loc["regional", "now"] / a.loc["regional", "prev"] - 1,
        "cap_yoy": a.loc["capital", "now"] / a.loc["capital", "prev"] - 1,
        "reg_change": a.loc["regional", "change"],
        "cap_change": a.loc["capital", "change"],
    }


def test_capital_vs_regional_sentences(areas):
    a = areas
    s2019 = a.loc["regional", "y2019"] / a["y2019"].sum()
    s_now = a.loc["regional", "now"] / a["now"].sum()
    text = flat(part3())
    for e in [
        f"The 29 regional areas averaged {a.loc['regional', 'now']:,.0f} ads a month in the 12 months to "
        f"August 2026, {signed(a.loc['regional', 'vs_2019'])} on 2019, against {signed(a.loc['capital', 'vs_2019'])} "
        "for the capital-city regions.",
        f"Regional Australia now holds {pct(s_now)} of placed ads, up from {pct(s2019)} in 2019.",
        f"the capitals lost {-a.loc['capital', 'change']:,.0f} ads a month ({signed(a.loc['capital', 'yoy'])}) while "
        f"regional areas gained {a.loc['regional', 'change']:,.0f} ({signed(a.loc['regional', 'yoy'])})",
    ]:
        assert e in text, e
    assert s_now == pytest.approx(SHARE["regional_share"].iloc[-1], abs=1e-5)


def test_coding_effect_sentences():
    from ivi import demand as D
    from ivi import regions as R
    from ivi.load import load_ivi_region, load_occupation_state
    occ = load_occupation_state()
    nat = D.compare(D.totals_wide(occ), "2026-08").loc["AUST"]
    b = R.share_bounds(D.compare(R.area_wide(load_ivi_region()), "2026-08"), nat)
    shift = (b.loc["now", "share_of_placed"] - b.loc["2019", "share_of_placed"]) * 100
    b_shift = (b.loc["now", "share_lower_bound"] - b.loc["2019", "share_lower_bound"]) * 100
    s = SHARE["regional_share"]
    after_peak = s[s.index > s[s.index <= "2021-12"].idxmax()]
    trough = after_peak.idxmin()
    climb = s[s.index >= trough].diff().dropna()
    text = flat(part3())
    for e in [
        f"On average {b.loc['now', 'unplaced']:,.0f} ads a month aren't placed in any region.",
        f"the regional share would be {pct(b.loc['now', 'share_lower_bound'])}, so unplaced ads can explain at "
        f"most {shift - b_shift:.1f} of the {shift:.1f} points of shift",
        f"fell back to {pct(s[trough])} in July 2022, then rose in {(climb > 0).sum()} of the {len(climb)} months since",
    ]:
        assert e in text, e
    assert trough == "2022-07"


def test_regions_against_2019():
    # recompute the rate from the ad counts: the CSV's rates are rounded to 4 decimals, and
    # rounding those again can move the last digit (0.18049 -> 0.1805 -> "+18.1%")
    REG_ = REG.assign(vs_2019=REG["now"] / REG["y2019"] - 1)
    below = REG_[REG_["vs_2019"] < 0].sort_values("vs_2019")
    regs = REG_[REG_["area"] == "regional"]
    assert list(below.index) == ["Canberra & ACT", "Sydney", "Melbourne"]
    assert (below["area"] == "capital").all() and (regs["vs_2019"] > 0).all()
    lo, hi = regs["vs_2019"].idxmin(), regs["vs_2019"].idxmax()
    text = flat(part3())
    assert (f"Canberra & ACT ({signed(below.loc['Canberra & ACT', 'vs_2019'])}), Sydney "
            f"({signed(below.loc['Sydney', 'vs_2019'])}) and Melbourne ({signed(below.loc['Melbourne', 'vs_2019'])})") in text
    assert f"from Pilbara & Kimberley ({signed(regs.loc[lo, 'vs_2019'])}) to Tamworth and North West NSW " \
           f"({signed(regs.loc[hi, 'vs_2019'])})" in text
    assert lo == "Pilbara & Kimberley" and hi == "Tamworth and North West NSW"


def test_occupation_group_sentences():
    h, c, l, ict = group("2H"), group("42"), group("27"), group("26")
    text = flat(part3())
    for e in [
        f"{pct(h['share_now'])} of ads for medical practitioners and nurses are now regional ({pct(h['share_2019'])} in 2019)",
        f"Regional ads for them rose {signed(h['reg_yoy'])} on the year while the capitals' were flat ({signed(h['cap_yoy'])})",
        f"regional areas added {h['reg_change']:,.0f} a month and the capitals lost {-h['cap_change']:,.0f}",
        f"Carers and aides ({pct(c['share_now'])} regional, from {pct(c['share_2019'])})",
        f"legal, social and welfare professionals ({pct(l['share_now'])}, from {pct(l['share_2019'])}; "
        f"{signed(l['reg_yoy'])} in the regions on the year, {signed(l['cap_yoy'])} in the capitals)",
        f"only {pct(ict['share_now'])} are regional",
    ]:
        assert e in text, e
    assert h["cap_change"] < 0 < h["reg_change"]


def test_sa4_sentences():
    lv = SA4.groupby("region_level")[["now", "prev"]].sum()
    yoy = lv["now"] / lv["prev"] - 1
    top10 = SA4[(SA4["region_level"] == "SA4") & (SA4["prev"] > 20)].sort_values("yoy", ascending=False).head(10)
    text = flat(part3())
    assert (f"the 8 greater capital cities are {signed(yoy['GCCSA'])} on the year and the 42 regional SA4s "
            f"{signed(yoy['SA4'])}") in text
    assert f"{(top10['state'] == 'NSW').sum()} of the 10 fastest-growing SA4s are in NSW" in text
    assert f"topped by {top10['region_name'].iloc[0]} ({signed(top10['yoy'].iloc[0])})" in text
    # the capital cross-check, from the counts in both CSVs
    from ivi.regions import CAPITALS
    g = SA4[SA4["region_level"] == "GCCSA"].set_index("state")
    gaps = [abs((g.loc[s, "now"] / g.loc[s, "prev"]) - (REG.loc[c, "now"] / REG.loc[c, "prev"])) * 100
            for s, c in CAPITALS.items()]
    assert f"give the same direction for all 8 capitals, at most {max(gaps):.1f} points apart" in text


def test_business_read_out_figures():
    text = flat(part3())
    big = REG[(REG["area"] == "regional") & (REG["now"] >= 500)].sort_values("yoy", ascending=False).head(3)
    items = [f"{r} ({signed(v)})" for r, v in zip(big.index, big["yoy"])]
    assert f"{items[0]}, {items[1]} and {items[2]}" in text
    nc = RG[(RG["region"] == "NSW North Coast") & (RG["anzsco_code"] == "2H")].iloc[0]
    assert f"medical practitioners and nurses have {nc['now']:,.0f} ads a month, {nc['lq']:.1f}× as common as across " \
           f"all regions, and {signed(nc['yoy'])} on the year" in text
    tw = RG[(RG["region"] == "Tamworth and North West NSW") & (RG["anzsco_code"] == "2H")].iloc[0]
    assert f"went from {tw['prev']:,.0f} to {tw['now']:,.0f} a month in a year" in text
