from trackmatch.features import pair_features

SAME = {"artist": "Charli xcx", "title": "Von dutch", "album": "Brat",
        "duration": 173, "provider": "deezer"}
SAME_LOCAL = {"artist": "Charli xcx", "title": "Von dutch", "album": "Brat",
              "duration": 174, "provider": "library"}

REMIX = {"artist": "Charli xcx", "title": "Von dutch (remix)", "album": "Brat",
         "duration": 210, "provider": "library"}

COVER = {"artist": "Paul Young", "title": "Love Will Tear Us Apart",
         "album": "", "duration": None, "provider": "library"}
ORIG = {"artist": "Joy Division", "title": "Love Will Tear Us Apart",
        "album": "", "duration": 187, "provider": "spotify"}


def test_same_pair_signals():
    f = pair_features(SAME, SAME_LOCAL)
    assert f["artist_sim"] == 1.0
    assert f["title_base_sim"] == 1.0
    assert f["provider_equal"] is False
    assert f["version_conflict"] is False
    assert f["duration_delta"] == 1


def test_version_conflict_detected():
    f = pair_features(SAME, REMIX)
    assert f["version_conflict"] is True
    assert f["title_base_sim"] == 1.0  # base still matches


def test_cover_pair_signals():
    f = pair_features(ORIG, COVER)
    assert f["title_base_sim"] == 1.0
    assert f["artist_sim"] < 0.5
    assert f["version_conflict"] is False
    assert f["duration_delta"] is None


def test_feat_credit_is_not_conflict():
    a = {"artist": "X", "title": "Song feat. Y", "album": "",
         "duration": 200, "provider": "deezer"}
    b = {"artist": "X", "title": "Song", "album": "",
         "duration": 200, "provider": "library"}
    assert pair_features(a, b)["version_conflict"] is False


def test_missing_fields_tolerated():
    f = pair_features({}, {})
    assert f["artist_sim"] == 1.0  # both empty -> identical
    assert f["duration_delta"] is None
    assert f["provider_equal"] is False
