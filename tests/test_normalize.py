from trackmatch.normalize import clean_artist, clean_title, split_version


def test_strips_track_numbers():
    assert clean_title("07 Summer of Love") == "summer of love"
    assert clean_title("1-02 Five") == "five"
    assert clean_title("12 - 05 Song") == "song"


def test_case_and_punctuation():
    assert clean_title("Brat!") == "brat"
    assert clean_title("Girl, so confusing") == "girl so confusing"
    assert clean_artist("Charli XCX") == "charli xcx"


def test_ampersand():
    assert clean_artist("Simon & Garfunkel") == "simon and garfunkel"


def test_whitespace_collapse():
    assert clean_title("  Talk   talk  ") == "talk talk"


def test_empty_and_none():
    assert clean_title("") == ""
    assert clean_title(None) == ""
    assert clean_artist(None) == ""


def test_parenthetical_split():
    base, segs = split_version("Song (demo)")
    assert base == "song" and segs == ["demo"]


def test_bracket_split():
    base, segs = split_version("Song [remastered]")
    assert base == "song" and segs == ["remastered"]


def test_feat_split():
    base, segs = split_version("Song feat. Someone")
    assert base == "song" and segs == ["feat someone"]
    base, segs = split_version("Song ft Someone Else")
    assert base == "song" and segs == ["ft someone else"]


def test_no_segments():
    assert split_version("Plain Song") == ("plain song", [])


def test_artist_the_reorder():
    assert clean_artist("Chills, The") == "the chills"


def test_va_markers():
    for va in ("Various Artists", "various", "VA", "unknown", ""):
        assert clean_artist(va) == "", va


def test_diacritics_folded_not_deleted():
    from trackmatch.normalize import clean_artist, clean_title
    assert clean_title("Ísjaki") == clean_title("Isjaki") == "isjaki"
    assert clean_artist("Sigur Rós") == clean_artist("Sigur Ros")
    assert clean_artist("Ságan") == "sagan"
    assert clean_title("Calígula") == "caligula"
