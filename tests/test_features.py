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


def test_artist_contained_feat_narrowing():
    a = {"artist": "Chief Keef, Akachi", "title": "Tony Montana Flow"}
    b = {"artist": "Chief Keef", "title": "Tony Montana Flow"}
    f = pair_features(a, b)
    assert f["artist_contained"] is True
    assert f["title_base_sim"] == 1.0


def test_artist_contained_requires_known_artists():
    assert pair_features({"artist": "", "title": "S"},
                         {"artist": "X", "title": "S"})["artist_contained"] is False
    assert pair_features({"artist": "", "title": "S"},
                         {"artist": "", "title": "S"})["artist_contained"] is False


def test_title_ext_subtitle_appended():
    a = {"artist": "Tamikrest", "title": "Imanin"}
    b = {"artist": "Tamikrest", "title": "Imanin bas zihoun"}
    f = pair_features(a, b)
    assert f["title_ext"] is True


def test_title_ext_blocked_by_version_word():
    a = {"artist": "Chief Keef", "title": "Jesus"}
    b = {"artist": "Chief Keef", "title": "Jesus Skit"}
    assert pair_features(a, b)["title_ext"] is False


def test_title_ext_not_a_substring_match():
    a = {"artist": "X", "title": "Forever"}
    b = {"artist": "Y", "title": "A Dream Goes On Forever"}
    assert pair_features(a, b)["title_ext"] is False
