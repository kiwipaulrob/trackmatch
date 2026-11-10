import html
import json

from trackmatch.review import write_report


def _rows():
    return [
        {"pos": 1, "old": {"artist": "A", "title": "One", "uri": "deezer--X://t/1"},
         "new": {"artist": "A", "title": "One", "uri": "library://track/11"},
         "confidence": 0.925, "band": "auto",
         "breakdown": {"parts": {"title_base": 1.0}, "weights": {"title_base": 0.4}}},
        {"pos": 2, "old": {"artist": "B", "title": "Two (remix)", "uri": "deezer--X://t/2"},
         "new": {"artist": "B", "title": "Two", "uri": "library://track/22"},
         "confidence": 0.90, "band": "review",
         "breakdown": {"parts": {"title_base": 1.0}, "weights": {"title_base": 0.4}}},
        {"pos": 3, "old": {"artist": "C", "title": "Three & More", "uri": "spotify--Y://t/3"},
         "new": None, "confidence": 0.10, "band": "reject",
         "breakdown": {"parts": {}, "weights": {}}},
    ]


def test_jsonl_roundtrip(tmp_path):
    jp = tmp_path / "review.jsonl"
    hp = tmp_path / "review.html"
    write_report(_rows(), str(jp), str(hp))
    with open(jp) as f:
        back = [json.loads(l) for l in f if l.strip()]
    assert len(back) == 3
    assert back[0]["band"] == "auto" and back[2]["new"] is None


def test_html_contains_all_positions_and_escapes(tmp_path):
    jp = tmp_path / "review.jsonl"
    hp = tmp_path / "review.html"
    write_report(_rows(), str(jp), str(hp))
    text = hp.read_text()
    for pos in ("1", "2", "3"):
        assert f">{pos}<" in text or f"pos {pos}" in text
    assert "Three &amp; More" in text  # escaped, not raw &
    assert "Three & More" not in text.replace("&amp;", "")
    assert text.startswith("<!DOCTYPE html>")
