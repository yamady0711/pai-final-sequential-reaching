#!/usr/bin/env python3
"""点検ポイント指差しタスクの自動評価ノード（1回の試行を判定して終了する）。

TF で world -> crane_plus_link_hand を 20Hz で取得し、
A -> B -> C の順に各点の半径 radius 以内へ入れば成功とする。
結果は JSON Lines（1試行1行）で --out に追記する。

使い方（ROS 2 の環境を source したターミナルで）:
    python3 pointing_evaluator.py --config ../config/points.yaml --out ../results/test.jsonl
テレオペで手動で A->B->C をなぞって SUCCESS になるかをまず確かめること。
"""
import argparse
import json
import math
import time
from pathlib import Path

import rclpy
import yaml
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from sensor_msgs.msg import JointState
from tf2_ros import Buffer, TransformListener

JOINT_MOVE_EPS = 0.02  # [rad] どれかの関節がこれ以上動いたら「動き出し」


class PointingEvaluator(Node):
    def __init__(self, cfg, meta):
        super().__init__(
            "pointing_evaluator",
            parameter_overrides=[Parameter("use_sim_time", value=True)],
        )
        self.cfg = cfg
        self.meta = meta
        self.points = cfg["points"]
        self.buf = Buffer()
        self.listener = TransformListener(self.buf, self)

        self.idx = 0                       # 次に到達すべき点
        self.reached = []                  # [{"name", "t"}]
        self.min_dist = {p["name"]: math.inf for p in self.points}
        self.home = None                   # 初期の手先位置
        self.t_wait0 = None                # 評価開始（sim時間）
        self.t0 = None                     # 動き出した時刻（sim時間）
        self.result = None
        self.joint_home = None             # 初期の関節角
        self.joint_moved = False

        self.create_subscription(JointState, "/joint_states", self.on_joints, 10)
        self.create_timer(0.05, self.tick)
        self.get_logger().info("waiting for TF / robot motion ...")

    def on_joints(self, msg):
        """直立姿勢で joint1 だけ回すと手先がほぼ動かないため、関節角でも動き出しを判定する。"""
        q = dict(zip(msg.name, msg.position))
        if self.joint_home is None:
            self.joint_home = q
            return
        if any(abs(q[k] - self.joint_home[k]) > JOINT_MOVE_EPS
               for k in q if k in self.joint_home):
            self.joint_moved = True

    def now_sec(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def tick(self):
        if self.result is not None:
            return
        now = self.now_sec()
        if now == 0.0:                     # /clock 未受信
            return
        if self.t_wait0 is None:
            self.t_wait0 = now
        try:
            tf = self.buf.lookup_transform(
                self.cfg["frame"], self.cfg["hand_link"], Time())
        except Exception:
            return
        p = tf.transform.translation
        pos = (p.x, p.y, p.z)

        # 計時開始: 手先が初期位置から動いたら
        if self.home is None:
            self.home = pos
        if self.t0 is None:
            if self.joint_moved or math.dist(pos, self.home) > self.cfg["start_move_eps"]:
                self.t0 = now
                self.get_logger().info("motion started")
            elif now - self.t_wait0 > self.cfg["wait_start_sec"]:
                self.finish(False, "robot did not move")
            return

        elapsed = now - self.t0
        target = self.points[self.idx]
        d = math.dist(pos, target["xyz"])
        self.min_dist[target["name"]] = min(self.min_dist[target["name"]], d)

        if d <= self.cfg["radius"]:
            self.reached.append({"name": target["name"], "t": round(elapsed, 3)})
            self.get_logger().info(f"reached {target['name']} at {elapsed:.2f}s")
            self.idx += 1
            if self.idx == len(self.points):
                self.finish(True, "all points reached in order")
        elif elapsed > self.cfg["timeout_sec"]:
            self.finish(False, f"timeout before {target['name']}")

    def finish(self, success, reason):
        elapsed = None if self.t0 is None else round(self.now_sec() - self.t0, 3)
        self.result = {
            **self.meta,
            "success": success,
            "reason": reason,
            "reached": self.reached,
            "duration_sec": elapsed,
            "idle_sec": (None if self.t0 is None or self.t_wait0 is None
                         else round(self.t0 - self.t_wait0, 3)),
            "min_dist_m": {k: (None if math.isinf(v) else round(v, 4))
                           for k, v in self.min_dist.items()},
            "radius_m": self.cfg["radius"],
            "wall_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        tag = "SUCCESS" if success else "FAIL"
        self.get_logger().info(f"[{tag}] {reason}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="../config/points.yaml")
    ap.add_argument("--out", default="../results/eval.jsonl")
    ap.add_argument("--trial", type=int, default=0)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--amp", type=float, default=None)
    ap.add_argument("--model", default=None, help="評価したモデルのパス（記録用）")
    args = ap.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)
    meta = {"trial": args.trial, "seed": args.seed, "amp": args.amp,
            "model": args.model}

    rclpy.init()
    node = PointingEvaluator(cfg, meta)
    try:
        while rclpy.ok() and node.result is None:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        node.finish(False, "interrupted")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        f.write(json.dumps(node.result, ensure_ascii=False) + "\n")
    print(json.dumps(node.result, ensure_ascii=False, indent=2))

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
