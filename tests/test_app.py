"""Smoke tests: the Streamlit dashboard renders on the committed data, its headline tiles show
the report figures, and every filter can be changed without an error."""
import pytest
from streamlit.testing.v1 import AppTest

APP = "../app/dashboard.py"


@pytest.fixture(scope="module")
def at():
    a = AppTest.from_file(APP, default_timeout=180).run()
    assert not a.exception
    return a


def metric(at, label):
    return next(m for m in at.metric if m.label == label)


def test_tabs_and_headline(at):
    assert [t.label for t in at.tabs] == ["Overview", "Occupations", "Regions",
                                          "SA4 areas (year on year)", "About the data"]
    assert metric(at, "Job ads a month (12-month average)").value == "209,655"
    assert metric(at, "On the year before").value == "−3.3%"
    assert metric(at, "Against 2019").value == "+21.2%"
    assert metric(at, "Latest 3 months vs a year earlier").value == "+0.9%"
    assert metric(at, "Regional share of placed ads").value == "30.1%"
    assert metric(at, "Regional areas: ads a month").value == "61,229"
    assert "August 2026" in at.caption[0].value


def test_state_switch_changes_the_tiles():
    a = AppTest.from_file(APP, default_timeout=180).run()
    a.selectbox(key="ov_state").set_value("SA").run()
    assert not a.exception
    assert metric(a, "Against 2019").value == "+82.5%"
    a.radio(key="ov_vs").set_value("2019").run()
    assert not a.exception


def test_occupation_filters():
    a = AppTest.from_file(APP, default_timeout=180).run()
    a.selectbox(key="oc_state").set_value("QLD").run()
    a.selectbox(key="oc_major").set_value("2").run()
    a.selectbox(key="oc_sort").set_value("Fastest rising on the year").run()
    a.number_input(key="oc_min").set_value(100).run()
    assert not a.exception
    df = a.dataframe[0].value
    assert len(df) > 0 and (df["anzsco_code"].str[0] == "2").all() and (df["now"] >= 100).all()
    assert df["yoy"].notna().all() and df["yoy"].is_monotonic_decreasing
    # the drill-down only offers occupations in the filtered table (in table order); an earlier
    # pick that is still in the table stays selected
    pick = a.selectbox(key="oc_pick")
    assert pick.value in set(df["anzsco_code"])
    assert len(pick.options) == len(df)


def test_search_with_no_match_hides_the_drill_down():
    a = AppTest.from_file(APP, default_timeout=180).run()
    a.text_input(key="oc_search").set_value("zzzz no such job").run()
    assert not a.exception
    assert len(a.dataframe[0].value) == 0
    assert "oc_pick" not in [s.key for s in a.selectbox]


def test_region_filters_and_drill_down():
    a = AppTest.from_file(APP, default_timeout=180).run()
    a.selectbox(key="rg_area").set_value("regional").run()
    a.selectbox(key="rg_state").set_value("NSW").run()
    a.radio(key="rg_vs").set_value("On the year").run()
    assert not a.exception
    a.selectbox(key="rg_pick").set_value("NSW North Coast").run()
    a.selectbox(key="rg_gsort").set_value("Most over-represented").run()
    assert not a.exception
    series = a.selectbox(key="rg_series")
    assert series.options[0] == "All ads in NSW North Coast"
    assert series.options[1] == "Medical Practitioners and Nurses"  # the most over-represented
    series.select_index(1).run()
    assert not a.exception


def test_sa4_tab_has_no_2019_option():
    a = AppTest.from_file(APP, default_timeout=180).run()
    assert not any("2019" in o for o in a.selectbox(key="sa_sort").options)
    a.selectbox(key="sa_state").set_value("WA").run()
    a.selectbox(key="sa_level").set_value("SA4").run()
    assert not a.exception
