"""环境自检：这个脚本全部打印出来且没有报错，就说明四条链路都通了——
  1) 依赖装对了版本（对照课件 1.4）
  2) 镜像生效（HF_ENDPOINT）
  3) 两个模型已经在本地缓存，from_pretrained 不会再去联网
  4) evaluate 能从本地 evaluate-main 目录加载指标

跑法：PYTHONUTF8=1 uv run python 00_check_env.py
"""

import os

import accelerate
import datasets
import evaluate
import gradio
import peft
import torch
import transformers
from transformers import AutoConfig, AutoTokenizer

print("== 1) 版本 ==")
print("torch        ", torch.__version__)
print("transformers ", transformers.__version__)
print("datasets     ", datasets.__version__)
print("evaluate     ", evaluate.__version__)
print("peft         ", peft.__version__)
print("accelerate   ", accelerate.__version__)
print("gradio       ", gradio.__version__)

print("\n== 2) 镜像与设备 ==")
print("HF_ENDPOINT  ", os.environ.get("HF_ENDPOINT"))
# 本机是 Intel 集显，这里预期打印 False；课件 2.4 的 device 逻辑在这台机器上永远落到 CPU
print("cuda available", torch.cuda.is_available())

print("\n== 3) 模型缓存 ==")
tokenizer = AutoTokenizer.from_pretrained("hfl/chinese-macbert-base")
print("macbert vocab_size", tokenizer.vocab_size)
config = AutoConfig.from_pretrained("uer/roberta-base-finetuned-dianping-chinese")
# id2label 就是课件 2.5 第三站"把下标翻译回标签名"用的那张表
print("dianping id2label", config.id2label)
# 练习脚本实际用的是本地 safetensors 目录（原因见 README），确认它们在
for local_dir in ["models/chinese-macbert-base", "models/roberta-base-finetuned-dianping-chinese"]:
    ok = os.path.exists(os.path.join(local_dir, "model.safetensors"))
    print(f"{local_dir:50s}", "ok" if ok else "MISSING")

print("\n== 4) evaluate 本地指标 ==")
acc = evaluate.load("./evaluate-main/metrics/accuracy/accuracy.py")
print(acc.compute(references=[0, 1], predictions=[0, 1]))

print("\nALL OK")
