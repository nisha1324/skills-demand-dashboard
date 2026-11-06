# Which jobs and regions are hiring in Australia? (skills-demand dashboard)

> **Status: in progress, Part 1 of 5 done** (source profile). Next: occupation demand (Part 2),
> regional demand (Part 3), a Streamlit dashboard (Part 4), then CI and the final write-up (Part 5).

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

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.download_data     # optional: fetches the 4 workbooks (12 MB) into data/raw/
python -m scripts.build_snapshot    # optional: rebuilds data/*.csv.gz from them
python -m scripts.profile_source    # Part 1 report and charts, from the committed snapshot
pytest
```

The committed snapshot is enough to rerun every report; the download is only needed to rebuild it.

## Project layout

```
scripts/download_data.py    fetch the workbooks (official site first, archive fallback, pinned SHA-256)
scripts/build_snapshot.py   workbooks -> tidy data/*.csv.gz + SNAPSHOT.json
scripts/profile_source.py   Part 1 report: results/SOURCE_PROFILE.md, charts 01-04, CSVs
ivi/load.py                 load the snapshot with the right types (codes stay text)
ivi/profile.py              the Part 1 checks, as small testable functions
tests/                      unit tests on hand-made data + checks on the committed snapshot
```

## Data credit

Contains data from the Jobs and Skills Australia Internet Vacancy Index, © Commonwealth of
Australia, licensed under CC BY 4.0. The figures here are my own analysis of that data, not JSA's.
