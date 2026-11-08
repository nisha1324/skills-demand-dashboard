"""Skills-demand dashboard: which jobs and regions are hiring in Australia.

Run: streamlit run app/dashboard.py

Every table comes from the CSVs that Parts 2 and 3 wrote to results/ (so the numbers match the
reports), and the monthly charts come from the committed snapshot in data/. Nothing is fetched.
"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ivi import dashboard as B  # noqa: E402
from ivi import demand as D  # noqa: E402
from ivi import regions as R  # noqa: E402
from ivi.load import load_ivi_region, load_occupation_state  # noqa: E402

# Colours: the same validated steps as the report charts (light surface)
BLUE, LIGHT_BLUE, ORANGE, RED = "#2a78d6", "#9ec2ef", "#eb6834", "#e34948"
INK_2, MUTED = "#52514e", "#8a8984"
AVG, RAW = B.AVG, B.RAW

st.set_page_config(page_title="Skills-demand dashboard (Australia)", layout="wide")


@st.cache_data
def tables() -> dict:
    return B.load_results()


@st.cache_data
def occupation_series() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """(state totals, Australia occupations, state x occupation), one column per month."""
    occ = load_occupation_state()
    return D.totals_wide(occ), D.national_wide(occ), D.state_occupation_wide(occ)


@st.cache_data
def region_series() -> tuple[pd.DataFrame, pd.DataFrame]:
    r = load_ivi_region()
    return R.region_wide(r, level=1), R.region_wide(r, level=3)


def month_label(m: str) -> str:
    return pd.Period(m, "M").strftime("%B %Y")


def pct_cols(d: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Rates as percentages for display (blank stays blank)."""
    d = d.copy()
    for c in cols:
        d[c] = d[c] * 100
    return d


def trend_chart(series: pd.DataFrame, baseline: float | None, height: int = 300) -> alt.Chart:
    """Raw 3-month averages (light) and the 12-month average (dark), with a crosshair tooltip
    that reads out both, and a dashed line at the 2019 average."""
    color = alt.Color("series:N", scale=alt.Scale(domain=[RAW, AVG], range=[LIGHT_BLUE, BLUE]),
                      legend=alt.Legend(orient="top", title=None, symbolType="stroke"))
    base = alt.Chart(series).encode(x=alt.X("month:T", title=None),
                                    y=alt.Y("ads:Q", title="Job ads a month", scale=alt.Scale(zero=True)),
                                    color=color)
    lines = base.mark_line(strokeWidth=2)
    hover = alt.selection_point(nearest=True, on="pointerover", fields=["month"], empty=False,
                                clear="pointerout")
    wide = series.pivot(index="month", columns="series", values="ads").reset_index()
    tips = [alt.Tooltip("month:T", title="3 months to", format="%B %Y")]
    tips += [alt.Tooltip(field=c, type="quantitative", title=c, format=",.0f")
             for c in [AVG, RAW] if c in wide]
    rule = (alt.Chart(wide).mark_rule(color=MUTED, strokeWidth=1)
            .encode(x="month:T", opacity=alt.condition(hover, alt.value(0.8), alt.value(0)), tooltip=tips)
            .add_params(hover))
    points = base.mark_point(size=64, filled=True).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0))).transform_filter(hover)
    layers = [lines, rule, points]
    if baseline:
        ref = pd.DataFrame({"ads": [baseline], "label": [f"2019 average: {baseline:,.0f}"]})
        layers.append(alt.Chart(ref).mark_rule(color=INK_2, strokeDash=[4, 4], strokeWidth=1)
                      .encode(y="ads:Q", tooltip=alt.Tooltip("label:N", title="Baseline")))
        layers.append(alt.Chart(ref).mark_text(align="left", dx=4, dy=-6, color=INK_2, fontSize=11)
                      .encode(y="ads:Q", x=alt.value(0), text="label:N"))
    return alt.layer(*layers).properties(height=height)


