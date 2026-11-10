# trackmatch

Probabilistic stream-to-local music track matcher.

Given a playlist entry pointing at a stream (Deezer, Spotify, Bandcamp,
...), decide with a scored confidence whether a local library track is
the same recording — and rebuild the playlist with local copies where
confident.

Confidence bands:

- `auto` (>= 0.90): swap without asking.
- `review` (0.60-0.90): human-readable queue with per-signal breakdown.
- `reject` (< 0.60): leave the stream in place, report why.

Built to replace a binary yes/no matcher that silently missed valid swaps
(feat. credits, subtitle extensions, regional catalogue-ID differences
slipped through) and re-searched the server once per track. trackmatch
scores a weighted basket of signals, pulls the library index once, and
puts everything it isn't sure about into a human review queue instead of
guessing.

## How it works

1. **Normalize** (`normalize.py`) — case/punctuation folding, leading track
   numbers stripped, parentheticals and feat. credits split off as version
   signals, "X, The" reordered, VA markers blanked.
2. **Features** (`features.py`) — per-pair signals: title-base similarity,
   artist similarity, full-title similarity, album, duration delta,
   provider equality, plus boolean flags: `version_conflict` (remix/live/
   demo/skit/...), `artist_contained` (feat. narrowing/widening),
   `title_ext` (subtitle appended to the same song).
3. **Score** (`score.py`) — weighted confidence: title_base 0.40, artist
   0.25, title_full / album / duration 0.10 each, provider 0.05. Unknown
   album/duration score neutral 0.5.
4. **Bands** (`bands.py`) — auto / review / reject with hard rules on top:
   - version conflict caps at review — a remix never auto-swaps;
   - artist mismatch (similarity < 0.35, both known) forces reject — same
     title + different artist is a cover or coincidence;
   - fast lanes to auto: exact title + near-exact artist; exact title +
     contained artist credit; same artist + subtitle extension.
5. **Adapter** (`adapters/ma.py`) — offline library index with title-token
   postings; top-8 candidates per entry by token overlap, full scoring on
   those. 4,000 entries x 100,000-track library prefilters in seconds.
6. **Review** (`review.py`) — JSONL machine log + single-file,
   dependency-free HTML table with per-row signal breakdowns.

A judge-tier interface is reserved in `score()` (`judge_prob` blend) for a
future fingerprint/LLM tier; the matcher consumes candidates from any
source, so a Phase-B fingerprint index plugs in at the adapter seam.

The core (`src/trackmatch/`) is pure Python stdlib — deterministic,
dependency-free, reusable by any model or pipeline. Music-server specifics
live in `adapters/`.

## Install

Stdlib only — no third-party dependencies.

    git clone https://github.com/kiwipaulrob/trackmatch.git
    cd trackmatch
    python3 -m pytest tests/ -q   # 55 tests, incl. a 4k x 100k prefilter perf test

Python 3.10+. The `examples/` runners that talk to Music Assistant need
the MA websocket helper they import via `MA_SCRIPTS_DIR` (default
`/root/.hermes/scripts`, not part of this repo); everything under `src/`
and `tests/` runs anywhere. (The `[test]` extra in `pyproject.toml` is a
leftover alias — plain `pytest` from your environment is all you need.)

## Quickstart

Score one pair:

    import sys; sys.path.insert(0, "src")
    from trackmatch.features import pair_features
    from trackmatch.score import score
    from trackmatch import bands
    old = {"artist": "Charli xcx", "title": "Von dutch",
           "album": "Brat", "provider": "deezer"}
    new = {"artist": "Charli xcx", "title": "Von dutch",
           "album": "Brat", "provider": "library"}
    feats = pair_features(old, new)
    conf, breakdown = score(feats)
    print(conf, bands.assign(conf, feats))  # 0.925 auto

Offline index over your own candidate list:

    from trackmatch.adapters.ma import build_index, find_candidates
    index = build_index(my_tracks)          # once
    cands = find_candidates(stream_entry, index)  # top-8, then score each

Review queue for the uncertain rows:

    from trackmatch.review import write_report
    write_report(rows, "review.jsonl", "review.html")

## Validation

- **Replay harness** (`harness.py`, `examples/replay_sweep.py`): 7 swept
  playlists (872 positions, 97 genuine swaps, snapshot-to-live joined by
  URI identity) — the engine auto-reproduces 88/88 genuine swaps; the 9
  residuals are stale-snapshot artifacts correctly rejected.
- **KEXP pilot** (`examples/kexp_pilot.py`, `docs/kexp-pilot.md`): 7 KEXP
  monthlies dry-run against the old binary matcher — see the doc for the
  comparison table.
- Tuning rationale and metric tables: `docs/weights.md`.

## Project layout

    src/trackmatch/          normalize, features, score, bands, harness, review
    src/trackmatch/adapters/ ma.py — library index + prefilter + fetcher
    tests/                   fixture + unit + perf tests (stdlib only)
    examples/                replay_sweep.py, kexp_pilot.py (need MA access)
    docs/                    design.md, weights.md, kexp-pilot.md, plans/

## Status

Phases 1–4 per `docs/plans/2026-11-10-trackmatch-a.md`: scorer, replay
validation, review queue, MA adapter, KEXP pilot — done. Cutover
(`rebuild_playlist`: snapshot → remove → add → verify) and `v0.1.0` tag
are next; see Task 15 in the plan.
