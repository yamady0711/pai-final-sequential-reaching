"""infer.py に「観測を学習データの範囲に制限する」処理を追加する（1回だけ実行）。
環境変数 OBS_RANGE に範囲ファイル（JSON: min / max）を指定したときだけ有効。未指定なら従来どおり。"""
import shutil, sys
path = sys.argv[1] if len(sys.argv) > 1 else "scripts/infer.py"
src = open(path).read()
if "OBS_RANGE" in src:
    sys.exit("既に適用済みです")
shutil.copy(path, path + ".orig")
anchor_imp = "import numpy as np\n"
anchor_obs = "self.latest_joint_state = np.array(arm_pos + [gripper_pos], dtype=np.float32)\n"
if src.count(anchor_imp) != 1 or src.count(anchor_obs) != 1:
    sys.exit("想定外の構造のため中止しました（何も変更していません）")
src = src.replace(anchor_imp, anchor_imp + '''import os, json
_RANGE = os.environ.get("OBS_RANGE")
if _RANGE:
    _r = json.load(open(_RANGE))
    OBS_LO = np.array(_r["min"], dtype=np.float32)
    OBS_HI = np.array(_r["max"], dtype=np.float32)
    print(f"[obs clip] ON: {_RANGE}")
else:
    OBS_LO = OBS_HI = None
''', 1)
line = [l for l in src.splitlines(True) if anchor_obs in l][0]
indent = line[:len(line) - len(line.lstrip())]
src = src.replace(line, line + indent + "if OBS_LO is not None:\n" + indent +
                  "    self.latest_joint_state = np.clip(self.latest_joint_state, OBS_LO, OBS_HI)\n", 1)
open(path, "w").write(src)
print(f"適用しました。元のファイル: {path}.orig")
