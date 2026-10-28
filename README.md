# 模倣学習（ACT）による物体A→B→Cへの順次到達 ― データ収集から自動評価までのRobOpsパイプライン

Physical AI 応用編1 最終課題。Ignition Gazebo上のCRANE+ V2の手先を、机上の物体A・B・Cへこの順に到達させる動作を、テレオペのお手本21本からACTで学習させた。主眼はタスクの難しさではなく、**環境・データ収集・学習・推論・評価を一つの系として自作でつなぐこと**と、**自動評価を使った失敗原因の切り分け**にある。

- 動画：YouTube（URLは提出フォームに記載）
- 本リポジトリは [matsuolab/pai_training](https://github.com/matsuolab/pai_training)（コミット `b4d6b54`）のフォークに、本課題の改造と自作コード（`pointing_task/`）を加えたもの。元のREADMEは `docs/README_pai_training.md` に残している
- 学習済みモデルとデータは Releases に置いている（モデルが154 MBでGitHubの1ファイル上限を超えるため）

## 結果

最終モデル：v2データ（途中の停止フレームを除去）で学習したACT、`n_action_steps=8`、推論時に観測を学習データの範囲に制限。

| 条件 | 初期姿勢 | 範囲制限 | 成功率 | 平均所要時間（成功時） |
| --- | --- | --- | --- | --- |
| A | 直立 | なし | 20/20 | 6.27 s |
| A' | 直立 | あり | 20/20 | 6.32 s |
| B | 全関節 ±0.05 rad 一様乱数（seed 1000–1019） | なし | 10/20 | 11.04 s |
| B' | Bと同seed | あり | 20/20 | 6.64 s |
| 参考 | テレオペのお手本 | — | 21/21 | 14.3 s |

大きな初期姿勢のずれ（1関節のみ、最終モデル）：

| 姿勢 | ずらし方 [rad] (joint1, 2, 3, 4) | 結果 |
| --- | --- | --- |
| P1 | 0, 0, 0, 0 | 成功 |
| P2 | +0.5, 0, 0, 0 | 成功 |
| P3 | −0.5, 0, 0, 0 | 失敗（3/3） |
| P4 | 0, 0, −0.5, 0 | 失敗（3/3） |
| P5 | 0, +0.3, 0, 0 | 失敗（3/3） |
| P6 | 0, −0.3, 0, 0 | 成功 |
| P7 | 0, 0, 0, +0.3 | 成功 |
| P8 | 0, 0, 0, −0.3 | 成功 |

成否は関節ごとの値域ではなく、その姿勢がお手本の軌道の周辺にあるかどうかで分かれた（推論）。詳細はレポートを参照。

## 構成

| パス | 内容 | 元リポジトリからの変更 |
| --- | --- | --- |
| `scripts/rosbag2lerobot.py` | rosbag2 → LeRobotDataset 変換 | 動き出し0.5 s前から変換（先頭の静止区間を除去）、状態・指令とも0.005 rad以上変化しないフレームを除去（v2）、末尾を最長エピソードに揃える埋め合わせを廃止 |
| `scripts/infer.py` | 推論ノード | 環境変数 `OBS_RANGE` 指定時、観測を学習データの最小・最大に制限 |
| `configs/` | 変換・学習の設定（v2） | データセット名・タスク名、`training_steps` 200→2000、`batch_size` 2→8、`delta_timestamps.action` を0.0始まりに |
| `configs/v1/` | v1（停止フレーム除去前）の設定 | 新規 |
| `pyproject.toml` / `pixi.lock` | 依存関係 | `wandb>=0.22`（講義第5回の手順） |
| `pointing_task/config/` | 物体A・B・Cの座標（TFのworld基準）・判定半径、観測の範囲（`obs_range_v2.json`） | 新規 |
| `pointing_task/scripts/` | 物体配置、評価ノード、お手本記録、初期姿勢リセット、自動評価、スイープ、集計 | 新規 |
| `pointing_task/pai_training_patches/` | 上記の改造を行ったパッチスクリプト（記録用。本リポジトリでは適用済み） | 新規 |
| `pointing_task/results/` | お手本の台帳（`demos.jsonl`）と評価結果 | 新規 |

`pointing_task/scripts/` の主なファイル：

- `spawn_markers.py`：物体A・B・C（半透明の球、接触判定なし）をGazeboに配置
- `pointing_evaluator.py`：評価ノード。TFで手先位置を追い、A→B→Cの到達を自動判定してJSONLに記録
- `record_demo.sh`：お手本1本の記録（rosbag2）と採点。失敗したエピソードは自動削除
- `reset_pose.py`：初期姿勢への復帰（ランダム摂動 `--amp` ／ 固定オフセット `--offset`）
- `run_eval.sh`：N回の自動評価（リセット → 評価ノード → 推論 → 判定）
- `sweep_joint.sh` / `sweep_pose.sh`：初期姿勢のずれを変えた評価

## 再現手順

### 1. 環境（講義第4・5回と同じ）

- Dockerイメージ：`airobotbook/ros2-desktop-ai-robot-book-humble`
- `~/pai_ws/src` に [matsuolab/physicalai_teleop](https://github.com/matsuolab/physicalai_teleop)（コミット `0ef2a00`）を置き、`colcon build`
- 本リポジトリを取得して依存関係を入れる

```bash
cd ~ && git clone --recursive https://github.com/yamady0711/pai-final-sequential-reaching.git pai_training
cd ~/pai_training && pixi install
ln -s ~/pai_training/pointing_task ~/pointing_task
```

LeRobotはsubmodule（`768e366`、v0.3.2~144）として固定されている。

### 2. 学習済みモデルで動作を確認する（学習を省略する場合）

Releasesから `model_crane_plus_pointing_v2_act_n8.tar.gz` を取得し、`~/checkpoints/train/` に展開する。

```bash
mkdir -p ~/checkpoints/train && tar xzf model_crane_plus_pointing_v2_act_n8.tar.gz -C ~/checkpoints/train

# ターミナル1
ros2 launch crane_plus_gazebo crane_plus_with_table.launch.py
# ターミナル2（テレオペは起動しない）
cd ~/pointing_task/scripts && python3 spawn_markers.py
export OBS_RANGE=~/pointing_task/config/obs_range_v2.json
N=20 AMP=0.0  ./run_eval.sh ~/checkpoints/train/crane_plus_pointing_v2_act_n8   # 条件A'
N=20 AMP=0.05 ./run_eval.sh ~/checkpoints/train/crane_plus_pointing_v2_act_n8   # 条件B'
./sweep_pose.sh                                                                 # P1〜P8
```

### 3. データから学習し直す場合

Releasesの `rosbags_pointing.tar.gz` を `~/dataset/rosbags/` に展開する（自分でお手本を集める場合は `pointing_task/scripts/record_demo.sh` を使う）。

```bash
mkdir -p ~/dataset/rosbags && tar xzf rosbags_pointing.tar.gz -C ~/dataset/rosbags
cd ~/pai_training
pixi run convert
WANDB_MODE=offline pixi run train        # CPUで約2時間（2000ステップ）
cd ~/checkpoints/train
cp -r crane_plus_pointing_v2_act crane_plus_pointing_v2_act_n8
sed -i 's/"n_action_steps": 1,/"n_action_steps": 8,/' crane_plus_pointing_v2_act_n8/config.json
```

変換済みデータセット（`dataset_crane_plus_pointing_v2.tar.gz`）もReleasesに置いている。

注意：TFの`world`はロボットの土台に一致し、Gazeboの原点より1.015 m上にある。`pointing_task/config/points.yaml`の`gazebo_offset`で補正している。

## クレジット

- ACT：T. Z. Zhao et al., *Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware*, arXiv:2304.13705, 2023
- [huggingface/lerobot](https://github.com/huggingface/lerobot)
- [matsuolab/pai_training](https://github.com/matsuolab/pai_training)（本リポジトリのフォーク元）
- [matsuolab/physicalai_teleop](https://github.com/matsuolab/physicalai_teleop)
- [AI-Robot-Book-Humble/docker-ros2-desktop-ai-robot-book-humble](https://github.com/AI-Robot-Book-Humble/docker-ros2-desktop-ai-robot-book-humble)
