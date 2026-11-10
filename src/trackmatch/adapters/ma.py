"""MA library adapter: offline index + top-k candidate prefilter.

The full local library is pulled ONCE (`fetch_library_tracks` paginates
`music/tracks/library_items`); `build_index` adds title-base token
postings so `find_candidates` answers each entry with an inverted-index
lookup instead of scanning 100k tracks. Full scorer runs on the top-k.
"""

from trackmatch.normalize import split_version

#: Tokens too common to discriminate (dropped from postings/queries).
STOPWORDS = frozenset({
    "the", "a", "an", "and", "of", "in", "on", "to", "le", "la", "les",
    "de", "des", "du", "el", "y",
})


def title_tokens(title):
    """Token set of the version-stripped title base, minus stopwords."""
    base, _segs = split_version(title)
    return {t for t in base.split() if t and t not in STOPWORDS}


def build_index(tracks):
    """Build a search index over candidate dicts.

    Each track: {artist, title, uri, album, duration, provider}.
    Returns {"tracks": [...], "postings": {token: [idx, ...]}}.
    """
    docs = []
    postings = {}
    for t in tracks:
        toks = title_tokens(t.get("title", ""))
        idx = len(docs)
        docs.append(dict(t, _tokens=toks))
        for tok in toks:
            postings.setdefault(tok, []).append(idx)
    return {"tracks": docs, "postings": postings}


def _public(doc):
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def find_candidates(entry, index, k=8):
    """Top-k index tracks by title-base token overlap with entry title.

    Ties break toward lower library position (stable, deterministic).
    Returns public candidate dicts (no private index keys).
    """
    toks = title_tokens(entry.get("title", ""))
    if not toks:
        return []
    tracks = index["tracks"]
    postings = index["postings"]
    counts = {}
    for tok in toks:
        for idx in postings.get(tok, ()):  # tuple default: no alloc
            counts[idx] = counts.get(idx, 0) + 1
    if not counts:
        return []
    top = sorted(counts, key=lambda i: (-counts[i], i))[:k]
    return [_public(tracks[i]) for i in top]


def _track_to_candidate(t):
    artists = t.get("artists") or []
    artist = ", ".join(a.get("name", "?") for a in artists)
    album = t.get("album") or {}
    album_name = album.get("name", "") if isinstance(album, dict) else str(album)
    uri = t.get("uri", "")
    provider = uri.split("://")[0].split("--")[0] if "://" in uri else ""
    return {
        "artist": artist,
        "title": t.get("name", "?"),
        "uri": uri,
        "album": album_name,
        "duration": t.get("duration"),
        "provider": provider,
    }


def fetch_library_tracks(api_call, page_size=500):
    """Pull the whole library via paginated `music/tracks/library_items`.

    `api_call(command, args)` is the injected transport (real MA websocket
    call in production, fake in tests). Returns candidate dicts.
    """
    out = []
    offset = 0
    while True:
        page = api_call("music/tracks/library_items",
                        {"limit": page_size, "offset": offset})
        if not isinstance(page, list) or not page:
            break
        out.extend(_track_to_candidate(t) for t in page)
        if len(page) < page_size:
            break
        offset += page_size
    return out
