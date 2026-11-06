"""Download the Jobs and Skills Australia Internet Vacancy Index (IVI) workbooks into data/raw/.

Source: Jobs and Skills Australia (JSA), "Internet Vacancy Index",
https://www.jobsandskills.gov.au/data/internet-vacancy-index
Release used: August 2026 data, published 23 September 2026.
Licence: Creative Commons Attribution 4.0 International (JSA's copyright page:
"All content on the Jobs and Skills Australia website is provided under a
Creative Commons Attribution 4.0 International Licence"). Attribution:
(c) Commonwealth of Australia, Jobs and Skills Australia.

Four workbooks are used:
- ANZSCO 4-digit occupations by state and territory (3-month averages, Mar 2006 on)
- ANZSCO 2-digit occupations by the 37 IVI regions (3-month averages, May 2010 on)
- ANZSCO 2-digit occupations by GCCSA and SA4 regions (3-month averages, Jan 2019 on)
- ANZSCO skill level by state and territory (trend and seasonally adjusted, Jan 2006 on)

The official jobsandskills.gov.au links come first. That site drops scripted
connections (it did from the machine this was built on: HTTP/2 resets and
HTTP/1.1 timeouts), so each file falls back to its Internet Archive capture,
fetched with the `id_` flag so the archive returns the original bytes. Every
file's SHA-256 is pinned: a file that differs stops the download instead of
silently changing the analysis.
"""
from pathlib import Path
import hashlib
import time
import urllib.parse
import urllib.request

JSA = "https://www.jobsandskills.gov.au/sites/default/files/2026-09"
WAYBACK = "https://web.archive.org/web"

# local name -> (expected SHA-256, official file name, Internet Archive timestamp)
FILES = {
    "ivi_anzsco4_states_aug2026.xlsx": (
        "810ca8800ff59ec9c58ec86ebda6808c668c2e69bf7de5c55905e49475453b55",
        "internet_vacancies_anzsco4_occupations_states_and_territories_-_august_2026.xlsx",
        "20261002232008",
    ),
    "ivi_anzsco2_ivi_regions_aug2026.xlsx": (
        "c2777b3a03e0186a790fd4889a9c5c5d0e0c11b2bb58152f4ec67e133ff39735",
        "internet_vacancies_anzsco2_occupations_ivi_regions_-_august_2026.xlsx",
        "20261019074733",
    ),
    "ivi_anzsco2_gccsa_sa4_aug2026.xlsx": (
        "6790f2354a64f69c52a9ad6a9173fe5b7aca43902c626226498754780c0078a1",
        "internet_vacancies_anzsco2_occupations_gccsa_and_sa4_regions_-_august_2026.xlsx",
        "20261009104439",
    ),
    "ivi_skill_level_states_aug2026.xlsx": (
        "26d4dad65384308011fe9f0bf9c08fccbbefe75d05e2d2e758a2be4db919ea36",
        "internet_vacancies_anzsco_skill_level_states_and_territories_-_august_2026.xlsx",
        "20261009193231",
    ),
}
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
USER_AGENT = "Mozilla/5.0 (skills-demand-dashboard; +https://github.com/nisha1324)"


def urls_for(name: str) -> list[str]:
    _, official, stamp = FILES[name]
    return [f"{JSA}/{official}", f"{WAYBACK}/{stamp}id_/{JSA}/{official}"]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# hosts that already failed in this run, so later files don't wait on them again
DEAD_HOSTS: set[str] = set()


def download(url: str, dest: Path, timeout: int = 60) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())


def fetch(name: str, dest: Path, retries: int = 2) -> str:
    """Try each URL in turn; keep the first file whose hash matches."""
    expected = FILES[name][0]
    tmp = dest.with_suffix(".part")
    for url in urls_for(name):
        host = urllib.parse.urlsplit(url).netloc
        if host in DEAD_HOSTS:
            continue
        for attempt in range(1, retries + 1):
            try:
                download(url, tmp)
                break
            except Exception as exc:  # timeouts, resets and HTTP errors all mean "try again"
                print(f"  {host} attempt {attempt} failed: {exc}")
                time.sleep(2 * attempt)
        else:
            DEAD_HOSTS.add(host)
            print(f"  skipping {host} for the rest of this run")
            continue
        if sha256(tmp) == expected:
            tmp.replace(dest)
            return url
        print(f"  hash mismatch from {host}, trying next source")
    tmp.unlink(missing_ok=True)
    raise SystemExit(f"could not get a verified copy of {name}")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, (expected, _, _) in FILES.items():
        dest = RAW / name
        if dest.exists() and sha256(dest) == expected:
            print(f"ok (cached)  {name}")
            continue
        url = fetch(name, dest)
        source = "archive" if url.startswith(WAYBACK) else "jsa"
        print(f"ok ({source})  {name}  {dest.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
