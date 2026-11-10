import json

from trackmatch import bands
from trackmatch.features import pair_features
from trackmatch.score import score


def _pair(label):
    with open("tests/fixtures/pairs.jsonl") as f:
        for line in f:
            row = json.loads(line)
            if row["label"] == label:
                old = {"artist": row["old_artist"], "title": row["old_title"],
                       "album": row["old_album"], "provider": row["old_provider"]}
                new = {"artist": row["new_artist"], "title": row["new_title"],
                       "album": row["new_album"], "provider": "library"}
                return pair_features(old, new)
    raise AssertionError("no fixture with label " + label)


def _by_note(substr):
    with open("tests/fixtures/pairs.jsonl") as f:
        for line in f:
            row = json.loads(line)
            if substr in row["note"]:
                old = {"artist": row["old_artist"], "title": row["old_title"],
                       "album": row["old_album"], "provider": row["old_provider"]}
                new = {"artist": row["new_artist"], "title": row["new_title"],
                       "album": row["new_album"], "provider": "library"}
                return pair_features(old, new)
    raise AssertionError("no fixture note matching " + substr)


def test_brat_pair_is_auto():
    conf, _ = score(_pair("same"))
    assert bands.assign(conf, _pair("same")) == "auto"


def test_remix_never_auto():
    feats = _by_note("remix is not the same")
    conf, _ = score(feats)
    assert bands.assign(conf, feats) == "review"


def test_cover_is_reject():
    feats = _by_note("cover version")
    conf, _ = score(feats)
    assert bands.assign(conf, feats) == "reject"


def test_exact_match_fast_lane():
    feats = _by_note("Bandcamp pinned entry")
    conf, _ = score(feats)
    assert conf < bands.AUTO_THRESHOLD  # missing album keeps it under
    assert bands.assign(conf, feats) == "auto"


def test_spelling_variant_stays_review():
    feats = _by_note("spelling variant")
    conf, _ = score(feats)
    assert bands.assign(conf, feats) == "review"


def test_breakdown_sums_to_confidence():
    feats = _pair("same")
    conf, breakdown = score(feats)
    parts = breakdown["parts"]
    weights = breakdown["weights"]
    total = sum(weights.values())
    calc = sum(parts[k] * weights[k] for k in parts) / total
    assert abs(calc - conf) < 1e-9


def test_score_json_serializable():
    feats = _by_note("unplugged")
    conf, breakdown = score(feats)
    json.dumps({"confidence": conf, "breakdown": breakdown})


def test_thresholds_sane():
    assert bands.AUTO_THRESHOLD == 0.90
    assert bands.REVIEW_THRESHOLD == 0.60
