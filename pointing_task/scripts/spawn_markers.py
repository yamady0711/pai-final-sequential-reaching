#!/usr/bin/env python3
"""点検ポイント（半透明の球）を Ignition Gazebo に配置する。

見た目だけのマーカー（collision なし・static）なので、ロボットの動きには影響しない。
使い方:
    python3 spawn_markers.py --config ../config/points.yaml
位置を変えたいときは Gazebo を再起動してから再実行する（同名モデルは重複配置できない）。
"""
import argparse
import shutil
import subprocess

import yaml

SDF_TEMPLATE = """<?xml version="1.0"?>
<sdf version="1.8">
  <model name="{name}">
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <geometry><sphere><radius>{radius}</radius></sphere></geometry>
        <material>
          <ambient>{rgba}</ambient>
          <diffuse>{rgba}</diffuse>
        </material>
        <transparency>{transparency}</transparency>
      </visual>
    </link>
  </model>
</sdf>
"""


def create_cmd():
    """Humble では ros_gz_sim、古い環境では ros_ign_gazebo に create がある。"""
    for pkg in ("ros_gz_sim", "ros_ign_gazebo"):
        r = subprocess.run(["ros2", "pkg", "prefix", pkg], capture_output=True)
        if r.returncode == 0:
            return ["ros2", "run", pkg, "create"]
    raise RuntimeError("ros_gz_sim / ros_ign_gazebo が見つかりません")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="../config/points.yaml")
    ap.add_argument("--marker-radius", type=float, default=None,
                    help="球の半径[m]。省略時は到達判定の radius と同じ")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    radius = args.marker_radius or cfg["radius"]
    base = create_cmd()

    for p in cfg["points"]:
        r, g, b, a = p["rgba"]
        sdf = SDF_TEMPLATE.format(
            name=f"point_{p['name']}",
            radius=radius,
            rgba=f"{r} {g} {b} 1",
            transparency=1.0 - a,
        )
        x, y, z = (a + b for a, b in zip(p["xyz"], cfg.get("gazebo_offset", [0, 0, 0])))
        cmd = base + ["-name", f"point_{p['name']}", "-string", sdf,
                      "-x", str(x), "-y", str(y), "-z", str(z)]
        print(f"[spawn] point_{p['name']} at ({x}, {y}, {z})")
        subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
