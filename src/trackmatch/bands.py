"""Confidence bands: auto / review / reject.

Hard rules (applied before thresholds):
- version_conflict caps at review: a remix/live/demo must never auto-swap.
- artist_mismatch (artist_sim < 0.35 with both artists known) forces
  reject: same title + different artist is a cover or coincidence.
Fast lanes to auto (no conflicting version signal in either case):
- exact title + near-exact artist (strongest metadata evidence).
- exact title + artist_contained: feat. narrowing/widening of the credit.
- title_ext + exact artist: subtitle appended to the same song by the
  same artist ("Imanin" -> "Imanin bas zihoun").
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
    if artist_sim < ARTIST_MISMATCH and not feats.get("artist_contained"):
        # Same title + different artist is a cover or coincidence. The
        # containment carve-out keeps feat. narrowing/widening
        # ("War" vs "Eric Burdon and War") on the scoring path instead of
        # forcing reject on a low difflib ratio for a token-subset credit.
        return REJECT
    if (feats.get("title_base_sim") == 1.0 and artist_sim >= 0.9):
        # Exact agreement on both key fields with no conflicting version
        # signal is the strongest evidence metadata can give. Residual
        # risk (unlabeled re-recordings) is accepted and documented.
        return AUTO
    if feats.get("title_base_sim") == 1.0 and feats.get("artist_contained"):
        # Same title, artist credit narrowed or widened (feat. handling).
        return AUTO
    if feats.get("title_ext") and artist_sim == 1.0:
        # Same artist, subtitle appended to the same base title.
        return AUTO
    if confidence >= AUTO_THRESHOLD:
        return AUTO
    if confidence >= REVIEW_THRESHOLD:
        return REVIEW
    return REJECT
