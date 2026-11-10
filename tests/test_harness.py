import json

from trackmatch.harness import replay_playlist


class FakeMA:
    """Canned Music Assistant client: pid -> ordered track dicts."""

    def __init__(self, playlists):
        self.playlists = playlists

    def playlist_tracks(self, pid):
        return self.playlists[str(pid)]


def _snap(tmp_path):
    snap = {
        "playlist_id": "99",
        "name": "Test",
        "when": "2026-11-10",
        "uris": ["deezer--X://track/1", "deezer--X://track/2", "deezer--X://track/3"],
        "songs": [
            {"pos": 1, "artist": "A", "title": "One", "uri": "deezer--X://track/1"},
            {"pos": 2, "artist": "B", "title": "Two", "uri": "deezer--X://track/2"},
            {"pos": 3, "artist": "C", "title": "Three", "uri": "deezer--X://track/3"},
        ],
    }
    p = tmp_path / "pl-99.json"
    p.write_text(json.dumps(snap))
    return str(p)


def test_positional_join_labels_swap(tmp_path):
    ma = FakeMA({"99": [
        {"artist": "A", "title": "One", "uri": "library://track/11"},   # swapped
        {"artist": "B", "title": "Two", "uri": "deezer--X://track/2"},   # untouched
        {"artist": "C", "title": "Three", "uri": "library://track/33"},  # swapped
    ]})
    pairs = list(replay_playlist(_snap(tmp_path), ma))
    assert len(pairs) == 3
    assert pairs[0][0]["uri"] == "deezer--X://track/1"
    assert pairs[0][1]["uri"] == "library://track/11"
    assert pairs[1][1]["uri"] == "deezer--X://track/2"  # same uri, not a swap
    assert pairs[2][1]["uri"] == "library://track/33"


def test_shorter_live_playlist_yields_none(tmp_path):
    ma = FakeMA({"99": [
        {"artist": "A", "title": "One", "uri": "library://track/11"},
    ]})
    pairs = list(replay_playlist(_snap(tmp_path), ma))
    assert len(pairs) == 3
    assert pairs[1][1] is None
    assert pairs[2][1] is None


def test_old_entries_carry_provider(tmp_path):
    ma = FakeMA({"99": []})
    pairs = list(replay_playlist(_snap(tmp_path), ma))
    assert pairs[0][0]["provider"] == "deezer"
    assert pairs[0][0]["artist"] == "A"