def change_bars(d: pd.DataFrame, label: str, value: str, title: str, tooltip: list,
                color: alt.Color | None = None) -> alt.Chart:
    """Horizontal bars of a % change, sorted, 24px per bar. Default colour is by sign (blue up,
    red down)."""
    d = d[d[value].notna()].copy()
    d["pct"] = d[value] * 100
    d["direction"] = d["pct"].map(lambda v: "Up" if v > 0 else "Down")
    if color is None:
        color = alt.Color("direction:N", scale=alt.Scale(domain=["Up", "Down"], range=[BLUE, RED]),
                          legend=alt.Legend(orient="top", title=None))
    return (alt.Chart(d).mark_bar(cornerRadiusEnd=4, height={"band": 0.75})
            .encode(y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
                    x=alt.X("pct:Q", title=title, axis=alt.Axis(tickCount=8)), color=color,
                    tooltip=tooltip)
            .properties(height=alt.Step(24)))


t = tables()
totals, nat_w, so_w = occupation_series()
END = totals.columns.max()

st.title("Which jobs and regions are hiring in Australia?")
st.caption(
    f"Online job ads from Jobs and Skills Australia's Internet Vacancy Index, to {month_label(END)}. "
    "Changes compare 12-month averages (the year to the latest month vs the year before, and vs "
    "2019), so the seasonal swing cancels. No growth rate is shown where the base has 20 ads a "
    "month or fewer. Job ads are a demand signal, not a count of jobs.")

tab_over, tab_occ, tab_reg, tab_sa4, tab_about = st.tabs(
    ["Overview", "Occupations", "Regions", "SA4 areas (year on year)", "About the data"])

# ---------------------------------------------------------------- Overview
with tab_over:
    c1, c2 = st.columns([2, 3])
    state = c1.selectbox("State or territory", B.STATES, format_func=B.STATE_NAMES.get, key="ov_state")
    vs = c2.radio("Compare occupation groups with", ["The year before", "2019"], horizontal=True,
                  key="ov_vs")
    h = B.headline(totals, state)
    k = st.columns(4)
    k[0].metric("Job ads a month (12-month average)", f"{h['now']:,.0f}",
                f"{h['change']:+,.0f} on the year before")
    k[1].metric("On the year before", B.pct(h["yoy"]))
    k[2].metric("Against 2019", B.pct(h["vs_2019"]))
    k[3].metric("Latest 3 months vs a year earlier", B.pct(h["latest_yoy"]),
                help="The latest 3-month average against the same 3 months a year before: "
                     "the most recent direction, but noisier than the 12-month figures.")
    st.subheader(f"Job ads in {B.STATE_NAMES[state]}")
    full = st.toggle("Show from 2006", value=False, key="ov_full")
    st.altair_chart(trend_chart(B.monthly(totals.loc[state], None if full else "2015-01"), h["y2019"]),
                    width="stretch", theme=None)
    st.caption("The raw 3-month average dips every summer (about 18% from October to January), "
               "so read direction from the 12-month average.")

    mg = B.major_groups(t, state=state)
    col = "yoy" if vs == "The year before" else "vs_2019"
    st.subheader("Occupation groups: " + ("change on the year before" if col == "yoy" else "change against 2019"))
    st.altair_chart(change_bars(
        mg, "name", col, "Change in job ads a month (%)",
        [alt.Tooltip("name:N", title="Group"), alt.Tooltip("pct:Q", title="Change (%)", format="+.1f"),
         alt.Tooltip("now:Q", title="Ads a month", format=",.0f"),
         alt.Tooltip("change:Q", title="Change on the year (ads)", format="+,.0f")]),
        width="stretch", theme=None)

