# Which jobs and regions are hiring in Australia? (skills-demand dashboard)

[![CI](https://github.com/nisha1324/skills-demand-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/nisha1324/skills-demand-dashboard/actions/workflows/ci.yml)

> **Status: complete.** Source profile, occupation demand, regional demand, a Streamlit dashboard,
> and CI that reruns every report on each push. Built on the August 2026 IVI release.

## TL;DR

- **Hiring has cooled but not collapsed.** Online job ads averaged 209,655 a month in the 12 months
  to August 2026: −3.3% on the year before, still +21.2% on 2019. The latest 3 months are +0.9% on a
  year earlier, so the fall has stopped for now.
- **Demand has moved to regional Australia.** Regional areas are +67.1% on 2019 against +4.9% for
  the capital-city regions, and now hold 30.1% of placed ads (21.2% in 2019). The only regions below
  2019 are Canberra & ACT, Sydney and Melbourne.
- **Health is the growth story, and it's regional.** GPs and resident medical officers added 1,362
  ads a month (+36.4%). 47.3% of ads for medical practitioners and nurses are now regional, and
  those regional ads rose +27.4% on the year while the capitals' were flat (−0.2%).
- **Sales-management, accounting and ICT roles are the weak side.** 22 big occupations are below
  2019 and still falling, the largest being advertising and sales managers, accountants and
  software programmers (−46.6% on 2019). ICT professional ads stay in the capitals: only 5.7% are
  regional.
- **A dashboard with the rules built in.** A Streamlit app answers these questions by state, region
  and occupation. It uses 12-month averages, never ranks a base of 20 ads a month or fewer, and
  compares regions only with regions, so the misleading views Part 1 warns about aren't on offer.

Recruiters, training providers and workforce planners all need the same answer: **which
occupations are employers advertising for, where, and is that demand rising or cooling?** A
training provider deciding which courses to run in Ballarat, or a recruitment agency deciding where
to open a desk, can't wait for the five-yearly Census.

Jobs and Skills Australia (JSA) publishes a monthly count of online job ads, the **Internet Vacancy
Index (IVI)**, by occupation, state and region, back to 2006. This project turns it into tested
tables, answers those questions, and ends with a dashboard a non-analyst can use.

It's easy to misread, though. Before ranking anything, Part 1 checks what the numbers mean.

## Data

| | |
|---|---|
| Dataset | [Internet Vacancy Index](https://www.jobsandskills.gov.au/data/internet-vacancy-index), August 2026 release (published 23 September 2026) |
| Publisher | Jobs and Skills Australia (Australian Government) |
| Licence | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), per JSA's copyright page. © Commonwealth of Australia, Jobs and Skills Australia. |
| Files used | 4-digit ANZSCO occupations by state (Mar 2006 on); 2-digit occupation groups by 37 IVI regions (May 2010 on) and by GCCSA/SA4 area (Jan 2019 on); skill level by state, trend and seasonally adjusted (Jan 2006 on) |
| In this repo | `data/*.csv.gz`: the four workbooks melted to one row per series per month (1.5 million rows, about 9 MB). `data/SNAPSHOT.json` records the source and output SHA-256. |

No key or sign-up is needed. `scripts/download_data.py` tries jobsandskills.gov.au first. That site
drops scripted connections (it did from the machine this was built on), so each file falls back to
its Internet Archive copy, fetched byte for byte. The SHA-256 of every file is pinned, so a changed
file stops the run instead of quietly changing the results.

The IVI counts **online job ads** on SEEK, CareerOne and Workforce Australia, not vacancies or
hires. This README always says "job ads".

## Part 1: what the numbers mean

Full report: [`results/SOURCE_PROFILE.md`](results/SOURCE_PROFILE.md) (generated; every figure comes
from the snapshot).

**The snapshot matches JSA's own release.** The seasonally adjusted count rose by 559 ads (+0.3%) to
212,401 in August 2026; JSA's release says "increased by 0.3% (or 560 job advertisements) … to
stand at 212,400".

**Demand is cooling from a high level.** The 12 months to August 2026 averaged 209,655 ads a month,
−3.3% on the 12 months before but still 21.2% above 2019. It isn't a record: the seasonally adjusted
peak was 306,851 in April 2008, and August 2026 is 30.8% below it.

![National job ads](results/charts/01_national_ads.png)

Six things would mislead a naive dashboard. Each one sets a rule for the rest of the project:

| Trap | What the data shows | Rule from here on |
|---|---|---|
| Occupation and regional data are raw 3-month averages, and they're seasonal | Against the seasonally adjusted level (2010-2019), the raw figure runs −10.9% in the 3 months ending January and +8.3% in those ending October | Compare the same month a year apart, or 12-month averages. Never month on month. |
| Adjusted series don't add up | In August 2026 the five seasonally adjusted skill levels sum to 212,839, against a total of 212,401 | Shares and mixes use raw 3-month averages only |
| 7 occupations are suppressed (no figures at all) | The published occupations miss 1.13% of ads in August 2026; the gap rose from 0.25% (2006) to 1.06% (2026 so far) | Shares use the published total, and say so. Totals are never rebuilt by adding occupations. |
| About 3% of ads aren't placed in any region | Regions held 99.7-99.9% of ads in 2011-2017 but 96.9% in August 2026. So regions grew 21.4% from 2019 against 24.8% nationally. About 3 points of that "regional lag" is coding, not demand. | Compare regions with each other, never with the national total. Keep the two regional geographies apart. |
| Most state × occupation cells are small, and small cells are noisy | 58% of the 2,808 cells have 20 or fewer ads a month. Year on year, 46% of cells with up to 5 ads moved by more than 50%, against 3% of cells with 20 to 50. | Growth rankings only include cells with more than 20 ads a month in the base period |
| Job ads aren't jobs | IVI misses word-of-mouth hiring and employer sites, counts a multi-position ad once, and leans towards higher-skilled roles | Results say "online job ads", a demand signal |

| | |
|---|---|
| ![Seasonality](results/charts/02_seasonality.png) | ![Regional coverage](results/charts/03_regional_coverage.png) |

**So what for the business?** A dashboard built straight from these files would show an 18% "slump"
from October to January every year, credit regions with a lag that is really a coding change, and
top its "fastest growing" list with noise: unfiltered, the top 10 risers all started from 0.67 ads a
month or fewer, led by film and TV directors in South Australia (0.33 to 6.00 ads, +1700%). With the
20-ad floor, the top riser is midwives in Queensland (24.67 to 49.33 ads a month, +100%), a change
worth looking into. Part 1's rules remove all three problems before any ranking is shown.

## Part 2: which occupations are in demand

Full report: [`results/OCCUPATION_DEMAND.md`](results/OCCUPATION_DEMAND.md) (generated). Every
change is measured on 12-month averages (a full year, so the seasonal swing cancels) against the
year before and against 2019, plus the latest 3 months against the same 3 months a year earlier.
No growth rate is shown on a base of 20 ads a month or fewer.

**The fall has stopped, for now.** Ads averaged 209,655 a month in the 12 months to August 2026,
−3.3% on the year before. But the latest 3 months are +0.9% on a year earlier, and JSA's seasonally
adjusted August figure is +4.8% on August 2025.

**One occupation group grew.** Machinery operators and drivers is the only major group up on the
year (+6.6%) and the furthest above 2019 (+62.0%). Clerical and administrative workers are barely
above 2019 (+5.2%).

![Major groups](results/charts/05_major_groups.png)

**Doctors and nurses cushioned the fall.** General practitioners and resident medical officers
added 1,362 ads a month (+36.4%); without them the fall would have been 8,413 a month, not 7,051.
Registered nurses (+397), electricians (+260) and nursing support workers (+236) came next. The
biggest falls were general clerks (−806), waiters (−534), child carers (−490) and software
programmers (−460).

![Where the change came from](results/charts/06_contributions.png)

**A demand matrix for the 108 occupations with 500+ ads a month** sorts each one by two questions:
up on the year, and above 2019?

| Demand state | Occupations | Ads a month | Largest |
|---|---|---|---|
| Growing, above 2019 | 32 | 51,472 | Registered Nurses, General Practitioners and Resident Medical Officers, Other Miscellaneous Labourers, Electricians |
| Cooling, still above 2019 | 52 | 86,868 | General Clerks, Sales Assistants (General), Retail Managers, Aged and Disabled Carers |
| Rising, still below 2019 | 2 | 4,238 | Construction Managers, Financial Investment Advisers and Managers |
| Shrinking, below 2019 | 22 | 31,307 | Advertising and Sales Managers, Accountants, Software and Applications Programmers, Human Resource Professionals |

![Demand matrix](results/charts/07_demand_matrix.png)

**States split sharply.** SA is +82.5% on 2019; VIC (−4.1%) and ACT (−21.4%) are below it, and ACT
fell most on the year (−15.8%). Machinery operators and drivers rose in 6 of the 8 states, most of
all in SA (+18%) and WA (+14%).

![States](results/charts/08_state_heatmap.png)

**So what for the business?**

- **Recruiters:** the strongest big markets include registered nurses (6,883 ads a month, +6.1%), GPs
  (5,105, +36.4%), electricians (3,064, +9.3%) and truck drivers (2,807, +2.0%). General clerks,
  waiters and child carers are losing the most ads, so placement volumes there are most at risk.
- **Training providers:** health, care and electrical courses feed occupations that are all above
  2019, though child carers (−12.9%) and aged and disabled carers (−3.1%) are cooling. ICT courses
  face a market far below 2019: software programmers −46.6%, ICT business and systems analysts
  −41.0%.
- **Workforce planners:** 22 big occupations are below 2019 and still falling, the largest being
  advertising and sales managers, accountants and software programmers. Don't plan on them
  bouncing back to 2019 levels.
- **A caution:** 5 occupations with 100+ ads a month are at least 3 times their 2019 level (GPs
  4.8×, vets 5.1×). Some are real shortages, but a jump that big could also be a change in how ads
  are coded. Check the monthly series before acting on one.

## Part 3: where the ads are

Full report: [`results/REGIONAL_DEMAND.md`](results/REGIONAL_DEMAND.md) (generated). It follows Part
1's rules for regions: regions are compared with each other, never with the national total; the 37
IVI regions (from October 2010) carry the comparison with 2019; the GCCSA/SA4 areas are used year
on year only. "Capital-city regions" are the 8 IVI regions that contain a capital.

**A shift to regional Australia, and it's still going.** The 29 regional areas averaged 61,229 ads
a month in the 12 months to August 2026, +67.1% on 2019, against +4.9% for the capital-city regions.
Regional Australia now holds 30.1% of placed ads, up from 21.2% in 2019. Over the last year the
capitals lost 7,253 ads a month (−4.8%) while regional areas gained 362 (+0.6%).

**It isn't a coding effect.** On average 6,013 ads a month aren't placed in any region. Even if every one
belonged to a capital, the regional share would be 29.2%, so unplaced ads can explain at most 0.8 of
the 8.8 points of shift. The share jumped in 2020, fell back to 25.6% in July 2022, then rose in 48
of the 49 months since.

![Regional share](results/charts/09_regional_share.png)

**Only three regions are below 2019, and all are capitals:** Canberra & ACT (−21.4%), Sydney
(−18.5%) and Melbourne (−15.3%). Every one of the 29 regional areas is above 2019, from Pilbara &
Kimberley (+18.0%) to Tamworth and North West NSW (+154.7%).

![Regions vs 2019](results/charts/10_regions_vs_2019.png)

**Health and care lead the move.** 47.3% of ads for medical practitioners and nurses are now
regional (38.3% in 2019). Regional ads for them rose +27.4% on the year while the capitals' were
flat (−0.2%): regional areas added 1,191 a month and the capitals lost 11. So the doctor and nurse
growth in Part 2 is a regional story. Carers and aides (41.8% regional, from 28.6%) and legal,
social and welfare professionals (39.1%, from 23.6%; +13.6% in the regions on the year, −8.8% in
the capitals) moved the same way. ICT professional ads stay in the capitals: only 5.7% are regional.

![Regional share by group](results/charts/11_group_regional_share.png)

**The year-on-year view agrees.** In the GCCSA/SA4 file the 8 greater capital cities are −4.6% on
the year and the 42 regional SA4s +0.4%. Regional NSW leads: 6 of the 10 fastest-growing SA4s are
in NSW, topped by New England and North West (+21.3%). The two geographies give the same direction
for all 8 capitals, at most 0.9 points apart.

![SA4 year on year](results/charts/12_sa4_year_on_year.png)

**So what for the business?**

- **Recruiters:** 3 in 10 placed ads are now outside the capitals, and that part of the market held
  up while the capitals fell. A desk that only covers the capitals is working the shrinking part.
  The fastest-growing big regional markets: Tamworth and North West NSW (+23.3%), Dubbo & Western
  NSW (+12.5%) and NSW North Coast (+8.5%).
- **Training providers:** health and care courses have a case for regional campuses or clinical
  placements. On the NSW North Coast, for example, medical practitioners and nurses have 541 ads a
  month, 2.7× as common as across all regions, and +62.0% on the year. ICT courses are a capital-city
  market.
- **Employers and workforce planners:** Canberra, Sydney and Melbourne have fewer ads than in 2019,
  so employers there compete with fewer other ads for staff. Every regional area has more ads than
  in 2019, so a regional employer should plan for more competition for the same local workers.
- **A caution:** single jumps can come from a few large employers. Tamworth's ads for medical
  practitioners and nurses went from 120 to 350 a month in a year; check the monthly series before
  acting on one. Use region figures to rank and compare places, not as exact counts.

## Part 4: the dashboard

`app/dashboard.py` is a Streamlit app that lets a recruiter, training provider or planner ask their
own version of these questions without reading the reports. It runs offline from the files in this
repo: the tables are the CSVs that Parts 2 and 3 wrote to `results/`, and the headline tiles and
monthly charts come from the committed snapshot through the same functions the reports use.

![Dashboard overview](docs/dashboard_overview.png)

| Tab | What it answers |
|---|---|
| Overview | How many ads a month, for Australia or any state, against the year before and 2019; the monthly series with the 2019 average marked; which of the 8 occupation groups are rising or falling |
| Occupations | All 351 published occupations, nationally or by state: filter by group, size or name, sort by size, growth or ads gained/lost, with a demand-matrix label for each. Pick one to see its monthly series. |
| Regions | Regional Australia's share of ads over time, the 37 IVI regions against 2019 or the year before, and what one region is hiring for (with location quotients and the monthly series) |
| SA4 areas | The 8 greater capital cities and 42 regional SA4s, year on year only |
| About the data | Source, licence, and the rules below |

**Part 1's rules are built in, not left to the user.** Growth rates are on 12-month averages, so the
summer dip never shows up as a slump in a ranking (charts draw the raw series lightly behind its
12-month average). No growth rate is shown on a base of 20 ads a month or fewer, and no location
quotient for a group that small; rate sorts leave those rows out instead of ranking them. Regions are compared
only with regions, and the SA4 tab has no 2019 option at all.

![Regions tab](docs/dashboard_regions.png)

**So what for the business?** A question that took a report section now takes a few filters. For
example, a training provider asking "which professional roles are growing in Queensland?" picks
Queensland, Professionals and "Fastest rising on the year" with at least 100 ads a month. The top
riser is primary school teachers, from 116 to 174 ads a month (+50.0%), but that's 7.9 times its
2019 level, so the drill-down chart is the next click before acting. The dashboard is built for
that habit: every ranking sits one click away from the monthly series behind it.

**Run it:** `streamlit run app/dashboard.py`, then open http://localhost:8501. To publish it,
create a free app on [Streamlit Community Cloud](https://share.streamlit.io) from this repo with
main file `app/dashboard.py` (it needs no secrets).

## Part 5: tests and CI

Every figure in this README and the reports is generated or checked by code:

- **Unit tests on hand-made data** for each measure: 12-month averages, the 20-ad floor (a base of
  exactly 20 gets no rate), the demand matrix, regional share, location quotients and the
  dashboard's filters and sorts.
- **Checks on the real snapshot:** occupation groups and states add up to their totals, capital
  plus regional areas make up all 37 IVI regions, location quotients average to 1, and the
  dashboard reproduces the reports' headline figures.
- **README tests:** the figures in Parts 1-4 are matched to the reports and CSVs. The TL;DR,
  recommendations and limitations may only repeat those figures, next to the same subject. So a
  typed-in number that drifts from the data fails the build.
- **Dashboard smoke tests:** Streamlit's AppTest runs the app headless, opens every tab and works
  its filters (state, occupation group, size, search, region, sort).

On every push, [GitHub Actions](.github/workflows/ci.yml) installs the exact package versions in
`requirements-lock.txt`, reruns the three reports from the committed snapshot (no network needed),
fails if any committed report, CSV or chart changes by a single byte, then runs the test suite.

## Recommendations

In priority order, each with the person who would act on it:

1. **Grow regional desks, starting with health and care.** *(Recruitment agency, business
   development lead.)* 3 in 10 placed ads are outside the capitals, and over the last year regional
   areas gained 362 ads a month while the capitals lost 7,253. Regional ads for medical
   practitioners and nurses rose +27.4%. The fastest-growing big regional markets are Tamworth and
   North West NSW (+23.3%), Dubbo & Western NSW (+12.5%) and NSW North Coast (+8.5%).
2. **Put health, care and electrical courses first, with regional placements.** *(Training
   provider, course planning.)* Registered nurses (6,883 ads a month, +6.1%), GPs (5,105, +36.4%)
   and electricians (3,064, +9.3%) are big and growing. On the NSW North Coast, medical
   practitioners and nurses are 2.7× as common in ads as across all regions. Child carers (−12.9%)
   are the exception to watch.
3. **Don't size ICT, accounting or sales-management intakes on 2019 demand.** *(Training provider
   and workforce planner.)* These are among the 22 big occupations below 2019 and still falling;
   software programmers are −46.6% on 2019 and ICT business and systems analysts −41.0%. ICT is a
   capital-city market, with only 5.7% of ads regional.
4. **Move capital-city recruiting effort away from the biggest losers.** *(Recruitment agency,
   capital-city desks.)* General clerks (−806 a month), waiters (−534), child carers (−490) and
   software programmers (−460) lost the most ads. Machinery operators and drivers is the only
   major group up on the year (+6.6%, and +62.0% on 2019).
5. **Plan regional hiring for more competition, capital-city hiring for less.** *(Employers' HR
   and workforce planning.)* Every regional area has more ads than in 2019; Canberra (−21.4%),
   Sydney (−18.5%) and Melbourne (−15.3%) have fewer. A regional employer is advertising alongside
   more other ads for the same local workers.
6. **Report the IVI with Part 1's rules, and check big jumps before acting.** *(Analytics team.)*
   Use 12-month averages or the same month a year apart, no rates on 20 ads a month or fewer, and
   regions compared only with regions. Jumps like GPs at 4.8× and vets at 5.1× their 2019 level, or
   Tamworth's doctor and nurse ads going from 120 to 350 a month, may be coding changes or a few
   employers: open the monthly series first. The dashboard makes that one click.

## Limitations

- **Job ads are a demand signal, not vacancies or hires.** The IVI covers ads on SEEK, CareerOne and
  Workforce Australia. It misses word-of-mouth hiring and employer sites, counts a multi-position ad
  once, and leans towards higher-skilled roles.
- **One release.** Everything is from the August 2026 release, pinned by SHA-256. Newer months need a
  new download, new pins and a rerun; the official site drops scripted connections, so the download
  falls back to Internet Archive copies, which can lag a release behind.
- **Raw 3-month averages below the national level.** Occupation and region series aren't seasonally
  adjusted, which is why every comparison is on 12-month averages or a year apart.
- **Gaps in the published data.** 7 occupations are suppressed (1.13% of ads in August 2026), and
  about 3% of ads aren't placed in any region. Region figures are for ranking and comparing places,
  not exact counts.
- **IVI regions aren't ABS capital-city boundaries.** Hobart's region takes in the south-east, and
  Canberra's is the whole territory.
- **Large jumps aren't verified.** 5 occupations with 100+ ads a month are at least 3 times their 2019
  level. The data can't say whether that's a shortage or a coding change.
- **What, not why.** The analysis shows where ads moved. It doesn't test causes such as migration,
  remote work or health funding.
- **The dashboard runs locally.** It isn't deployed yet; publishing it needs a (free) Streamlit
  Community Cloud sign-in.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.download_data     # optional: fetches the 4 workbooks (12 MB) into data/raw/
python -m scripts.build_snapshot    # optional: rebuilds data/*.csv.gz from them
python -m scripts.profile_source    # Part 1 report and charts, from the committed snapshot
python -m scripts.occupation_demand # Part 2 report, charts and CSVs
python -m scripts.regional_demand   # Part 3 report, charts and CSVs
streamlit run app/dashboard.py      # Part 4 dashboard
pytest
```

The committed snapshot is enough to rerun every report; the download is only needed to rebuild it.

For byte-identical charts and CSVs (what CI checks), install `requirements-lock.txt` instead: it pins
the exact versions the committed outputs were made with, on Python 3.12.

## Project layout

```
scripts/download_data.py    fetch the workbooks (official site first, archive fallback, pinned SHA-256)
scripts/build_snapshot.py   workbooks -> tidy data/*.csv.gz + SNAPSHOT.json
scripts/profile_source.py   Part 1 report: results/SOURCE_PROFILE.md, charts 01-04, CSVs
scripts/occupation_demand.py  Part 2 report: results/OCCUPATION_DEMAND.md, charts 05-08, CSVs
scripts/regional_demand.py  Part 3 report: results/REGIONAL_DEMAND.md, charts 09-12, CSVs
ivi/load.py                 load the snapshot with the right types (codes stay text)
ivi/profile.py              the Part 1 checks, as small testable functions
ivi/demand.py               the Part 2 measures (12-month averages, the 20-ad floor, demand matrix)
ivi/regions.py              the Part 3 measures (capital vs regional, location quotient, SA4 year on year)
ivi/dashboard.py            the Part 4 data layer (filters, sorts with the 20-ad floor, region views)
app/dashboard.py            the Streamlit dashboard (Part 4)
docs/                       dashboard screenshots
.github/workflows/ci.yml    CI: rerun the 3 reports, fail on any change, then pytest
requirements-lock.txt       exact package versions for CI (requirements.txt has the ranges)
tests/                      unit tests on hand-made data, checks on the committed snapshot, app smoke tests
```

## Data credit

Contains data from the Jobs and Skills Australia Internet Vacancy Index, © Commonwealth of
Australia, licensed under CC BY 4.0. The figures here are my own analysis of that data, not JSA's.
