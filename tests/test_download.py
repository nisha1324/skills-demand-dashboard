import hashlib
import re

import pytest

from scripts import download_data as D


def test_every_file_is_pinned_and_tries_jsa_first():
    assert len(D.FILES) == 4
    for name, (sha, official, stamp) in D.FILES.items():
        assert re.fullmatch(r"[0-9a-f]{64}", sha), name
        assert official.endswith("_-_august_2026.xlsx")
        urls = D.urls_for(name)
        assert urls[0].startswith("https://www.jobsandskills.gov.au/")
        # id_ asks the archive for the original bytes, not a rewritten page
        assert urls[1] == f"https://web.archive.org/web/{stamp}id_/{urls[0]}"


def test_fetch_skips_a_dead_host_and_rejects_a_wrong_file(tmp_path, monkeypatch):
    good = b"the real workbook"
    name = "ivi_skill_level_states_aug2026.xlsx"
    monkeypatch.setitem(D.FILES, name, (hashlib.sha256(good).hexdigest(), "f.xlsx", "20260101000000"))
    monkeypatch.setattr(D, "DEAD_HOSTS", set())
    monkeypatch.setattr(D.time, "sleep", lambda s: None)
    calls = []

    def fake_download(url, dest, timeout=60):
        calls.append(url)
        if "jobsandskills" in url and "archive" not in url:
            raise TimeoutError("read timed out")
        dest.write_bytes(good)

    monkeypatch.setattr(D, "download", fake_download)
    dest = tmp_path / name
    url = D.fetch(name, dest)
    assert "web.archive.org" in url
    assert dest.read_bytes() == good
    assert len(calls) == 3  # two tries on JSA, one on the archive

    # a copy whose hash doesn't match is never kept
    monkeypatch.setattr(D, "DEAD_HOSTS", set())
    monkeypatch.setattr(D, "download", lambda url, dest, timeout=60: dest.write_bytes(b"changed"))
    dest.unlink()
    with pytest.raises(SystemExit):
        D.fetch(name, dest)
    assert not dest.exists()
    assert not dest.with_suffix(".part").exists()
