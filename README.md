# trackmatch

Probabilistic stream-to-local music track matcher.

Given a playlist entry pointing at a stream (Deezer, Spotify, Bandcamp, ...),
decide with a scored confidence whether a local library track is the same
recording — and rebuild the playlist with local copies where confident.

Confidence bands:

- `auto` (>= 0.90): swap without asking.
- `review` (0.60-0.90): human-readable queue with per-signal breakdown.
- `reject` (< 0.60): leave the stream in place, report why.

The core (`src/trackmatch/`) is pure Python stdlib — deterministic,
dependency-free, reusable by any model or pipeline. Music-server specifics
live in `adapters/`.

## Quickstart

  git clone https://github.com/kiwipaulrob/trackmatch.git
  cd trackmatch
  pip install -e .[test]
  python3 -m pytest tests/ -q

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

See `docs/plans/2026-11-10-trackmatch-a.md` for the build plan and
`docs/design.md` for why probabilistic.
