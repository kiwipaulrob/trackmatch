# KEXP pilot: trackmatch vs the Oct 2026 sweeps

Dry-run comparison of the new scorer against the six KEXP monthly playlists
(1609, 1579, 1578, 5474, 5475, 5498) that the October 2026 sweep scripts had
already processed. Read-only throughout: the pilot scores every entry against
a 287k-track library index and records the band it *would* assign; nothing is
swapped. Reproduce with:

  python3 examples/kexp_pilot.py --out kexp-pilot.json 1609 1579 1578 5474 5475 5498

(`kexp-pilot.json` / `kexp-pilot-index.pkl` are gitignored run artifacts.)

## Headline numbers (run of 10 Nov 2026, Jaccard prefilter)

| pid | entries | new auto | review | reject | no-cand | old swapped |
|-----|---------|----------|--------|--------|---------|-------------|
| 1609 | 697 | 295 | 63 | 320 | 19 | 251 |
| 1579 | 725 | 268 | 53 | 380 | 24 | 223 |
| 1578 | 635 | 240 | 58 | 314 | 23 | 214 |
| 5474 | 224 |  98 | 19 | 101 |  6 |  53 |
| 5475 | 513 | 185 | 32 | 282 | 14 | 167 |
| 5498 | 571 | 205 | 44 | 308 | 14 | 163 |
| total | 3365 | 1291 | 269 | 1705 | 100 | 1071 |

Agreement with the old sweep, measured at **song level** (normalized
artist+title, not library URI — this library holds several copies of many
songs, so URI equality understates agreement):

- 978 / 1071 old swaps (91.3%) pick the same song in the new engine.
- 43 true divergences (same position, different song): sampled 12, all
  new-better or equal — exact artist over compilation attribution
  ("Neil Young, Crazy Horse" not "Neil Young"), clean title over
  filename-prefixed junk ("Love Fade" not "Tamaryn - Love Fade"),
  original over remix feature ("Blinding Lights" solo, not the Rosalia
  remix), plus one corrected old false positive (Billy Stewart's
  "Summertime", which the old matcher had pointed at a "Winston Groovy"
  soundalike).
- 270 new-only swaps: sampled 12, all exact same-song matches at 0.975
  (White Fence, Courtney Barnett, Hot Chocolate, ...) the old MA-search
  matcher left on the table — a straight recall gain.
- 50 old-swapped positions the new engine does not auto-swap. Rescored
  after the fixes below: 9 auto (boundary metadata since clarified),
  24 review (genuinely ambiguous: diacritics, demos, covers, truncated
  titles — the human queue working as designed), 15 reject, 2 no-cand.

The 15 rejects include old false positives the new engine correctly
refuses: a Death Cab cover for R.E.M.'s "Fall On Me", Silver Jews for
Jeff Tweedy's "New Orleans", Sun Araw's "Beams" for Arlo Parks' "Beams",
a mariachi "Holy" for a Gelbison track. The artist-mismatch rule earns
its keep here.

## Bugs the pilot found (all fixed, all with regression tests)

1. **Prefilter drowned exact matches.** Raw token-overlap ranking + top-8
   truncation lost one-token queries ("Holy Holy") among hundreds of
   partials. Now Jaccard-ranked with a same-artist tie-break
   (`test_prefilter_exact_short_title_among_many_partials`,
   `test_prefilter_end_to_end_auto_band`). Recall effect: +52 auto-swaps
   on pid 1579 alone (216 -> 268).
2. **Diacritics deleted, not folded.** `clean_title("Ísjaki")` was "sjaki",
   `clean_artist("Sigur Rós")` was "sigur r s". `_basic` now NFKD-folds
   (`test_diacritics_folded_not_deleted`). Fixed one of three no-candidate
   misses outright.
3. **Containment vs mismatch contradiction.** `artist_contained=True`
   ("War" vs "Eric Burdon and War") was still forced to reject by the
   difflib-ratio mismatch rule. The rule now yields to containment
   (`test_contained_artist_low_ratio_not_forced_reject`).

## Replay cross-check (all swept playlists, 10 Nov 2026)

`examples/replay_sweep.py` over every pre-swap snapshot: 7238 positions,
257 performed swaps, new engine reproduces 226 (88%). The 31 misses are
unchanged before/after the three fixes above (verified by diffing verdict
sets) and are the same population as the pilot's reject/review buckets:
old false positives correctly refused, ambiguous pairs queued for review.
Replay cannot measure overreach (rejected candidates are gone from the
snapshots); the pilot's new-only sample covers that side.

## Known residual risks

- Single-token artist containment ("War" vs "War on Drugs") can auto-swap
  on an exact title; accepted as rare, same class as the documented
  feat.-narrowing lane.
- Unlabeled re-recordings with identical metadata remain indistinguishable
  (accepted, documented in `bands.py`).
- Pilot numbers drift with live playlists; rerun before treating any count
  as current.
