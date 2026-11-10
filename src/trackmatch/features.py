"""Pairwise match signals between a stream entry and a local candidate.

Each side is a dict with optional keys: artist, title, album, duration
(seconds), provider. Output is a JSON-serializable dict of named signals
consumed by score.score().
"""

from .normalize import clean_album, clean_artist, clean_title, split_version
from .similarity import ratio

# Version segments that mark a DIFFERENT recording. 'feat' credits and
# 'remaster' are metadata noise, not conflicts.
VERSION_WORDS = {
    "remix", "remixed", "mix", "live", "demo", "edit", "edited",
    "acoustic", "unplugged", "cover", "reprise", "instrumental",
    "karaoke", "slowed", "sped", "session", "take", "version",
}


def _is_version(seg):
    words = set(seg.split())
    return bool(words & VERSION_WORDS) and not seg.startswith("feat")


def pair_features(old, new):
    """Compute named similarity signals for an (old, new) entry pair."""
    old = old or {}
    new = new or {}

    old_base, old_segs = split_version(old.get("title", ""))
    new_base, new_segs = split_version(new.get("title", ""))

    old_ver = {s for s in old_segs if _is_version(s)}
    new_ver = {s for s in new_segs if _is_version(s)}
    version_conflict = bool(old_ver ^ new_ver) or (
        bool(old_ver and new_ver) and old_ver != new_ver
    )

    try:
        od = old.get("duration")
        nd = new.get("duration")
        duration_delta = abs(float(od) - float(nd)) if od and nd else None
    except (TypeError, ValueError):
        duration_delta = None

    return {
        "artist_sim": ratio(clean_artist(old.get("artist", "")),
                            clean_artist(new.get("artist", ""))),
        "title_sim": ratio(clean_title(old.get("title", "")),
                           clean_title(new.get("title", ""))),
        "title_base_sim": ratio(old_base, new_base),
        "album_sim": ratio(clean_album(old.get("album", "")),
                           clean_album(new.get("album", ""))),
        "album_known": bool((old.get("album") or "").strip()
                            or (new.get("album") or "").strip()),
        "duration_delta": duration_delta,
        "provider_equal": bool(old.get("provider"))
        and old.get("provider") == new.get("provider"),
        "version_conflict": version_conflict,
    }
