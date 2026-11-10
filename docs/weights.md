# trackmatch weights and bands

## Weights (unchanged since init)

title_base 0.40, artist 0.25, title_full 0.10, album 0.10, duration 0.10,
provider 0.05. Unknown album/duration score neutral 0.5; provider scores
1.0 when equal, 0.5 otherwise (absence of evidence, not disagreement).

No weight tuning was needed: replay shortfalls were fixed with two
fast-lane rules instead (see below). Grid search over weights remains
open if the review queue grows in pilot.

## Bands

- auto: confidence >= 0.90, OR any fast lane below (all require no
  version_conflict; conflict caps at review).
- review: confidence >= 0.60.
- reject: below 0.60, or artist_sim < 0.35 (artist mismatch forces
  reject even at high title agreement — covers/coincidences).
- Exact lane: title_base_sim == 1.0 and artist_sim >= 0.9 -> auto.
- Containment lane (10 Nov 2026): title_base_sim == 1.0 and
  artist_contained (one credit's tokens subset of the other's, both
  known) -> auto. Covers feat. narrowing/widening
  ("Chief Keef, Akachi" -> "Chief Keef").
- Extension lane (10 Nov 2026): title_ext and artist_sim == 1.0 -> auto.
  title_ext = longer base starts with shorter base at a word boundary,
  extension carries no version words, both artists known. Covers
  subtitle appends ("Imanin" -> "Imanin bas zihoun"). Deliberately
  blocked for "Jesus" -> "Jesus Skit": skit/skito/interlude/intro/outro
  were added to VERSION_WORDS as separate recordings, not the song.

## Replay validation (10 Nov 2026, 7 swept playlists, 872 positions)

- Harness aligns snapshot songs to live tracks by URI identity
  (SequenceMatcher on URI streams), NOT by position: rebuilds that drop
  poison/unavailable entries shift later positions and naive zipping
  reports phantom swaps (pl-1144 showed 430 phantom vs 92 genuine).
- Result: 97 genuine swaps, 88 reproduced (auto), 9 missed — and all 9
  are stale-window artifacts (snapshot predates a later rebuild pass;
  old songs gone from live entirely, correctly rejected as different
  songs). Genuine record: 88/88 auto, 0 wrong rejects, 0 review.
- Replay verdicts are only meaningful with fresh snapshots: take the
  snapshot immediately pre-apply, otherwise later edits pollute the
  labels. Stale-window pairs (old URI absent from live AND paired song
  differs) must be excluded from tuning metrics.
- Verdict log: replay-verdicts.jsonl (gitignored; regenerate with
  examples/replay_sweep.py).
