# trackmatch (Option A) Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** A probabilistic stream-to-local track matcher that scores candidate pairs with confidence bands (auto / review / reject) instead of binary rules.

**Architecture:** Pure-stdlib Python core (`normalize` → `features` → `score` → `bands`), a Music Assistant adapter for the offline library index and playlist rebuilds, a JSONL/HTML review queue, and a comparison harness that replays swept playlists as ground truth. Judge tier (local yes/no model) deferred until the scorer is validated.

**Tech Stack:** Python 3.11+ stdlib only in core (`difflib`, `unicodedata`, `re`); optional `rapidfuzz` accelerator; `pytest` for tests; MIT license.

---

## Conventions for every task

- TDD: failing test first, run it, minimal implementation, run again, commit.
- Test command: `python3 -m pytest tests/ -q` from repo root (add `-k name` for one test).
- Commit style: `feat:`, `fix:`, `test:`, `docs:` prefixes.
-ien Do NOT add dependencies to core. Anything non-stdlib goes in `adapters/` with a guarded import.
- Deterministic: no randomness, no wall-clock, no network in core. Same inputs → byte-identical outputs.

## Repo layout (target)

  trackmatch/
    src/trackmatch/__init__.py
    src/trackmatch/normalize.py     # artist/title/album cleaning
    src/trackmatch/similarity.py    # string sim (stdlib + optional rapidfuzz)
    src/trackmatch/features.py      # pair → named signal dict
    src/trackmatch/score.py         # weights → confidence + band
    src/trackmatch/bands.py         # thresholds, band assignment
    src/trackmatch/review.py        # review-queue JSONL + HTML report
    src/trackmatch/harness.py       # ground-truth replay + comparison
    src/trackmatch/adapters/ma.py   # Music Assistant index + rebuild (later phase)
    tests/fixtures/pairs.jsonl      # labelled pairs from swept playlists
    tests/test_*.py
    docs/plans/ (this file)

---

## Phase 0 — Skeleton

### Task 1: Project skeleton

**Objective:** Creatable, installable package layout with license and README.

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE` (MIT, author Paul Robertson)
- Create: `README.md` (what/why/bands/quickstart placeholder)
- Create: `src/trackmatch/__init__.py` (exports `__version__ = "0.1.0"`)
- Create: `tests/__init__.py`

**Step 1:** Write `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "trackmatch"
version = "0.1.0"
description = "Probabilistic stream-to-local music track matcher"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"

[project.optional-dependencies]
speed = ["rapidfuzz>=3.0"]
test = ["pytest>=8.0"]

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2:** Verify: `python3 -c "import sys; sys.path.insert(0,'src'); import trackmatch; print(trackmatch.__version__)"` → prints `0.1.0`.

**Step 3:** Commit: `git add -A && git commit -m "feat: project skeleton (stdlib-only core)" && git push`.

### Task 2: Ground-truth fixture extractor

**Objective:** Derive labelled old→new pairs from sweep snapshots + live MA state later; for now, lock the pair schema with hand-written seed pairs from known sweeps.

**Files:**
- Create: `tests/fixtures/pairs.jsonl`
- Create: `tests/test_fixtures.py`

**Step 1: Write failing test** (`tests/test_fixtures.py`):

```python
import json

REQUIRED = {"old_artist", "old_title", "old_album", "old_provider",
            "new_artist", "new_title", "new_album", "label", "note"}

def test_fixture_schema():
    bad = []
    with open("tests/fixtures/pairs.jsonl") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if set(row) != REQUIRED or row["label"] not in ("same", "different"):
                bad.append(i)
    assert not bad, f"bad fixture lines: {bad}"

def test_fixtures_nonempty():
    with open("tests/fixtures/pairs.jsonl") as f:
        rows = [l for l in f if l.strip()]
    assert len(rows) >= 20, "need >=20 seed pairs"
```

**Step 2:** Run → FAIL (file missing).

**Step 3:** Write `tests/fixtures/pairs.jsonl` with ≥20 seed pairs, one JSON object per line, keys exactly:
`old_artist old_title old_album old_provider new_artist new_title new_album label note`.
Labels: `same` (known-good swaps, e.g. Charli xcx Brat run from pl-1144 dry-run log, Teleost/Navigator Bandcamp→local, artist-drift cases like "The Chills" vs "Chills"), `different` (wrong-edition traps: live vs studio, remix vs original, cover vs original, same title different artist).