# ---------------------------------------------------------------- Occupations
with tab_occ:
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    o_state = c1.selectbox("State or territory", B.STATES, format_func=B.STATE_NAMES.get, key="oc_state")
    majors = [None] + list(D.MAJOR_GROUPS)
    o_major = c2.selectbox("Occupation group", majors, key="oc_major",
                           format_func=lambda m: "All groups" if m is None else D.MAJOR_GROUPS[m])
    o_sort = c3.selectbox("Sort by", list(B.SORTS), key="oc_sort")
    o_min = c4.number_input("At least this many ads a month", min_value=0, value=0, step=50, key="oc_min")
    o_search = st.text_input("Search occupations", "", key="oc_search", placeholder="e.g. nurse, electrician")
    occ = B.occupations(t, o_state, o_major, o_sort, o_min, o_search)
    if B.SORTS[o_sort][0] in B.RATE_COLS:
        st.caption("Occupations with 20 or fewer ads a month in the base period have no rate, so "
                   "they're left out of this ranking.")
    show = pct_cols(occ, ["yoy", "vs_2019", "latest_yoy"])
    st.dataframe(
        show[["anzsco_title", "anzsco_code", "now", "change", "yoy", "vs_2019", "latest_yoy", "demand_state"]],
        hide_index=True, width="stretch", height=380,
        column_config={"anzsco_title": "Occupation", "anzsco_code": "ANZSCO",
                       "now": st.column_config.NumberColumn("Ads a month", format="%,.0f"),
                       "change": st.column_config.NumberColumn("Change (ads a month)", format="%+,.0f"),
                       "yoy": st.column_config.NumberColumn("On the year", format="%+.1f%%"),
                       "vs_2019": st.column_config.NumberColumn("Vs 2019", format="%+.1f%%"),
                       "latest_yoy": st.column_config.NumberColumn("Latest 3 months vs a year ago",
                                                                   format="%+.1f%%"),
                       "demand_state": "Demand state"})
    st.caption(f"{len(occ)} occupations. Ads a month are 12-month averages to {month_label(END)}. "
               "A blank rate (shown as None) means the base had 20 ads a month or fewer.")

    if len(occ):
        st.subheader("Check the monthly series before acting on a number")
        codes = list(occ["anzsco_code"])
        names = dict(zip(occ["anzsco_code"], occ["anzsco_title"]))
        pick = st.selectbox("Occupation", codes, format_func=lambda c: f"{names[c]} ({c})", key="oc_pick")
        row = nat_w.loc[pick] if o_state == "AUST" else so_w.loc[(o_state, pick)]
        r = occ[occ["anzsco_code"] == pick].iloc[0]
        st.altair_chart(trend_chart(B.monthly(row, "2015-01"), r["y2019"], height=260),
                        width="stretch", theme=None)

        rated = occ[occ["yoy"].notna() & occ["vs_2019"].notna()]
        if len(rated) >= 3:
            st.subheader("Demand matrix")
            st.caption("Each dot is an occupation in the table above with both rates. Right of the "
                       "line: up on the year. Above the line: above 2019.")
            m = rated.assign(yoy_pct=rated["yoy"] * 100, v19_pct=rated["vs_2019"] * 100)
            hover = alt.selection_point(nearest=True, on="pointerover", empty=False, clear="pointerout")
            dots = (alt.Chart(m).mark_circle(color=BLUE, stroke="#fcfcfb", strokeWidth=1)
                    .encode(x=alt.X("yoy_pct:Q", title="Change on the year (%)", axis=alt.Axis(tickCount=10)),
                            y=alt.Y("v19_pct:Q", title="Change against 2019 (%)"),
                            size=alt.Size("now:Q", title="Ads a month", scale=alt.Scale(range=[30, 600]),
                                          legend=alt.Legend(orient="top", format=",.0f")),
                            opacity=alt.condition(hover, alt.value(1), alt.value(0.55)),
                            tooltip=[alt.Tooltip("anzsco_title:N", title="Occupation"),
                                     alt.Tooltip("now:Q", title="Ads a month", format=",.0f"),
                                     alt.Tooltip("yoy_pct:Q", title="On the year (%)", format="+.1f"),
                                     alt.Tooltip("v19_pct:Q", title="Vs 2019 (%)", format="+.1f"),
                                     alt.Tooltip("demand_state:N", title="Demand state")])
                    .add_params(hover))
            zero = pd.DataFrame({"v": [0]})
            axes = [alt.Chart(zero).mark_rule(color=MUTED, strokeWidth=1).encode(x="v:Q"),
                    alt.Chart(zero).mark_rule(color=MUTED, strokeWidth=1).encode(y="v:Q")]
            st.altair_chart(alt.layer(*axes, dots).properties(height=380), width="stretch", theme=None)

