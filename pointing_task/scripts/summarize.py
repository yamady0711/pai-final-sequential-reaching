#!/usr/bin/env python3
"""評価結果（JSON Lines）を集計する。
使い方: python3 summarize.py ../results/eval_xxx.jsonl
"""
import json
import statistics
import sys

rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
n = len(rows)
ok = [r for r in rows if r["success"]]
print(f"trials      : {n}")
print(f"success     : {len(ok)}  ({len(ok) / n:.0%})" if n else "no data")
if ok:
    d = [r["duration_sec"] for r in ok]
    print(f"duration[s] : mean {statistics.mean(d):.2f} / min {min(d):.2f} / max {max(d):.2f}")
fails = {}
for r in rows:
    if not r["success"]:
        fails[r["reason"]] = fails.get(r["reason"], 0) + 1
for reason, c in fails.items():
    print(f"fail reason : {reason} x{c}")
