#!/usr/bin/env bash
# 租卡那天在 dist/ 目录里按顺序执行；每组跑完看 results.csv 多出的行，并对照另一个终端里的 nvidia-smi -l 2
# 装环境：pip install "transformers==4.51.3" peft datasets accelerate deepspeed ninja modelscope
# 下模型：modelscope download --model Qwen/Qwen2.5-0.5B-Instruct --local_dir /root/autodl-tmp/code/model_qwen05b
set -e
cd "$(dirname "$0")"
export MODEL_DIR="${MODEL_DIR:-/root/autodl-tmp/code/model_qwen05b}"   # 没设就用 AutoDL 的默认位置
[ -d "$MODEL_DIR" ] || { echo "模型目录不存在: $MODEL_DIR，先执行上面的 modelscope download"; exit 1; }

echo "== ① 单卡全参基线 =="
CUDA_VISIBLE_DEVICES=0 python train_dist.py --run single

echo "== ② 两卡 DDP =="
torchrun --nproc_per_node=2 train_dist.py --run ddp

echo "== ③ 两卡 ZeRO-2 =="
torchrun --nproc_per_node=2 train_dist.py --run zero2

echo "== ④ 两卡 ZeRO-3 + CPU Offload =="
torchrun --nproc_per_node=2 train_dist.py --run zero3_offload

# 可选
# echo "== ⑤ 两卡 ZeRO-3（不 offload）=="
# torchrun --nproc_per_node=2 train_dist.py --run zero3
# echo "== ⑥ LoRA 下的 ZeRO-2：优化器状态本来就小，看它几乎不省 =="
# torchrun --nproc_per_node=2 train_dist.py --run zero2 --lora
# echo "== ⑦ 课件场景复现：7B LoRA + ZeRO-3 =="
# torchrun --nproc_per_node=2 train_dist.py --run zero3 --lora --dtype bf16 --model Qwen/Qwen2.5-7B-Instruct --steps 30

echo "== 汇总 =="
cat results.csv
