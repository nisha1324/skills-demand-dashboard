"""Turn the four IVI workbooks in data/raw/ into tidy, long CSV snapshots in data/.

Each workbook has one row per series and one column per month. This script
melts them to one row per series per month, keeps the published numbers as
they are, and turns JSA's "." (suppressed occupation) into an empty value.

Outputs (gzip with a fixed timestamp, so the same input gives the same bytes):
- data/occupation_state.csv.gz   ANZSCO 4-digit x state, 3-month average, Mar 2006 on
- data/ivi_region.csv.gz         custom ANZSCO 2-digit x 37 IVI regions, 3-month average, May 2010 on
- data/sa4_region.csv.gz         custom ANZSCO 2-digit x GCCSA/SA4, 3-month average, Jan 2019 on
- data/skill_level_state.csv.gz  skill level x state, trend and seasonally adjusted, Jan 2006 on
- data/SNAPSHOT.json             source hashes, row counts and month ranges
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import io
import json
from pathlib import Path

import pandas as pd

from scripts.download_data import FILES

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

SUPPRESSED = "."


def month_columns(df: pd.DataFrame) -> list:
    return [c for c in df.columns if isinstance(c, (dt.datetime, pd.Timestamp))]


def melt(df: pd.DataFrame, id_cols: list[str], value_name: str) -> pd.DataFrame:
    """Wide (one column per month) to long, with "." as missing."""
    months = month_columns(df)
    other = [c for c in df.columns if c not in months and c not in id_cols]
    if other:
        raise ValueError(f"unexpected columns: {other}")
    long = df.melt(id_vars=id_cols, value_vars=months, var_name="month", value_name=value_name)
    raw = long[value_name]
    bad = raw[raw.map(lambda v: isinstance(v, str) and v != SUPPRESSED)]
    if len(bad):
        raise ValueError(f"unexpected text values: {sorted(set(bad))[:5]}")
    long[value_name] = pd.to_numeric(raw.where(raw != SUPPRESSED), errors="raise")
    long["month"] = pd.to_datetime(long["month"]).dt.strftime("%Y-%m")
    return long


def read_occupation_state(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="4 digit 3 month average", dtype={"ANZSCO_CODE": str})
    df = df.rename(columns={"ANZSCO_CODE": "anzsco_code", "ANZSCO_TITLE": "anzsco_title"})
    long = melt(df, ["anzsco_code", "anzsco_title", "state"], "ads_3ma")
    # Suppressed occupations have "." as their code too; give them a stable key from the title.
    long["suppressed"] = long["anzsco_code"] == SUPPRESSED
    long.loc[long["suppressed"], "anzsco_code"] = ""
    long["level"] = long["anzsco_code"].map(lambda c: "total" if c == "0" else "occupation")
    cols = ["month", "state", "level", "anzsco_code", "anzsco_title", "suppressed", "ads_3ma"]
    return long[cols].sort_values(["month", "state", "anzsco_code", "anzsco_title"], kind="stable")


def read_ivi_region(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Averaged", dtype={"ANZSCO_CODE": str})
    df = df.rename(columns={"Level": "level", "State": "state", "ANZSCO_CODE": "anzsco_code",
                            "ANZSCO_TITLE": "anzsco_title"})
    long = melt(df, ["level", "state", "region", "anzsco_code", "anzsco_title"], "ads_3ma")
    cols = ["month", "state", "region", "level", "anzsco_code", "anzsco_title", "ads_3ma"]
    return long[cols].sort_values(["month", "state", "region", "level", "anzsco_code"], kind="stable")


def read_sa4_region(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Averaged", dtype={"ANZSCO_CODE": str, "region_code": str})
    df = df.rename(columns={"Level": "level", "State": "state", "ANZSCO_CODE": "anzsco_code",
                            "ANZSCO_TITLE": "anzsco_title"})
    ids = ["level", "state", "region_name", "region_code", "region_level", "anzsco_code", "anzsco_title"]
    long = melt(df, ids, "ads_3ma")
    cols = ["month", "state", "region_code", "region_name", "region_level", "level",
            "anzsco_code", "anzsco_title", "ads_3ma"]
    return long[cols].sort_values(["month", "state", "region_code", "level", "anzsco_code"], kind="stable")


def read_skill_level(path: Path) -> pd.DataFrame:
    parts = []
    for sheet, series in [("Trend", "trend"), ("Seasonally Adjusted", "seasonally_adjusted")]:
        df = pd.read_excel(path, sheet_name=sheet)
        df = df.rename(columns={"Level": "level", "Title": "title", "State": "state",
                                "Skill_level": "skill_level"})
        long = melt(df, ["level", "title", "state", "skill_level"], "ads")
        long["series"] = series
        parts.append(long)
    long = pd.concat(parts, ignore_index=True)
    cols = ["series", "month", "state", "skill_level", "title", "ads"]
    return long[cols].sort_values(["series", "month", "state", "skill_level"], kind="stable")


def write_csv_gz(df: pd.DataFrame, path: Path) -> str:
    """Write a gzip CSV with mtime 0, so reruns give identical bytes. Returns its SHA-256."""
    text = df.to_csv(index=False, lineterminator="\n")
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as gz:
        gz.write(text.encode("utf-8"))
    path.write_bytes(buf.getvalue())
    return hashlib.sha256(buf.getvalue()).hexdigest()


TABLES = {
    "occupation_state": ("ivi_anzsco4_states_aug2026.xlsx", read_occupation_state),
    "ivi_region": ("ivi_anzsco2_ivi_regions_aug2026.xlsx", read_ivi_region),
    "sa4_region": ("ivi_anzsco2_gccsa_sa4_aug2026.xlsx", read_sa4_region),
    "skill_level_state": ("ivi_skill_level_states_aug2026.xlsx", read_skill_level),
}


def main() -> None:
    manifest = {
        "source": "Jobs and Skills Australia, Internet Vacancy Index, August 2026 release "
                  "(published 23 September 2026)",
        "licence": "CC BY 4.0, (c) Commonwealth of Australia, Jobs and Skills Australia",
        "tables": {},
    }
    for name, (raw_name, reader) in TABLES.items():
        raw_path = RAW / raw_name
        expected = FILES[raw_name][0]
        got = hashlib.sha256(raw_path.read_bytes()).hexdigest()
        if got != expected:
            raise SystemExit(f"{raw_name}: SHA-256 {got} is not the pinned {expected}")
        df = reader(raw_path)
        out = OUT / f"{name}.csv.gz"
        digest = write_csv_gz(df, out)
        value_col = "ads" if "ads" in df.columns else "ads_3ma"
        manifest["tables"][name] = {
            "file": f"data/{out.name}",
            "source_file": FILES[raw_name][1],
            "source_sha256": expected,
            "rows": int(len(df)),
            "first_month": df["month"].min(),
            "last_month": df["month"].max(),
            "empty_values": int(df[value_col].isna().sum()),
            "sha256": digest,
        }
        print(f"{name}: {len(df):,} rows, {df['month'].min()} to {df['month'].max()}, "
              f"{out.stat().st_size / 1e6:.1f} MB")
    (OUT / "SNAPSHOT.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
