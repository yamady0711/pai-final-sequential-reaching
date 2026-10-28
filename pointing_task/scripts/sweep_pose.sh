#!/usr/bin/env bash
# 見て分かる初期姿勢ごとに1回ずつ評価（最終モデル・範囲制限あり）。Ctrl+C 1回で中断。
# 使い方: ./sweep_pose.sh            → 全候補
#        POSES="P1 P4 P8" ./sweep_pose.sh → 指定した姿勢だけ（録画用）
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
MODEL=/home/ubuntu/checkpoints/train/crane_plus_pointing_v2_act_n8
export OBS_RANGE=/home/ubuntu/pointing_task/config/obs_range_v2.json
declare -A OFF=(
  [P1]="0,0,0,0"      [P2]="0.5,0,0,0"   [P3]="-0.5,0,0,0"  [P4]="0,0,-0.5,0"
  [P5]="0,0.3,0,0"    [P6]="0,-0.3,0,0"  [P7]="0,0,0,0.3"   [P8]="0,0,0,-0.3" )
POSES=${POSES:-"P1 P2 P3 P4 P5 P6 P7 P8"}
STAMP=$(date +%Y%m%d_%H%M%S)
CSV="$HERE/../results/sweep_pose_${STAMP}.csv"
echo "pose,offset,success,duration_sec,reached,reason" > "$CSV"
for p in $POSES; do
  out="$HERE/../results/sweep_pose_${STAMP}_${p}.jsonl"
  echo "##### $p  offset(joint1..4)=${OFF[$p]} #####"
  N=1 OFFSET="${OFF[$p]}" OUT="$out" "$HERE/run_eval.sh" "$MODEL" || { echo "中断しました"; break; }
  python3 - "$out" "$p" "${OFF[$p]}" >> "$CSV" << 'PY'
import json, sys
r = json.loads(open(sys.argv[1]).read().splitlines()[-1])
print(f"{sys.argv[2]},\"{sys.argv[3]}\",{r['success']},{r['duration_sec']},{'/'.join(x['name'] for x in r['reached']) or '-'},{r['reason']}")
PY
done
echo; column -s, -t "$CSV"; echo "saved: $CSV"
