"""Ground-truth replay: join pre-swap snapshots with live playlist state.

A sweep snapshot holds the ORIGINAL entries (pos/artist/title/uri). The
live playlist after a successful apply holds the NEW entries at the same
positions. Positional join gives (old, new-or-None) pairs for free:

- new is None ......... position vanished (omission / count mismatch)
- new.uri == old.uri .. untouched stream entry (negative example)
- otherwise ........... a performed swap (positive example)

Read-only. The ma_client needs one method: playlist_tracks(pid) returning
an ordered list of {artist, title, uri} dicts.
"""

import json


def _provider_of(uri):
    uri = uri or ""
    if "://" in uri:
        scheme = uri.split("://", 1)[0]
        return scheme.split("--")[0]
    return ""


def replay_playlist(snapshot_path, ma_client):
    """Yield (old_entry, new_entry_or_None) for each snapshot position."""
    with open(snapshot_path) as f:
        snap = json.load(f)
    live = ma_client.playlist_tracks(snap["playlist_id"])
    live_by_pos = {i + 1: t for i, t in enumerate(live or [])}
    for song in snap.get("songs", []):
        old = {"pos": song.get("pos"),
               "artist": song.get("artist", ""),
               "title": song.get("title", ""),
               "uri": song.get("uri", ""),
               "provider": _provider_of(song.get("uri", ""))}
        new_track = live_by_pos.get(song.get("pos"))
        new = None
        if new_track is not None:
            new = {"pos": song.get("pos"),
                   "artist": new_track.get("artist", ""),
                   "title": new_track.get("title", ""),
                   "uri": new_track.get("uri", ""),
                   "provider": _provider_of(new_track.get("uri", ""))}
        yield old, new


def is_swap(pair):
    """True when the position holds a different URI than the snapshot."""
    old, new = pair
    return new is not None and new.get("uri") != old.get("uri")


def compare_decisions(pairs, new_fn):
    """Compare performed swaps against the new scorer's bands.

    new_fn(old, new_or_None) -> (confidence, band). new None means the
    position vanished: score against an empty candidate (must reject).

    Verdicts: reproduced (swap+auto), missed (swap+review/reject),
    agree-keep (position unswapped — the scorer's opinion on the
    identical pair is uninformative, so keeps always agree).

    Overreach (auto-swapping a wrong candidate) cannot be measured at
    replay time — the rejected candidates are gone — and is measured
    instead in live pilot runs against a candidate index.
    """
    rows = []
    for old, new in pairs:
        swapped = is_swap((old, new))
        conf, band = new_fn(old, new)
        if swapped and band == "auto":
            verdict = "reproduced"
        elif swapped:
            verdict = "missed"
        else:
            verdict = "agree-keep"
        rows.append({"pos": old.get("pos"), "old_uri": old.get("uri"),
                     "new_uri": (new or {}).get("uri"),
                     "swapped": swapped, "confidence": conf,
                     "band": band, "verdict": verdict})
    return rows


def summarize(rows):
    """Count verdicts: {'reproduced': n, 'missed': n, ...}."""
    counts = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    return counts
