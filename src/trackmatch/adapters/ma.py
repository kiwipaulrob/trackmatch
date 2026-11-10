"""MA library adapter: offline index + top-k candidate prefilter.

The full local library is pulled ONCE (`fetch_library_tracks` paginates
`music/tracks/library_items`); `build_index` adds title-base token
postings so `find_candidates` answers each entry with an inverted-index
lookup instead of scanning 100k tracks. Full scorer runs on the top-k.
"""

from trackmatch.normalize import clean_artist, split_version

#: Tokens too common to discriminate (dropped from postings/queries).
STOPWORDS = frozenset({
    "the", "a", "an", "and", "of", "in", "on", "to", "le", "la", "les",
    "de", "des", "du", "el", "y",
})


def title_tokens(title):
    """Token set of the version-stripped title base, minus stopwords."""
    base, _segs = split_version(title)
    return {t for t in base.split() if t and t not in STOPWORDS}


def artist_tokens(artist):
    """Token set of the cleaned artist string (feat. credits cut)."""
    return set(clean_artist(artist).split())


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
        docs.append(dict(t, _tokens=toks,
                         _atokens=artist_tokens(t.get("artist", ""))))
        for tok in toks:
            postings.setdefault(tok, []).append(idx)
    return {"tracks": docs, "postings": postings}


def _public(doc):
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def find_candidates(entry, index, k=8):
    """Top-k index tracks by title-token JACCARD with the entry title.

    Raw overlap counts drown exact matches when one common token (e.g.
    "holy") hits hundreds of tracks and truncation keeps an arbitrary 8;
    Jaccard ranks the 1-token exact title 1.0 and a 7-token partial ~0.14
    (overlap coefficient can't do this: with a 1-token query every hit
    scores 1.0). Ties break on raw overlap, then lower library position
    (stable, deterministic). Returns public candidate dicts.
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
    n = len(toks)
    atoks = artist_tokens(entry.get("artist", ""))
    ranked = sorted(counts,
                    key=lambda i: (-counts[i] / (n + len(tracks[i]["_tokens"])
                                                - counts[i]),
                                   -len(atoks & tracks[i]["_atokens"]),
                                   -counts[i], i))[:k]
    return [_public(tracks[i]) for i in ranked]


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


class RebuildError(Exception):
    """Playlist rebuild failed mid-apply; `.report` has snapshot + state."""

    def __init__(self, msg, report=None):
        super().__init__(msg)
        self.report = report or {}


def rebuild_playlist(transport, pid, new_uris, batch_size=25):
    """Rebuild one playlist IN PLACE (ported sweep-script semantics).

    snapshot -> remove-all by position -> verify empty -> batched add ->
    verify count. `transport` provides fetch(pid), remove(pid, positions),
    add(pid, uris). Verification is by COUNT, not URI equality: MA
    normalizes library:// merge URIs to the local file mapping on ingest,
    so post-add URI comparison always mismatches (lesson from the Nov 2026
    sweep). Returns a report dict. Raises RebuildError (with .report incl.
    snapshot) on any failure after mutation starts — never auto-restores:
    the old URIs may no longer be addable, so restore can destroy what the
    rebuild saved.
    """
    snapshot = transport.fetch(pid)
    if snapshot is None:
        raise RebuildError(f"pid {pid}: pre-mutation fetch failed")
    report = {"pid": pid, "before": len(snapshot),
              "snapshot_uris": [t.get("uri", "") for t in snapshot],
              "target": len(new_uris), "added": 0, "verified": False}

    positions = [t.get("position", i) for i, t in enumerate(snapshot)]
    try:
        if positions:
            transport.remove(pid, positions)
        if transport.fetch(pid):
            raise RebuildError(f"pid {pid}: not empty after remove")
        for i in range(0, len(new_uris), batch_size):
            transport.add(pid, new_uris[i:i + batch_size])
            report["added"] += len(new_uris[i:i + batch_size])
        final = transport.fetch(pid)
        if final is None or len(final) != len(new_uris):
            raise RebuildError(
                f"pid {pid}: count mismatch "
                f"({len(final) if final is not None else 'fetch-failed'}"
                f" vs {len(new_uris)})")
        report["verified"] = True
        report["after"] = len(final)
    except Exception as e:
        report["error"] = str(e)
        raise RebuildError(str(e), report)
    return report
