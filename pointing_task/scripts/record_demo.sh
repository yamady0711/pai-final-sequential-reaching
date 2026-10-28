#!/usr/bin/env bash
# お手本1エピソードを記録する。成功なら保存、失敗なら削除。
# 使い方: ./record_demo.sh <エピソード番号>   例: ./record_demo.sh 0
set -u
set -m   # 子プロセスがCtrl+C相当の停止信号を受け取れるようにする
EP=${1:?"usage: record_demo.sh <episode-number>"}
HERE=$(cd "$(dirname "$0")" && pwd)
BAG_ROOT=${BAG_ROOT:-$HOME/dataset/rosbags/pointing}
BAG="$BAG_ROOT/ep$EP"
LOG="$HERE/../results/demos.jsonl"

if [ -e "$BAG" ]; then echo "!!! $BAG は既にあります。番号を確認してください"; exit 1; fi
mkdir -p "$BAG_ROOT"

ros2 bag record -a -o "$BAG" < /dev/null > "/tmp/bag_ep$EP.log" 2>&1 &
BAGPID=$!
sleep 3
echo ">>> ep$EP 記録中。テレオペのターミナルをクリックしてレシピどおりに操作してください"

python3 "$HERE/pointing_evaluator.py" --out "$LOG" --trial "$EP" 2>&1 | grep -E "reached|SUCCESS|FAIL|motion"

kill -INT -- -"$BAGPID" 2>/dev/null
wait "$BAGPID" 2>/dev/null

LAST=$(tail -n 1 "$LOG")
if echo "$LAST" | grep -q '"success": true'; then
  DUR=$(echo "$LAST" | python3 -c "import json,sys;print(json.load(sys.stdin)['duration_sec'])")
  echo "=== SUCCESS: ep$EP を保存しました（${DUR}秒） → $BAG"
  echo "=== 次: テレオペで x を押してから ./record_demo.sh $((EP + 1))"
else
  rm -rf "$BAG"
  echo "=== FAIL: ep$EP を削除しました。x を押してから ./record_demo.sh $EP でやり直してください"
fi