# ---------------------------------------------------------------- Regions
with tab_reg:
    a = B.area_summary(t)
    share_now, share_19 = a.loc["regional", "share"], a.loc["regional", "share_2019"]
    k = st.columns(3)
    k[0].metric("Regional share of placed ads", f"{share_now:.1%}",
                f"{(share_now - share_19) * 100:+.1f} points on 2019", delta_color="off")
    k[1].metric("Regional areas: ads a month", f"{a.loc['regional', 'now']:,.0f}",
                f"{B.pct(a.loc['regional', 'vs_2019'])} on 2019")
    k[2].metric("Capital-city regions: ads a month", f"{a.loc['capital', 'now']:,.0f}",
                f"{B.pct(a.loc['capital', 'vs_2019'])} on 2019")

    sh = t["regional_share"].assign(month=lambda d: pd.PeriodIndex(d["month"], freq="M").to_timestamp())
    sh = sh.rename(columns={"regional_share": "Share of placed ads",
                            "lower_bound": "Lowest possible (every unplaced ad in a capital)"})
    sh_long = sh.melt("month", var_name="series", value_name="share")
    sh_long["share_pct"] = sh_long["share"] * 100
    sh_hover = alt.selection_point(nearest=True, on="pointerover", fields=["month"], empty=False,
                                   clear="pointerout")
    sh_tips = [alt.Tooltip("month:T", title="12 months to", format="%B %Y")] + [
        alt.Tooltip(field=c, type="quantitative", title=c, format=".1%")
        for c in ["Share of placed ads", "Lowest possible (every unplaced ad in a capital)"]]
    sh_color = alt.Color("series:N", legend=alt.Legend(orient="top", title=None, symbolType="stroke",
                                                       labelLimit=0),
                         scale=alt.Scale(domain=list(sh.columns[1:]), range=[BLUE, MUTED]))
    sh_base = alt.Chart(sh_long).encode(x=alt.X("month:T", title=None),
                                        y=alt.Y("share_pct:Q", title="Regional share (%)",
                                                scale=alt.Scale(zero=False)), color=sh_color)
    st.subheader("Regional Australia's share of job ads (rolling 12 months)")
    st.altair_chart(alt.layer(
        # lower bound first, so the share line sits on top where the two are equal (before 2019)
        sh_base.mark_line(strokeWidth=2).transform_filter(alt.datum.series != "Share of placed ads"),
        sh_base.mark_line(strokeWidth=2).transform_filter(alt.datum.series == "Share of placed ads"),
        alt.Chart(sh).mark_rule(color=MUTED).encode(
            x="month:T", opacity=alt.condition(sh_hover, alt.value(0.8), alt.value(0)),
            tooltip=sh_tips).add_params(sh_hover),
        sh_base.mark_point(size=64, filled=True).transform_filter(sh_hover),
    ).properties(height=260), width="stretch", theme=None)

    st.subheader("The 37 IVI regions")
    st.caption("Regions are compared with each other, never with the national total: about 3% of "
               "ads aren't placed in any region. \"Capital\" means the 8 IVI regions that contain a "
               "capital (Canberra & ACT is the whole territory).")
    c1, c2, c3, c4 = st.columns(4)
    r_area = c1.selectbox("Area", [None, "capital", "regional"], key="rg_area",
                          format_func=lambda x: {None: "All regions", "capital": "Capital-city regions",
                                                 "regional": "Regional areas"}[x])
    r_state = c2.selectbox("State or territory", B.STATES, key="rg_state",
                           format_func=lambda s: "All states" if s == "AUST" else B.STATE_NAMES[s])
    r_sort = c3.selectbox("Sort by", list(B.SORTS), index=5, key="rg_sort")
    r_vs = c4.radio("Chart shows", ["Against 2019", "On the year"], key="rg_vs")
    reg = B.regions(t, r_area, r_state, r_sort)
    area_color = alt.Color("area:N", scale=alt.Scale(domain=["capital", "regional"], range=[BLUE, ORANGE]),
                           legend=alt.Legend(orient="top", title=None, labelExpr=(
                               "datum.label == 'capital' ? 'Capital-city region' : 'Regional area'")))
    rcol = "vs_2019" if r_vs == "Against 2019" else "yoy"
    st.altair_chart(change_bars(
        reg, "region", rcol, "Change in job ads a month (%)",
        [alt.Tooltip("region:N", title="Region"), alt.Tooltip("state:N", title="State"),
         alt.Tooltip("pct:Q", title="Change (%)", format="+.1f"),
         alt.Tooltip("now:Q", title="Ads a month", format=",.0f")], color=area_color),
        width="stretch", theme=None)
    st.dataframe(pct_cols(reg, ["yoy", "vs_2019", "latest_yoy"])[
        ["region", "state", "area", "now", "change", "yoy", "vs_2019", "latest_yoy"]],
        hide_index=True, width="stretch",
        column_config={"region": "Region", "state": "State", "area": "Area",
                       "now": st.column_config.NumberColumn("Ads a month", format="%,.0f"),
                       "change": st.column_config.NumberColumn("Change (ads a month)", format="%+,.0f"),
                       "yoy": st.column_config.NumberColumn("On the year", format="%+.1f%%"),
                       "vs_2019": st.column_config.NumberColumn("Vs 2019", format="%+.1f%%"),
                       "latest_yoy": st.column_config.NumberColumn("Latest 3 months vs a year ago",
                                                                   format="%+.1f%%")})

    st.subheader("What one region is hiring for")
    c1, c2 = st.columns(2)
    region_names = sorted(t["ivi_regions"]["region"])
    g_region = c1.selectbox("Region", region_names, key="rg_pick",
                            index=region_names.index(reg["region"].iloc[0]) if len(reg) else 0)
    g_sort = c2.selectbox("Sort groups by", ["Most ads", "Most over-represented", "Fastest rising on the year",
                                             "Most ads gained", "Most ads lost"], key="rg_gsort")
    grp = B.region_groups(t, g_region, g_sort)
    st.dataframe(pct_cols(grp, ["yoy", "vs_2019"])[
        ["group_title", "now", "change", "yoy", "vs_2019", "lq"]],
        hide_index=True, width="stretch", height=320,
        column_config={"group_title": "Occupation group (2-digit ANZSCO)",
                       "now": st.column_config.NumberColumn("Ads a month", format="%,.0f"),
                       "change": st.column_config.NumberColumn("Change (ads a month)", format="%+,.0f"),
                       "yoy": st.column_config.NumberColumn("On the year", format="%+.1f%%"),
                       "vs_2019": st.column_config.NumberColumn("Vs 2019", format="%+.1f%%"),
                       "lq": st.column_config.NumberColumn(
                           "Location quotient", format="%.2f×",
                           help="How much more common this group is in the region than across all "
                                "regions: 2.00× means twice as common. Blank at 20 ads a month or fewer.")})
    st.caption("A blank rate or location quotient (shown as None) means the base had 20 ads a "
               "month or fewer. One large employer can move a small region's figures; check the "
               "monthly series below before acting on a jump.")
    reg_w, rg_w = region_series()
    g_pick = st.selectbox("Monthly series for", [None] + list(grp["anzsco_code"]), key="rg_series",
                          format_func=lambda c: f"All ads in {g_region}" if c is None else
                          dict(zip(grp["anzsco_code"], grp["group_title"]))[c])
    srow = reg_w.loc[g_region] if g_pick is None else rg_w.loc[(g_region, g_pick)]
    base19 = srow[[f"2019-{m:02d}" for m in range(1, 13)]].mean()
    st.altair_chart(trend_chart(B.monthly(srow, "2015-01"), base19, height=240),
                    width="stretch", theme=None)

