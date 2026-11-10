from trackmatch import similarity
from trackmatch.similarity import ratio


def test_identical_is_one():
    assert ratio("brat", "brat") == 1.0


def test_empty_is_zero():
    assert ratio("", "x") == 0.0
    assert ratio("", "") == 1.0


def test_partial_in_range():
    r = ratio("summer of love", "summer of love remastered")
    assert 0.5 < r < 1.0


def test_symmetric():
    assert ratio("abc xyz", "abc") == ratio("abc", "abc xyz")


def test_backend_exposed():
    assert similarity.BACKEND in ("rapidfuzz", "stdlib")
