"""Pairwise match signals between a stream entry and a local candidate.

Each side is a dict with optional keys: artist, title, album, duration
(seconds), provider. Output is a JSON-serializable dict of named signals
consumed by score.score().
"""

from .normalize import clean_album, clean_artist, clean_title, split_version
from .similarity import ratio

# Version segments that mark a DIFFERENT recording. 'feat' credits and
# 'remaster' are metadata noise, not conflicts. Spoken interludes
# (skit/interlude/intro/outro) are separate tracks, not the song.
VERSION_WORDS = {
    "remix", "remixed", "mix", "live", "demo", "edit", "edited",
    "acoustic", "unplugged", "cover", "reprise", "instrumental",
    "karaoke", "slowed", "sped", "session", "take", "version",
    "skit", "skito", "interlude", "intro", "outro",
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

    old_artist = clean_artist(old.get("artist", ""))
    new_artist = clean_artist(new.get("artist", ""))
    old_toks, new_toks = set(old_artist.split()), set(new_artist.split())
    # Feat. narrowing/widening: one artist credit contains the other
    # ("Chief Keef, Akachi" vs "Chief Keef"). Both must be known.
    artist_contained = bool(old_artist and new_artist) and (
        old_toks <= new_toks or new_toks <= old_toks
    )
    # Subtitle extension: the longer base starts with the shorter plus a
    # word boundary ("Imanin bas zihoun" vs "Imanin"). The extension must
    # carry no version words (blocks "Jesus" -> "Jesus Skit"), and both
    # artists must be known so two empty credits can't self-confirm.
    title_ext = False
    if old_base and new_base and old_base != new_base:
        short, long = (old_base, new_base) if len(old_base) < len(new_base) \
            else (new_base, old_base)
        if long.startswith(short) and long[len(short)] == " ":
            ext_toks = set(long[len(short):].split())
            title_ext = (not (ext_toks & VERSION_WORDS)
                         and bool(old_artist and new_artist))

    return {
        "artist_sim": ratio(old_artist, new_artist),
        "title_sim": ratio(clean_title(old.get("title", "")),
                           clean_title(new.get("title", ""))),
        "title_base_sim": ratio(old_base, new_base),
        "album_sim": (ratio(clean_album(old.get("album", "")),
                           clean_album(new.get("album", "")))
                      if ((old.get("album") or "").strip()
                          and (new.get("album") or "").strip())
                      else 0.5),
        # One-sided album knowledge is absence of evidence, not
        # disagreement: only a known-vs-known comparison informs.
        "album_known": bool((old.get("album") or "").strip()
                            and (new.get("album") or "").strip()),
        "duration_delta": duration_delta,
        "provider_equal": bool(old.get("provider"))
        and old.get("provider") == new.get("provider"),
        "version_conflict": version_conflict,
        "artist_contained": artist_contained,
        "title_ext": title_ext,
    }