# ---------------------------------------------------------------- SA4 areas
with tab_sa4:
    st.info("These 50 areas (8 greater capital cities and 42 regional SA4s) are shown year on year "
            "only. JSA built this file in 2024 and backcast it to 2019, and in 2019 its areas held "
            "between 98.8% and 100.7% of national ads, so a comparison with 2019 wouldn't be "
            "reliable here.")
    c1, c2, c3 = st.columns(3)
    s_state = c1.selectbox("State or territory", B.STATES, key="sa_state",
                           format_func=lambda s: "All states" if s == "AUST" else B.STATE_NAMES[s])
    s_level = c2.selectbox("Areas", [None, "GCCSA", "SA4"], key="sa_level",
                           format_func=lambda x: {None: "All areas", "GCCSA": "Greater capital cities",
                                                  "SA4": "Regional SA4s"}[x])
    s_sort = c3.selectbox("Sort by", [s for s in B.SORTS if B.SORTS[s][0] != "vs_2019"], index=1,
                          key="sa_sort")
    sd = B.sa4(t, s_state, s_level, s_sort)
    lvl_color = alt.Color("region_level:N", scale=alt.Scale(domain=["GCCSA", "SA4"], range=[BLUE, ORANGE]),
                          legend=alt.Legend(orient="top", title=None, labelExpr=(
                              "datum.label == 'GCCSA' ? 'Greater capital city' : 'Regional SA4'")))
    st.altair_chart(change_bars(
        sd, "region_name", "yoy", "Change in job ads a month on the year before (%)",
        [alt.Tooltip("region_name:N", title="Area"), alt.Tooltip("state:N", title="State"),
         alt.Tooltip("pct:Q", title="Change (%)", format="+.1f"),
         alt.Tooltip("now:Q", title="Ads a month", format=",.0f")], color=lvl_color),
        width="stretch", theme=None)
    st.dataframe(pct_cols(sd, ["yoy", "latest_yoy"])[
        ["region_name", "state", "region_level", "now", "change", "yoy", "latest_yoy"]],
        hide_index=True, width="stretch",
        column_config={"region_name": "Area", "state": "State", "region_level": "Type",
                       "now": st.column_config.NumberColumn("Ads a month", format="%,.0f"),
                       "change": st.column_config.NumberColumn("Change (ads a month)", format="%+,.0f"),
                       "yoy": st.column_config.NumberColumn("On the year", format="%+.1f%%"),
                       "latest_yoy": st.column_config.NumberColumn("Latest 3 months vs a year ago",
                                                                   format="%+.1f%%")})

