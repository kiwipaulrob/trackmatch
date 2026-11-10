import json

REQUIRED = {"old_artist", "old_title", "old_album", "old_provider",
            "new_artist", "new_title", "new_album", "label", "note"}


def _rows():
    with open("tests/fixtures/pairs.jsonl") as f:
        return [json.loads(l) for l in f if l.strip()]


def test_fixture_schema():
    bad = []
    for i, row in enumerate(_rows(), 1):
        if set(row) != REQUIRED or row["label"] not in ("same", "different"):
            bad.append(i)
    assert not bad, f"bad fixture lines: {bad}"


def test_fixtures_nonempty():
    assert len(_rows()) >= 20, "need >=20 seed pairs"


def test_fixtures_have_both_labels():
    labels = {r["label"] for r in _rows()}
    assert labels == {"same", "different"}
