"""Part 1, the TL;DR, recommendations, limitations and Part 5 of the README.

Part 1's figures must be in the generated source profile. The summary sections may only repeat
figures that Parts 1-4 already state (and those are tied to the data by the other README tests),
and each repeated figure must sit next to the same subject it has there.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
PROFILE = (ROOT / "results" / "SOURCE_PROFILE.md").read_text()
CI = (ROOT / ".github" / "workflows" / "ci.yml").read_text()

NUMBER = re.compile(r"[−+]?\d+(?:,\d{3})*(?:\.\d+)?[%×]?")


def flat(text):
    return re.sub(r"\s+", " ", text)


def section(heading, end="\n## "):
    return README.split(heading, 1)[1].split(end, 1)[0]


def tokens(text):
    # Whole figures only, so "1.3%" can't hide inside "21.3%". A leading "+" is dropped
    # because the parts sometimes write "21.2% above 2019" for "+21.2% on 2019".
    return {t.lstrip("+") for t in NUMBER.findall(text)}


PARTS_1_TO_4 = section("## Part 1:", "## Part 5:")
SUMMARIES = {
    "TL;DR": section("## TL;DR"),
    "Part 5": section("## Part 5:"),
    "Recommendations": section("## Recommendations"),
    "Limitations": section("## Limitations"),
}


def test_every_part1_figure_is_in_the_source_profile():
    # Written differently in the report: its gap table has "−1.13%" (published minus total),
    # and its text gives the range as "99.7% to 99.9%".
    worded_differently = {"1.13%", "99.7"}
    missing = tokens(section("## Part 1:")) - tokens(PROFILE) - worded_differently
    assert not missing, sorted(missing)
    assert "−1.13%" in PROFILE and "99.7% to 99.9%" in PROFILE


@pytest.mark.parametrize("name", SUMMARIES)
def test_summary_figures_repeat_figures_from_parts_1_to_4(name):
    method = {"256"}  # SHA-256
    missing = tokens(SUMMARIES[name]) - tokens(PARTS_1_TO_4) - method
    assert not missing, (name, sorted(missing))


# (phrase in a summary section, phrase in Parts 1-4 that gives the same figure the same subject)
SAME_SUBJECT = [
    ("TL;DR", "averaged 209,655 a month in the 12 months to August 2026: −3.3% on the year before, still +21.2% on 2019",
     "The 12 months to August 2026 averaged 209,655 ads a month, −3.3% on the 12 months before but still 21.2% above 2019"),
    ("TL;DR", "The latest 3 months are +0.9% on a year earlier", "the latest 3 months are +0.9% on a year earlier"),
    ("TL;DR", "Regional areas are +67.1% on 2019 against +4.9% for the capital-city regions",
     "+67.1% on 2019, against +4.9% for the capital-city regions"),
    ("TL;DR", "now hold 30.1% of placed ads (21.2% in 2019)", "holds 30.1% of placed ads, up from 21.2% in 2019"),
    ("TL;DR", "GPs and resident medical officers added 1,362 ads a month (+36.4%)",
     "General practitioners and resident medical officers added 1,362 ads a month (+36.4%)"),
    ("TL;DR", "47.3% of ads for medical practitioners and nurses are now regional",
     "47.3% of ads for medical practitioners and nurses are now regional"),
    ("TL;DR", "rose +27.4% on the year while the capitals' were flat (−0.2%)",
     "rose +27.4% on the year while the capitals' were flat (−0.2%)"),
    ("TL;DR", "22 big occupations are below 2019 and still falling", "22 big occupations are below 2019 and still falling"),
    ("TL;DR", "the largest being advertising and sales managers, accountants and software programmers",
     "the largest being advertising and sales managers, accountants and software programmers"),
    ("TL;DR", "software programmers (−46.6% on 2019)", "software programmers −46.6%"),
    ("TL;DR", "ICT professional ads stay in the capitals: only 5.7% are regional",
     "ICT professional ads stay in the capitals: only 5.7% are regional"),
    ("Recommendations", "regional areas gained 362 ads a month while the capitals lost 7,253",
     "the capitals lost 7,253 ads a month (−4.8%) while regional areas gained 362 (+0.6%)"),
    ("Recommendations", "Tamworth and North West NSW (+23.3%), Dubbo & Western NSW (+12.5%) and NSW North Coast (+8.5%)",
     "Tamworth and North West NSW (+23.3%), Dubbo & Western NSW (+12.5%) and NSW North Coast (+8.5%)"),
    ("Recommendations", "Registered nurses (6,883 ads a month, +6.1%), GPs (5,105, +36.4%) and electricians (3,064, +9.3%)",
     "registered nurses (6,883 ads a month, +6.1%), GPs (5,105, +36.4%), electricians (3,064, +9.3%)"),
    ("Recommendations", "medical practitioners and nurses are 2.7× as common in ads as across all regions",
     "2.7× as common as across all regions"),
    ("Recommendations", "Child carers (−12.9%)", "child carers (−12.9%)"),
    ("Recommendations", "software programmers are −46.6% on 2019 and ICT business and systems analysts −41.0%",
     "software programmers −46.6%, ICT business and systems analysts −41.0%"),
    ("Recommendations", "General clerks (−806 a month), waiters (−534), child carers (−490) and software programmers (−460)",
     "general clerks (−806), waiters (−534), child carers (−490) and software programmers (−460)"),
    ("Recommendations", "Machinery operators and drivers is the only major group up on the year (+6.6%, and +62.0% on 2019)",
     "Machinery operators and drivers is the only major group up on the year (+6.6%) and the furthest above 2019 (+62.0%)"),
    ("Recommendations", "Canberra (−21.4%), Sydney (−18.5%) and Melbourne (−15.3%) have fewer",
     "Canberra & ACT (−21.4%), Sydney (−18.5%) and Melbourne (−15.3%)"),
    ("Recommendations", "GPs at 4.8× and vets at 5.1× their 2019 level", "GPs 4.8×, vets 5.1×"),
    ("Recommendations", "from 120 to 350 a month", "went from 120 to 350 a month"),
    ("Limitations", "7 occupations are suppressed (1.13% of ads in August 2026)",
     "The published occupations miss 1.13% of ads in August 2026"),
    ("Limitations", "5 occupations with 100+ ads a month are at least 3 times their 2019 level",
     "5 occupations with 100+ ads a month are at least 3 times their 2019 level"),
]


@pytest.mark.parametrize("name, summary, part", SAME_SUBJECT)
def test_summary_figures_keep_their_subject(name, summary, part):
    assert flat(summary) in flat(SUMMARIES[name])
    assert flat(part) in flat(PARTS_1_TO_4)


def test_rules_stated_in_the_summary_match_the_code():
    from ivi import demand as D
    from ivi import regions as G
    assert D.FLOOR == 20.0
    assert "base of 20 ads a month or fewer" in flat(SUMMARIES["TL;DR"])
    assert "a base of exactly 20 gets no rate" in flat(SUMMARIES["Part 5"])
    assert "no rates on 20 ads a month or fewer" in flat(SUMMARIES["Recommendations"])
    assert len(G.CAPITALS) == 8 and "Hobart's region takes in the south-east" in flat(SUMMARIES["Limitations"])


def test_ci_reruns_every_report_in_how_to_run():
    how_to_run = section("## How to run")
    reports = re.findall(r"python -m (scripts\.\w+)\s+# Part \d report", how_to_run)
    assert len(reports) == 3
    for module in reports:
        assert f"python -m {module}\n" in CI
    assert "test -z \"$(git status --porcelain)\"" in CI and "pytest" in CI
    assert "actions/workflows/ci.yml/badge.svg" in README


def test_lock_file_pins_every_requirement():
    def names(path, sep):
        out = set()
        for line in (ROOT / path).read_text().splitlines():
            line = line.split("#")[0].strip()
            if line:
                out.add(re.split(sep, line)[0].strip().lower().replace("_", "-"))
        return out
    lock = (ROOT / "requirements-lock.txt").read_text()
    assert all("==" in l for l in lock.splitlines() if l and not l.startswith("#"))
    assert names("requirements.txt", r"[<>=!~]") <= names("requirements-lock.txt", "==")
