"""rosbag2lerobot.py に「動き出し0.5秒前から変換する」処理を追加する（1回だけ実行）。"""
import re, shutil, sys
path = sys.argv[1] if len(sys.argv) > 1 else "scripts/rosbag2lerobot.py"
src = open(path).read()
if "motion_start_time" in src:
    sys.exit("既に適用済みです")
shutil.copy(path, path + ".orig")

helper = '''TRIM_EPS_RAD = 0.02     # アームのどれかの関節がこれ以上動いたら「動き出し」[rad]
TRIM_MARGIN_SEC = 0.5   # 動き出しの何秒前から変換するか


def motion_start_time(j_times, j_pos, start_time):
    """先頭の静止区間を除くため、動き出し TRIM_MARGIN_SEC 秒前の時刻[ns]を返す。"""
    pos = np.asarray(j_pos)[:, :4]          # アーム4軸（5列目のグリッパは除外）
    moved = np.any(np.abs(pos - pos[0]) > TRIM_EPS_RAD, axis=1)
    if not moved.any():
        return start_time
    t = int(j_times[int(np.argmax(moved))]) - int(TRIM_MARGIN_SEC * 1e9)
    return max(start_time, t)


def load_config_py('''

pat = re.compile(r"^(\s*)start_time = max\(j_times\[0\], a_times\[0\], g_times\[0\]\)$", re.M)
call = "start_time = motion_start_time(j_times, np.array([m.position for m, _ in messages['/joint_states']]), start_time)"
src, n = pat.subn(lambda m: m.group(0) + "\n" + m.group(1) + call, src)
if n != 2 or src.count("def load_config_py(") != 1:
    shutil.copy(path + ".orig", path)
    sys.exit(f"想定外の構造のため中止しました（置換 {n} 箇所）。元に戻しました")
src = src.replace("def load_config_py(", helper, 1)
open(path, "w").write(src)
print(f"適用しました（{n} 箇所）。元のファイル: {path}.orig")