# ---------------------------------------------------------------- About
with tab_about:
    st.markdown(f"""
**Source.** Jobs and Skills Australia, Internet Vacancy Index, release to {month_label(END)}.
© Commonwealth of Australia, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The figures are my own analysis of
that data, not JSA's.

**What the numbers are.** Online job ads on SEEK, CareerOne and Workforce Australia, as 3-month
averages. They miss word-of-mouth hiring and employer websites, count a multi-position ad once,
and lean towards higher-skilled roles. Read them as a demand signal, not a count of jobs.

**Rules this dashboard follows** (from Part 1 of the project):

1. Changes are measured on 12-month averages (or the same 3 months a year apart), never month on
   month, because the raw series falls about 18% from October to January every year.
2. No growth rate on a base of 20 ads a month or fewer, and rate rankings leave those rows out:
   unfiltered, every top-10 riser started from under one ad a month.
3. Totals are JSA's published totals, which include 7 suppressed occupations. They're never
   rebuilt by adding up occupations.
4. Regions are compared with regions. About 3% of ads aren't placed in any region, so a region
   against the national total would show a "lag" that's really coding.
5. The GCCSA/SA4 areas are year on year only.

The full method and findings are in the project's reports: source profile, occupation demand and
regional demand (`results/*.md` in the repository).
""")
