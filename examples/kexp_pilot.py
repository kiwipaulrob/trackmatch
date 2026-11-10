#!/usr/bin/env python3
"""KEXP pilot: run the new trackmatch engine over KEXP monthlies (DRY-RUN).

Read-only: fetches each playlist's tracks, treats every entry's
artist/title as a stream entry, runs index -> candidates -> score ->
band, and counts would-swap / review / keep / no-candidate. Compares
against the OLD binary matcher (dj_playlist_local_sweep.plan_playlist,
also read-only) on the same playlists.

Usage:
  kexp_pilot.py [--out pilot.json] pid [pid ...]
"""

import argparse
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "src"))
sys.path.insert(0, os.environ.get("MA_SCRIPTS_DIR", "/root/.hermes/scripts"))

import ma_playlist_lib as mplib  # noqa: E402

from trackmatch import bands  # noqa: E402
from trackmatch.adapters.ma import (  # noqa: E402
    build_index,
    fetch_library_tracks,
    find_candidates,
)
from trackmatch.features import pair_features  # noqa: E402
from trackmatch.score import score  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "dj_sweep",
    os.path.join(os.environ.get("MA_SCRIPTS_DIR", "/root/.hermes/scripts"),
                 "dj_playlist_local_sweep.py"))
dj_sweep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dj_sweep)


def to_entry(t):
    artists = ", ".join(a.get("name", "?") for a in (t.get("artists") or []))
    alb = t.get("album") or {}
    album = alb.get("name", "") if isinstance(alb, dict) else str(alb)
    uri = t.get("uri", "")
    provider = uri.split("://")[0].split("--")[0] if "://" in uri else ""
    return {"artist": artists, "title": t.get("name", "?"), "uri": uri,
            "album": album, "duration": t.get("duration"),
            "provider": provider}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="kexp-pilot.json")
    ap.add_argument("pids", nargs="+")
    args = ap.parse_args()

    token = mplib.get_ma_token()

    def api_call(command, payload):
        return mplib._api(token, {"message_id": "x", "command": command,
                                  "args": payload}, timeout=120)

    print("fetching library index ...", flush=True)
    lib = fetch_library_tracks(api_call)
    print(f"library tracks: {len(lib)}", flush=True)
    index = build_index(lib)

    report = {"library_size": len(lib), "playlists": []}
    for pid in args.pids:
        tracks = dj_sweep.fetch_tracks(token, pid)
        if tracks is None:
            print(f"pid {pid}: fetch failed, skipping")
            continue
        tracks = sorted(tracks, key=lambda t: t.get("position", 0))
        rows = {"pid": pid, "total": len(tracks), "auto_same": 0,
                "would_swap": 0, "review": 0, "reject": 0,
                "no_candidate": 0, "examples": []}
        for t in tracks:
            entry = to_entry(t)
            cands = find_candidates(entry, index, k=8)
            if not cands:
                rows["no_candidate"] += 1
                continue
            scored = []
            for c in cands:
                feats = pair_features(entry, c)
                conf, _ = score(feats)
                scored.append((conf, bands.assign(conf, feats), c))
            scored.sort(key=lambda s: -s[0])
            conf, band, best = scored[0]
            if band == "auto":
                if best["uri"] == entry["uri"]:
                    rows["auto_same"] += 1
                else:
                    rows["would_swap"] += 1
                    if len(rows["examples"]) < 5:
                        rows["examples"].append(
                            {"pos": t.get("position"), "entry": entry,
                             "best_uri": best["uri"], "conf": round(conf, 3)})
            elif band == "review":
                rows["review"] += 1
            else:
                rows["reject"] += 1
        _, swaps, stats = dj_sweep.plan_playlist(token, pid, delay=0.2)
        rows["old_swappable"] = stats.get("swappable", 0)
        rows["old_stats"] = stats
        rows["new_swap_uris"] = None  # filled below if needed
        print(f"pid {pid}: {rows['total']} tracks -> {rows}", flush=True)
        report["playlists"].append(rows)

    with open(args.out, "w") as f:
        json.dump(report, f, indent=1)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
