#!/usr/bin/env python3
"""Replay swept playlists through the trackmatch scorer (READ-ONLY).

For each pre-swap snapshot, positionally join with the live playlist,
score every performed swap with the new engine, and report
reproduced / missed / agree-keep verdicts.

Usage:
  replay_sweep.py [--snap-dir D] [--out review.jsonl] [pid ...]

No mutation calls: only music/playlists/playlist_tracks reads.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))
sys.path.insert(0, os.environ.get("MA_SCRIPTS_DIR", "/root/.hermes/scripts"))

import ma_playlist_lib as mplib  # noqa: E402
from trackmatch import bands  # noqa: E402
from trackmatch.features import pair_features  # noqa: E402
from trackmatch.harness import (compare_decisions, replay_playlist,  # noqa: E402
                                summarize)
from trackmatch.score import score  # noqa: E402


def artists_str(t):
    return ", ".join(a.get("name", "?") for a in (t.get("artists") or []))


def album_str(t):
    alb = t.get("album") or {}
    if isinstance(alb, dict):
        return alb.get("name", "")
    return str(alb)


class MAClient:
    def __init__(self, token):
        self.token = token

    def playlist_tracks(self, pid):
        try:
            tr = mplib._api(
                self.token,
                {"message_id": "t", "command": "music/playlists/playlist_tracks",
                 "args": {"item_id": str(pid),
                          "provider_instance_id_or_domain": "library"}},
                timeout=60)
        except Exception as e:
            print(f"  fetch pid {pid} failed: {e}")
            return []
        if not isinstance(tr, list):
            return []
        out = []
        for t in sorted(tr, key=lambda x: x.get("position", 0)):
            uri = t.get("uri", "")
            out.append({
                "artist": artists_str(t),
                "title": t.get("name", "?"),
                "uri": uri,
                "album": album_str(t),
                "duration": t.get("duration"),
                "provider": uri.split("://")[0].split("--")[0]
                if "://" in uri else "",
            })
        return out


def new_fn(old, new):
    if new is None:
        return 0.0, "reject"
    feats = pair_features(old, new)
    conf, _ = score(feats)
    return conf, bands.assign(conf, feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pids", nargs="*")
    ap.add_argument("--snap-dir",
                    default=os.environ.get("MA_SWEEP_SNAP_DIR",
                                           "/root/.hermes/data/playlist-sweep-snapshots"))
    ap.add_argument("--out", default="replay-verdicts.jsonl")
    args = ap.parse_args()

    snaps = []
    if args.pids:
        for pid in args.pids:
            p = os.path.join(args.snap_dir, "pl-%s.json" % pid)
            if os.path.exists(p):
                snaps.append(p)
            else:
                print(f"no snapshot for pid {pid}")
    else:
        snaps = sorted(
            os.path.join(args.snap_dir, f) for f in os.listdir(args.snap_dir)
            if f.startswith("pl-") and f.endswith(".json"))

    token = mplib.get_ma_token()
    ma = MAClient(token)
    all_rows, totals = [], {}
    with open(args.out, "w") as f:
        for snap in snaps:
            pairs = list(replay_playlist(snap, ma))
            rows = compare_decisions(pairs, new_fn)
            counts = summarize(rows)
            swaps = sum(1 for r in rows if r["swapped"])
            pid = os.path.basename(snap)
            print(f"{pid}: {len(rows)} positions, {swaps} swaps -> {counts}")
            for r in rows:
                r["snapshot"] = pid
                f.write(json.dumps(r) + "\n")
            all_rows.extend(rows)
    totals = summarize(all_rows)
    n_swaps = sum(1 for r in all_rows if r["swapped"])
    rep = totals.get("reproduced", 0)
    print(f"TOTAL: {len(all_rows)} positions, {n_swaps} performed swaps, "
          f"reproduced {rep}/{n_swaps} -> {totals}")


if __name__ == "__main__":
    main()
