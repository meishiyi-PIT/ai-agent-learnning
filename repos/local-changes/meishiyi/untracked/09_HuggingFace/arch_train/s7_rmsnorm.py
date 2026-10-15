"""课件 7《RMSNorm》：LayerNorm vs RMSNorm 手算对照 + Qwen3 里 RMSNorm 用在哪。

1. 同一个 4 维小向量 [2, 4, 4, 6]，分别过 LayerNorm 和 RMSNorm（γ=1、β=0，只看归一化本身）
2. 用 transformers 里 Qwen3 的官方实现 Qwen3RMSNorm 再算一遍，确认和手写公式一致
3. 按 config 在 meta 设备上搭一个空壳 Qwen3-0.6B（不加载权重，秒出），数它有多少个 RMSNorm、各在哪

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s7_rmsnorm.py
"""
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoConfig, AutoModelForCausalLM
from transformers.models.qwen3.modeling_qwen3 import Qwen3RMSNorm

x = torch.tensor([2.0, 4.0, 4.0, 6.0])

ln = (x - x.mean()) / torch.sqrt(x.var(unbiased=False) + 1e-6)     # 减均值、除标准差
rms = x / torch.sqrt(x.pow(2).mean() + 1e-6)                         # 只除均方根
print("LayerNorm :", [round(v, 2) for v in ln.tolist()], "均值", round(ln.mean().item(), 2))
print("RMSNorm   :", [round(v, 2) for v in rms.tolist()], "均方根", round(rms.pow(2).mean().sqrt().item(), 2))
print("Qwen3 官方:", [round(v, 2) for v in Qwen3RMSNorm(4, eps=1e-6)(x).tolist()])

cfg = AutoConfig.from_pretrained(Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B")
with torch.device("meta"):
    model = AutoModelForCausalLM.from_config(cfg)
names = [n for n, m in model.named_modules() if isinstance(m, Qwen3RMSNorm)]
where = Counter(n.split(".")[-1] for n in names)
print(f"Qwen3-0.6B：{cfg.num_hidden_layers} 层，共 {len(names)} 个 RMSNorm，eps={cfg.rms_norm_eps}，按位置：{dict(where)}")
