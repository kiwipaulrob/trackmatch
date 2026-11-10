"""Weighted confidence scorer: signals -> 0..1 confidence + breakdown.

Initial weights (tuned in harness Phase 3, documented in docs/weights.md):
title_base 0.40, artist 0.25, title_full 0.10, album 0.10, duration 0.10,
provider 0.05. Unknown album/duration/provider score neutral 0.5 rather
than rewarding or punishing missing metadata.

`judge_prob` is a reserved forward hook for the optional local-model judge
tier: when given, it blends 80/20 with the deterministic score and is
logged in the breakdown. Default None = pure deterministic.
"""

WEIGHTS = {
    "title_base": 0.40,
    "artist": 0.25,
    "title_full": 0.10,
    "album": 0.10,
    "duration": 0.10,
    "provider": 0.05,
}

_DURATION_TOLERANCE = 30.0  # seconds over which duration agreement decays
_JUDGE_BLEND = 0.20


def _duration_score(delta):
    if delta is None:
        return 0.5
    return max(0.0, 1.0 - min(delta / _DURATION_TOLERANCE, 1.0))


def score(feats, weights=None, judge_prob=None):
    """Return (confidence, breakdown) for a pair_features() dict."""
    weights = weights or WEIGHTS
    album_known = feats.get("album_known", True)
    parts = {
        "title_base": feats.get("title_base_sim", 0.0),
        "artist": feats.get("artist_sim", 0.0),
        "title_full": feats.get("title_sim", 0.0),
        "album": feats.get("album_sim", 0.5) if album_known else 0.5,
        "duration": _duration_score(feats.get("duration_delta")),
        "provider": 1.0 if feats.get("provider_equal") else 0.5,
    }
    total = sum(weights[k] for k in parts)
    conf = sum(parts[k] * weights[k] for k in parts) / total
    breakdown = {"parts": parts, "weights": {k: weights[k] for k in parts}}
    if judge_prob is not None:
        conf = (1.0 - _JUDGE_BLEND) * conf + _JUDGE_BLEND * judge_prob
        breakdown["judge_prob"] = judge_prob
        breakdown["judge_blend"] = _JUDGE_BLEND
    return conf, breakdown
