# trackmatch design

## Why probabilistic

The binary matcher it replaces answered one question — "is this the same
track, yes or no?" — with fingerprint rules. Every miss was a dead end and
every verdict was silent. In practice most pairs are not yes-or-no:

- exact agreement on artist + title + album (swap with confidence),
- exact agreement but one side says "(remix)" (never swap, but say why),
- same title, different artist (a cover — reject, say why),
- "French Disko" vs "French Disco" (probably the same, human confirms).

Scored confidence with per-signal breakdowns turns those into three bands
(auto / review / reject) plus a review queue a human can clear in minutes.
The score is deterministic: same inputs, same number, everywhere.

## Lineage

- beets autotagger (`beets/autotag/distance.py`, MIT): weighted per-field
  penalties, length-normalized string distance with reduced weights for
  "the"/"feat."/parentheticals, recommendation bands from thresholds.
  trackmatch's scorer is this pattern retuned for stream→local matching.
- Splink (UK Ministry of Justice, MIT): Fellegi-Sunter linkage — compare
  pairs on levels, sum log-likelihood weights. Borrowed as the mental
  model; the dependency (Spark/DuckDB) stays out at our scale.
- The `music-assistant` and `missing-track-recovery` Hermes skills encode
  hard-won API truths (search returns fragments; title-only fallback;
  title-cleaning order) that the MA adapter must respect.

## What the model judge is for (and not for)

A local yes/no decision model (e.g. gutsy, Apache 2.0, 0.8B GGUF on CPU)
may vote ONLY on the review band, and its probability is one more logged
signal blended 80/20 — never a silent override. It is off by default. The
deterministic scorer stays the authority because close-pair judging and
number comparison are documented weaknesses of small decision models, and
durations/similarities are computed in code, never by the model.

## Phase-B seam

The matcher consumes local candidates from ANY source through plain dicts
(`artist/title/album/duration/provider`). Today that is the MA library
index; tomorrow a chromaprint/AcoustID fingerprint index plugs into the
same seam with no scorer changes.
