import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import build_snapshot as B
from ivi import load

ROOT = Path(__file__).resolve().parents[1]


def wide(values):
    return pd.DataFrame({
        "code": ["0", "1111", "."],
        dt.datetime(2026, 7, 1): values[0],
        dt.datetime(2026, 8, 1): values[1],
    })


def test_melt_turns_dot_into_missing_and_keeps_numbers():
    long = B.melt(wide([[10, 4, "."], [12.33333, 5, "."]]), ["code"], "ads_3ma")
    assert list(long["month"].unique()) == ["2026-07", "2026-08"]
    assert long["ads_3ma"].isna().sum() == 2
    assert long.loc[(long["code"] == "0") & (long["month"] == "2026-08"), "ads_3ma"].item() == 12.33333


def test_melt_rejects_other_text_and_unknown_columns():
    with pytest.raises(ValueError, match="unexpected text"):
        B.melt(wide([[10, "n/a", "."], [1, 2, "."]]), ["code"], "v")
    df = wide([[1, 2, 3], [4, 5, 6]]).assign(extra="x")
    with pytest.raises(ValueError, match="unexpected columns"):
        B.melt(df, ["code"], "v")


def test_csv_gz_is_byte_identical_on_rerun(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    h1 = B.write_csv_gz(df, tmp_path / "one.csv.gz")
    h2 = B.write_csv_gz(df, tmp_path / "two.csv.gz")
    assert h1 == h2
    assert gzip.decompress((tmp_path / "one.csv.gz").read_bytes()).decode() == "a,b\n1,x\n2,y\n"
    # the gzip header's timestamp (bytes 4-7) is zero, so a rerun next week gives the same file too
    assert (tmp_path / "one.csv.gz").read_bytes()[4:8] == b"\x00\x00\x00\x00"


# --- the committed snapshot ---------------------------------------------------------

SNAP = json.loads((ROOT / "data" / "SNAPSHOT.json").read_text())


@pytest.mark.parametrize("name", list(SNAP["tables"]))
def test_snapshot_files_match_the_manifest(name):
    meta = SNAP["tables"][name]
    path = ROOT / meta["file"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]
    assert meta["last_month"] == "2026-08"


def test_occupation_table_keys_and_suppression():
    occ = load.load_occupation_state()
    assert len(occ) == SNAP["tables"]["occupation_state"]["rows"]
    assert not occ.duplicated(["month", "state", "anzsco_code", "anzsco_title"]).any()
    assert set(occ["state"]) == {"AUST", "NSW", "VIC", "QLD", "SA", "WA", "TAS", "NT", "ACT"}
    # suppressed rows have no code and no values; everything else has both
    sup = occ[occ["suppressed"]]
    assert sup["ads_3ma"].isna().all() and (sup["anzsco_code"] == "").all()
    pub = occ[~occ["suppressed"]]
    assert pub["ads_3ma"].notna().all()
    assert pub.loc[pub["level"] == "occupation", "anzsco_code"].str.fullmatch(r"\d{4}").all()
    # codes stay text: the total is "0", not 0
    assert (occ.loc[occ["level"] == "total", "anzsco_code"] == "0").all()


def test_region_tables_keep_custom_group_codes_as_text():
    reg = load.load_ivi_region()
    assert {"2H", "7A"} <= set(reg["anzsco_code"])
    assert reg["region"].nunique() == 37
    sa4 = load.load_sa4_region()
    assert sa4.loc[sa4["level"] == 1, "region_code"].nunique() == 50
    assert "1GSYD" in set(sa4["region_code"])
