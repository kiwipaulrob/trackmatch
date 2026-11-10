"""Human review queue: JSONL machine log + dependency-free single-file HTML.

Rows are dicts: {pos, old{artist,title,uri}, new{...}|None, confidence,
band, breakdown{parts, weights}}. The HTML table shows every signal so a
reviewer can accept/reject without re-running anything.
"""

import html
import json


def _fmt_track(t):
    if not t:
        return "<i>none</i>"
    return "%s — %s<br><small>%s</small>" % (
        html.escape(str(t.get("artist", ""))),
        html.escape(str(t.get("title", ""))),
        html.escape(str(t.get("uri", ""))),
    )


def _fmt_breakdown(bd):
    parts = (bd or {}).get("parts", {})
    weights = (bd or {}).get("weights", {})
    cells = []
    for key in parts:
        w = weights.get(key, 0)
        cells.append("%s=%.2f (w %.2f)" % (html.escape(key), parts[key], w))
    return "<br>".join(cells) or "<i>n/a</i>"


def write_report(rows, jsonl_path, html_path):
    """Write rows to a JSONL log and a single-file HTML table."""
    rows = list(rows)
    with open(jsonl_path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    trs = []
    for row in rows:
        trs.append(
            "<tr><td>%s</td><td>%s</td><td>%s</td><td>%.3f</td>"
            "<td><b>%s</b></td><td><small>%s</small></td></tr>"
            % (
                html.escape(str(row.get("pos", ""))),
                _fmt_track(row.get("old")),
                _fmt_track(row.get("new")),
                float(row.get("confidence", 0.0)),
                html.escape(str(row.get("band", ""))),
                _fmt_breakdown(row.get("breakdown")),
            )
        )
    page = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>trackmatch review queue</title>
<style>body{font-family:sans-serif}table{border-collapse:collapse}
td,th{border:1px solid #999;padding:4px 8px;vertical-align:top}</style>
</head><body>
<h1>trackmatch review queue (%d rows)</h1>
<table><tr><th>pos</th><th>stream entry</th><th>local candidate</th>
<th>confidence</th><th>band</th><th>signals</th></tr>
%s
</table></body></html>
""" % (len(rows), "\n".join(trs))
    with open(html_path, "w") as f:
        f.write(page)
    return jsonl_path, html_path
