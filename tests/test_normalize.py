from trackmatch.normalize import clean_artist, clean_title


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
