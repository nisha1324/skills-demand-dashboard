"""Load the tidy IVI snapshot with the right types (codes stay text: "0", "1111", "2H")."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def load_occupation_state(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or DATA / "occupation_state.csv.gz", dtype={"anzsco_code": str},
                     keep_default_na=False, na_values={"ads_3ma": [""]})
    df["suppressed"] = df["suppressed"].map({"True": True, "False": False, True: True, False: False})
    return df


def load_ivi_region(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or DATA / "ivi_region.csv.gz", dtype={"anzsco_code": str})


def load_sa4_region(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or DATA / "sa4_region.csv.gz", dtype={"anzsco_code": str, "region_code": str})


def load_skill_level(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or DATA / "skill_level_state.csv.gz")


def load_all():
    return load_occupation_state(), load_ivi_region(), load_sa4_region(), load_skill_level()
