#!/usr/bin/env bash
# 1つの関節だけ初期姿勢をずらし、ずれの量ごとに1回ずつ評価する。Ctrl+C 1回で中断。
# 使い方: JOINT=1 ./sweep_joint.sh <model-path>
#        DELTAS="-0.10 -0.05 0.05 0.10" でずらす量[rad]を変更できる
set -u
MODEL=${1:?"usage: JOINT=1 ./sweep_joint.sh <model-path>"}
JOINT=${JOINT:-1}
DELTAS=${DELTAS:-"-0.10 -0.05 -0.02 0.02 0.05 0.10"}
HERE=$(cd "$(dirname "$0")" && pwd)
STAMP=$(date +%Y%m%d_%H%M%S)
CSV="$HERE/../results/sweep_joint${JOINT}_${STAMP}.csv"
echo "joint,delta_rad,delta_deg,success,duration_sec,reached,reason" > "$CSV"

for d in $DELTAS; do
  off=$(python3 -c "o=['0']*4; o[$JOINT-1]='$d'; print(','.join(o))")
  out="$HERE/../results/sweep_joint${JOINT}_${STAMP}_d${d}.jsonl"
  echo "##### joint$JOINT を $d rad ずらす（offset=$off） #####"
  N=1 OFFSET="$off" OUT="$out" "$HERE/run_eval.sh" "$MODEL" || { echo "スイープを中断しました"; break; }
  python3 - "$out" "$JOINT" "$d" >> "$CSV" << 'PY'
import json, math, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
d = float(sys.argv[3])
reached = "/".join(x["name"] for x in r["reached"]) or "-"
print(f"{sys.argv[2]},{d},{math.degrees(d):.1f},{r['success']},{r['duration_sec']},{reached},{r['reason']}")
PY
done

echo
column -s, -t "$CSV" 2>/dev/null || cat "$CSV"
echo "saved: $CSV"
