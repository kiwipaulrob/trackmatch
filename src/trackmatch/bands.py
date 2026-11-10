"""Confidence bands: auto / review / reject.

Hard rules (applied before thresholds):
- version_conflict caps at review: a remix/live/demo must never auto-swap.
- artist_mismatch (artist_sim < 0.35 with both artists known) forces
  reject: same title + different artist is a cover or coincidence.
"""

AUTO_THRESHOLD = 0.90
REVIEW_THRESHOLD = 0.60
ARTIST_MISMATCH = 0.35

AUTO = "auto"
REVIEW = "review"
REJECT = "reject"


def assign(confidence, feats):
    """Assign a band for a confidence + pair_features() dict."""
    feats = feats or {}
    if feats.get("version_conflict"):
        if confidence >= REVIEW_THRESHOLD:
            return REVIEW
        return REJECT
    artist_sim = feats.get("artist_sim", 1.0)
    if artist_sim < ARTIST_MISMATCH:
        return REJECT
    if confidence >= AUTO_THRESHOLD:
        return AUTO
    if confidence >= REVIEW_THRESHOLD:
        return REVIEW
    return REJECT