**Step 4:** Run tests → PASS. Commit (`test: fixture schema + seed pairs`).

---

## Phase 1 — Normalization (fold in missing-track-recovery + beets rules)

### Task 3: Basic cleaning

**Objective:** `normalize.clean_title` / `clean_artist` handle the trivial cases.

**Files:**
- Create: `src/trackmatch/normalize.py`
- Create: `tests/test_normalize.py`

**Step 1: Write failing tests:**

```python
from trackmatch.normalize import clean_title, clean_artist

def test_strips_track_numbers():
    assert clean_title("07 Summer of Love") == "summer of love"
    assert clean_title("1-02 Five") == "five"

def test_case_and_punctuation():
    assert clean_title("Brat!") == "brat"
    assert clean_artist("Charli XCX") == "charli xcx"

def test_ampersand():
    assert clean_artist("Simon & Garfunkel") == "simon and garfunkel"
```

**Step 2:** Run → FAIL. **Step 3:** Implement (lowercase, strip leading `NN` / `N-NN` track numbers, `&`→`and`, drop non-alphanumerics except spaces, collapse whitespace). **Step 4:** PASS. Commit.

### Task 4: Parentheticals and feat handling

**Objective:** Reduced-weight segments: `(demo)`, `[remaster]`, `feat. X` must not dominate, but must be retained as signals.

**Files:**
- Modify: `src/trackmatch/normalize.py` — add `split_version(title)` returning `(base, segments[])`
- Modify: `tests/test_normalize.py`

Tests:

```python
from trackmatch.normalize import split_version

def test_parenthetical_split():
    base, segs = split_version("Song (demo)")
    assert base == "song" and segs == ["demo"]

def test_feat_split():
    base, segs = split_version("Song feat. Someone")
    assert base == "song" and "feat someone" in segs

def test_the_prefix_kept_but_noted():
    base, segs = split_version("The Chills - Heavenly Pop Hit")
    assert base == "the chills - heavenly pop hit"  # artist-side handled separately
```

Implement with regexes for `(...)`, `[...]`, `\b(feat|ft|featuring)\b.*$`. Commit.

### Task 5: Artist variants ("X, The", VA markers)

**Objective:** `clean_artist` maps "Chills, The"→"the chills", VA markers ("various artists", "va", "unknown", "")→"" so VA never penalizes.

Tests: `clean_artist("Chills, The") == "the chills"`; `clean_artist("Various Artists") == ""`. Commit.

---

## Phase 2 — Similarity + features + score

### Task 6: String similarity with optional rapidfuzz

**Objective:** `similarity.ratio(a, b)` → 0..1; uses rapidfuzz if installed, else `difflib.SequenceMatcher`; identical outputs within 0.01 on fixtures.

**Files:** Create `src/trackmatch/similarity.py`, `tests/test_similarity.py`.
Tests: `ratio("brat","brat")==1.0`; `ratio("","x")==0.0`; `0.5 < ratio("summer of love","summer of love remastered") < 1.0`; backend name exposed as `similarity.BACKEND` in ("rapidfuzz","stdlib"). Commit.

### Task 7: Feature extraction

**Objective:** `features.pair_features(old, new)` where each side is a dict with `artist/title/album/duration/provider` → dict of named signals:
`artist_sim, title_sim, title_base_sim, album_sim, duration_delta (seconds, None if unknown), provider_equal (bool), version_conflict (bool: one side has remix/live/demo segment the other lacks)`.

Tests: build from two fixture rows (one `same`, one `different`), assert signal directions (e.g. `version_conflict is True` for remix-vs-original pair; `duration_delta` None when missing). Commit.

### Task 8: Weighted scorer + bands

**Objective:** `score.score(feats)` → `(confidence 0..1, breakdown dict)`; `bands.assign(confidence, feats)` → `"auto" | "review" | "reject"` with hard rules: `version_conflict` caps at `review`; `provider_equal and title_base_sim==1.0 and artist_sim>0.9` → ≥0.95.

