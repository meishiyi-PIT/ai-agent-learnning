"""课件 7《从 MHA 到 MQA 与 GQA》：Qwen3-0.6B 的 GQA 在缓存里长什么样。

1. 真跑一次前向，打开 KV Cache，看缓存里 K 的形状：存的是 8 个 KV 头，不是 16 个 Q 头
2. 16 个 Q 头各自去找哪个 KV 头（repeat_kv 的分组规则）
3. 按课件公式算 4096 token 的 KV Cache：MHA / GQA / MQA 各多大

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s12_gqa_cache.py
"""
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B"
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()
c = model.config

ids = tok("人工智能正在改变世界", return_tensors="pt").input_ids
with torch.no_grad():
    cache = model(ids, use_cache=True).past_key_values
k = cache.key_cache[0] if hasattr(cache, "key_cache") else cache.layers[0].keys
print(f"Q 头 {c.num_attention_heads} 个，KV 头 {c.num_key_value_heads} 个；第 0 层缓存 K 的形状 {tuple(k.shape)} = [批, KV头, token数, head_dim]")

group = c.num_attention_heads // c.num_key_value_heads
print("Q 头 → 用哪个 KV 头：", {q: q // group for q in range(c.num_attention_heads)})

seq, bytes_ = 4096, 2   # 4096 个 token，BF16 每个数 2 字节
for name, kv in [("MHA", c.num_attention_heads), ("GQA", c.num_key_value_heads), ("MQA", 1)]:
    mb = c.num_hidden_layers * kv * c.head_dim * 2 * bytes_ * seq / 2**20
    print(f"{name}：KV 头 {kv:2d} 个 → 4096 token 的 KV Cache {mb:6.0f} MB")
