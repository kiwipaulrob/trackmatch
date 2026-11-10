import time

import pytest

from trackmatch.adapters.ma import (
    build_index,
    fetch_library_tracks,
    find_candidates,
)


def _lib():
    return [
        {"artist": "Tamikrest", "title": "Imanin bas zihoun",
         "uri": "library://track/1", "album": "A", "duration": 200,
         "provider": "library"},
        {"artist": "Chief Keef", "title": "Tony Montana Flow",
         "uri": "library://track/2", "album": "B", "duration": 210,
         "provider": "library"},
        {"artist": "Someone Else", "title": "Totally Different Song",
         "uri": "library://track/3", "album": "C", "duration": 180,
         "provider": "library"},
    ]


def test_top_candidate_matches_entry():
    index = build_index(_lib())
    got = find_candidates({"title": "Imanin"}, index, k=8)
    assert got and got[0]["uri"] == "library://track/1"


def test_k_respected_and_no_private_keys():
    index = build_index(_lib())
    got = find_candidates({"title": "Song"}, index, k=1)
    assert len(got) <= 1
    assert all(not k.startswith("_") for c in got for k in c)


def test_no_overlap_returns_empty():
    index = build_index(_lib())
    assert find_candidates({"title": "Zqxw Vjplm Kzzz"}, index) == []
    assert find_candidates({"title": ""}, index) == []
    assert find_candidates({"title": "The"}, index) == []  # stopwords only


def test_fetch_library_tracks_paginates():
    pages = [
        [{"name": f"Song {i}", "artists": [{"name": "A"}],
          "album": {"name": "Alb"}, "duration": 200,
          "uri": f"library://track/{i}"} for i in range(3)],
        [{"name": "Song 3", "artists": [{"name": "B"}],
          "album": {"name": "Alb"}, "duration": 210,
          "uri": "library://track/3"}],
    ]

    def fake_api(command, args):
        assert command == "music/tracks/library_items"
        if args["offset"] == 0:
            assert args["limit"] == 3
            return pages[0]
        return pages[1]

    got = fetch_library_tracks(fake_api, page_size=3)
    assert [c["uri"] for c in got] == [f"library://track/{i}" for i in range(4)]
    assert got[0]["artist"] == "A" and got[0]["title"] == "Song 0"
    assert got[0]["provider"] == "library"


def test_prefilter_perf_4k_entries_x_100k_library():
    import random
    rng = random.Random(42)
    vocab = [f"word{i}" for i in range(2000)]
    lib = [
        {"artist": f"Artist {i % 500}", "title": " ".join(rng.sample(vocab, 4)),
         "uri": f"library://track/{i}", "album": "", "duration": 200,
         "provider": "library"}
        for i in range(100_000)
    ]
    t0 = time.perf_counter()
    index = build_index(lib)
    build_s = time.perf_counter() - t0
    entries = [{"title": " ".join(rng.sample(vocab, 4))} for _ in range(4000)]
    t0 = time.perf_counter()
    for e in entries:
        find_candidates(e, index, k=8)
    query_s = time.perf_counter() - t0
    assert query_s < 60, f"prefilter too slow: {query_s:.1f}s"
    print(f"\nbuild {build_s:.1f}s, 4k queries {query_s:.1f}s")
