"""Text cleaning for artist/title/album comparison.

Folds the missing-track-recovery title rules (track numbers, parentheticals,
punctuation) and the beets string-distance pre-normalization
("X, The" reorder, ampersand fold, VA markers) into deterministic cleaners.
"""

import re

_TRACK_NUM = re.compile(r"^(?:\d{1,3}\s*-\s*)?\d{1,3}\b[\s.\-]+")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_MULTI_SPACE = re.compile(r"\s+")

VA_MARKERS = {"", "various artists", "various", "va", "unknown"}

_END_WORDS = ("the", "a", "an")


def _basic(text):
    """Lowercase, drop non-alphanumerics (except spaces), collapse runs."""
    if not text:
        return ""
    text = str(text).lower().replace("&", " and ")
    text = _NON_ALNUM.sub(" ", text)
    return _MULTI_SPACE.sub(" ", text).strip()


def clean_title(title):
    """Clean a track title: strip leading track numbers, fold case/punct."""
    if not title:
        return ""
    text = str(title).strip()
    text = _TRACK_NUM.sub("", text)
    return _basic(text)


def clean_artist(artist):
    """Clean an artist name: VA markers -> '', 'X, The' -> 'the x'."""
    if not artist:
        return ""
    text = _basic(artist)
    if text in VA_MARKERS:
        return ""
    for word in _END_WORDS:
        suffix = ", " + word
        if text.endswith(suffix):
            text = word + " " + text[: -len(suffix)].strip()
            break
    return text


_PAREN = re.compile(r"\s*[\(\[](.*?)[\)\]]\s*")
_FEAT = re.compile(r"\s*\b(feat|ft|featuring)\b[\. :].*$", re.IGNORECASE)


def split_version(title):
    """Split 'Song (demo) feat. X' -> ('song', ['demo', 'feat x']).

    Base is cleaned for comparison; segments are retained as version
    signals (remix/live/demo/edit) for the version_conflict feature.
    """
    if not title:
        return "", []
    text = str(title).strip()
    segs = []
    for m in _PAREN.finditer(text):
        seg = _basic(m.group(1))
        if seg:
            segs.append(seg)
    text = _PAREN.sub(" ", text)
    m = _FEAT.search(text)
    if m:
        seg = _basic(m.group(0))
        if seg:
            segs.append(seg)
        text = text[: m.start()]
    return _basic(text), segs


def clean_album(album):
    """Album cleaning is title cleaning without track-number stripping."""
    return _basic(album)