Initial weights (tune in Phase 4): title_base 0.40, artist 0.25, title_full 0.10, album 0.10, duration 0.10, provider 0.05. Thresholds: auto ≥0.90, review 0.60–0.90, reject <0.60.

**Files:** Create `src/trackmatch/score.py`, `src/trackmatch/bands.py`, `tests/test_score.py`.
Tests:
- Brat-run fixture pair → band `auto`.
- Remix-vs-original pair → band ≤ `review`.
- Same-title-different-artist pair → `reject`.
- `score()` output JSON-serializable; breakdown weights sum to confidence within 1e-9.
Commit.

---

## Phase 3 — Harness (parallel fine-tune vs old matcher)

### Task 9: Ground-truth replay from snapshots

**Objective:** `harness.replay_playlist(snapshot_path)` yields `(old_entry, new_entry_or_None)` pairs by joining snapshot `songs[]` (pre-swap) with the CURRENT live MA playlist at the same positions. Read-only.

**Files:** Create `src/trackmatch/harness.py`, `tests/test_harness.py` (mock MA client returning canned playlist JSON; assert positional join + label derivation: same position, different URI → candidate `same`).

Note: needs MA read access; test with fakes, run for real in Task 10. Commit.

### Task 10: Old-vs-new comparison report

**Objective:** `harness.compare(snapshot_paths, old_match_fn, report_path)` runs the OLD binary matcher (`plan()` from dj_playlist_local_sweep, imported, dry-run only) and the NEW scorer over the same entries and writes per-entry agreement/disagreement JSONL: `{pos, old_uri, old_match_decision, new_confidence, new_band, agree}`.

Run for real against ≥5 already-swept playlists (June Dandelion set). Success criterion for Phase 3: new scorer reproduces 100% of old correct swaps (no `auto`→miss regressions) — disagreements must all be old-miss/new-catch or review-queue upgrades. Commit code + report sample (reports/ dir, gitignored except samples).

### Task 11: Weight tuning loop

**Objective:** Grid-search weights/thresholds against fixture + replay labels to minimize review-queue size at zero auto-errors. `harness.tune(pairs, grid)` → best params + metrics table. Document chosen params in `docs/weights.md` with the metric table. Commit.

---

## Phase 4 — Review queue + MA adapter + pilot

### Task 12: Review queue output

**Objective:** `review.write_report(rows, path_jsonl, path_html)` — JSONL machine log + single-file HTML table (no JS deps) with signal breakdowns per row. Test: write 3 rows, assert both files parse and contain all positions. Commit.

### Task 13: MA adapter — offline library index

**Objective:** `adapters/ma.build_index(ma_client)` pulls the full local library ONCE → list of candidate dicts; `find_candidates(entry, index, k=8)` returns top-k by cheap prefilter (title_base token overlap) for full scoring. Prefilter must run 4k entries × 100k library in <60s on this host (test with synthetic data). Commit.

### Task 14: KEXP pilot (new engine, dry-run)

**Objective:** Run index + scorer over the 7 KEXP monthlies, dry-run only. Compare swap counts vs old matcher projections. Write `docs/kexp-pilot.md` with the numbers. No MA writes in this task. Commit docs.

### Task 15: Cutover + publish

**Objective:** `adapters/ma.rebuild_playlist` (snapshot → remove → add → verify, ported semantics from sweep script), README quickstart, `docs/design.md` (why probabilistic, beets/Splink lineage, judge-tier interface reserved), tag `v0.1.0`, `git push --tags`. B-interface note: matcher consumes candidates from ANY source — document the seam where the Phase-B fingerprint index will plug in.

---

## Out of scope (Phase B, later)

Audio fingerprinting, tree merge authority, downloader integration, judge-tier model. The `judge` protocol stub (`score.py` reserves `judge_prob` as an optional additive signal, default None) is the only forward hook.

## Verification checklist (before v0.1.0)

- [ ] `python3 -m pytest tests/ -q` all green on stdlib-only install
- [ ] Replay over ≥5 swept playlists: zero auto-band regressions vs old matcher
- [ ] KEXP pilot numbers documented
- [ ] No core import outside stdlib (`python3 -c` assert scan in CI)
- [ ] README quickstart works verbatim on a fresh clone
