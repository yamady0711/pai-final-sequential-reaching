#!/usr/bin/env python3
"""アームを直立姿勢（全関節0）へ戻す。--amp を与えると seed 付きの小さな摂動を加える。

評価の各試行の前に呼ぶ。摂動量を変えると「初期姿勢のずれに方策がどこまで耐えるか」を測れる。
注意: テレオペノードは止めておくこと（20Hzで指令を出し続けて上書きするため）。
使い方:
    python3 reset_pose.py                  # 厳密に0へ
    python3 reset_pose.py --seed 1000 --amp 0.05
"""
import argparse
import random
import time

import rclpy
from builtin_interfaces.msg import Duration
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

TOPIC = "/crane_plus_arm_controller/joint_trajectory"
# 要確認: ros2 topic echo /joint_states --once で名前が一致するか
JOINTS = ["crane_plus_joint1", "crane_plus_joint2",
          "crane_plus_joint3", "crane_plus_joint4"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--amp", type=float, default=0.0, help="ランダム摂動の最大値[rad]")
    ap.add_argument("--offset", default="0,0,0,0",
                    help="決まった量のずれ[rad]。joint1,joint2,joint3,joint4 の順にカンマ区切り")
    ap.add_argument("--move-sec", type=float, default=2.0)
    ap.add_argument("--settle-sec", type=float, default=1.5)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    offset = [float(v) for v in args.offset.split(",")]
    assert len(offset) == len(JOINTS), "--offset には4つの値を指定してください"
    target = [o + rng.uniform(-args.amp, args.amp) for o in offset]

    rclpy.init()
    node = Node("reset_pose")
    pub = node.create_publisher(JointTrajectory, TOPIC, 10)

    # コントローラが購読を始めるまで待つ
    t_end = time.time() + 5.0
    while pub.get_subscription_count() == 0 and time.time() < t_end:
        rclpy.spin_once(node, timeout_sec=0.1)

    msg = JointTrajectory()
    msg.joint_names = JOINTS
    pt = JointTrajectoryPoint()
    pt.positions = target
    sec = int(args.move_sec)
    pt.time_from_start = Duration(sec=sec, nanosec=int((args.move_sec - sec) * 1e9))
    msg.points = [pt]
    pub.publish(msg)
    node.get_logger().info(f"reset -> {[round(v, 3) for v in target]} (seed={args.seed})")

    time.sleep(args.move_sec + args.settle_sec)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
