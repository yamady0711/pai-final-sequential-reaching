#!/usr/bin/env bash
# 学習済み方策を N 回試行して自動評価する。Ctrl+C 1回で全体を止める。
# 使い方: N=20 AMP=0.05 ./run_eval.sh <model-path>
#        OFFSET="-0.05,0,0,0" で初期姿勢を決まった量だけずらす（joint1〜4の順）
set -u
MODEL=${1:?"usage: run_eval.sh <model-path>"}
N=${N:-20}; SEED0=${SEED0:-1000}; AMP=${AMP:-0.0}; OFFSET=${OFFSET:-0,0,0,0}
TRAIN_DIR=${TRAIN_DIR:-$HOME/pai_training}
HERE=$(cd "$(dirname "$0")" && pwd)
CFG="$HERE/../config/points.yaml"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT=${OUT:-"$HERE/../results/eval_${STAMP}.jsonl"}
LOGDIR="$HERE/../results/logs_${STAMP}"
mkdir -p "$LOGDIR"
EV=""; INF=""

stop_children() {
  [ -n "$INF" ] && kill -KILL -- -"$INF" 2>/dev/null
  [ -n "$EV" ] && kill -KILL "$EV" 2>/dev/null
  INF=""; EV=""
}
on_interrupt() {
  echo; echo "=== 中断しました（ここまでの結果: $OUT）"
  stop_children
  [ -s "$OUT" ] && python3 "$HERE/summarize.py" "$OUT"
  exit 130
}
trap on_interrupt INT TERM

for i in $(seq 0 $((N - 1))); do
  seed=$((SEED0 + i))
  echo "=== trial $i / seed $seed ==="
  python3 "$HERE/reset_pose.py" --seed "$seed" --amp "$AMP" --offset="$OFFSET"
  python3 "$HERE/pointing_evaluator.py" --config "$CFG" --out "$OUT" \
    --trial "$i" --seed "$seed" --amp "$AMP" --model "$MODEL" &
  EV=$!
  setsid bash -c "cd '$TRAIN_DIR' && exec pixi run infer --model-path '$MODEL'" \
    > "$LOGDIR/infer_$i.log" 2>&1 &
  INF=$!
  wait "$EV"
  EV=""
  stop_children
  sleep 1
done

echo
python3 "$HERE/summarize.py" "$OUT"
echo "results: $OUT"
