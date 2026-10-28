"""rosbag2lerobot.py に「途中の停止フレームを除く」処理を追加する（1回だけ実行）。"""
import re, shutil, sys
path = sys.argv[1] if len(sys.argv) > 1 else "scripts/rosbag2lerobot.py"
src = open(path).read()
if "drop_pauses" in src:
    sys.exit("既に適用済みです")
shutil.copy(path, path + ".before_pause")

helper = '''PAUSE_EPS_RAD = 0.005   # 状態も指令もこれ以上変わらないフレームを「停止」とみなす[rad]


def drop_pauses(j_pos, a_pos, eps=PAUSE_EPS_RAD):
    """直前に残したフレームから、アームの状態も指令も eps 以上変わっていないフレームを除く。"""
    keep = [0]
    for i in range(1, len(j_pos)):
        k = keep[-1]
        if (np.abs(j_pos[i, :4] - j_pos[k, :4]).max() > eps
                or np.abs(a_pos[i, :4] - a_pos[k, :4]).max() > eps):
            keep.append(i)
    return np.array(keep)


def load_config_py('''

pat = re.compile(r"^(\s*)a_pos_full = np\.hstack\(.*$", re.M)
add = ("keep = drop_pauses(j_pos_sampled, a_pos_full)\n"
       "{i}print(f\"  pauses removed: {{num_frames}} -> {{len(keep)}} frames\")\n"
       "{i}j_pos_sampled = j_pos_sampled[keep]\n"
       "{i}a_pos_full = a_pos_full[keep]\n"
       "{i}num_frames = len(keep)")
src, n = pat.subn(lambda m: m.group(0) + "\n" + m.group(1) + add.format(i=m.group(1)), src)
if n != 1 or src.count("def load_config_py(") != 1 or "for i in range(num_frames):" not in src:
    shutil.copy(path + ".before_pause", path)
    sys.exit(f"想定外の構造のため中止しました（置換 {n} 箇所）。元に戻しました")
src = src.replace("def load_config_py(", helper, 1)
open(path, "w").write(src)
print(f"適用しました。元のファイル: {path}.before_pause")
