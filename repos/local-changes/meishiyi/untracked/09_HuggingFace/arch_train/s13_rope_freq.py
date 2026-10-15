"""课件 7《RoPE 旋转位置编码》：真实 Qwen3 里的 RoPE 长什么样。

1. head_dim=128 拆成 64 对，每对转速不同：看几对"每往后一格转多少、多少格转满一圈"
2. 用 Qwen3 源码里真正的 apply_rotary_pos_emb 验证：相隔格数一样 → 打分一样，和绝对位置无关
3. 同一对 q/k 只改相隔距离，打分怎么变（内容不变，距离变 → 分数变）

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s13_rope_freq.py
"""
import math
from pathlib import Path

import torch
from transformers import AutoConfig
from transformers.models.qwen3.modeling_qwen3 import Qwen3RotaryEmbedding, apply_rotary_pos_emb

MODEL = Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B"
c = AutoConfig.from_pretrained(MODEL)
rope = Qwen3RotaryEmbedding(config=c)

inv = rope.inv_freq                      # 64 个转速 θ_i = rope_theta^(-2i/128)
print(f"rope_theta = {c.rope_theta:.0f}，head_dim = {c.head_dim} → {len(inv)} 对，每对一个转速")
for i in [0, 8, 16, 32, 48, 63]:
    print(f"  第 {i:2d} 对：每往后 1 格转 {inv[i].item():.6f} 弧度，转满一圈要 {2 * math.pi / inv[i].item():>12,.0f} 格")


def score(q, k, q_pos, k_pos):
    pos = torch.tensor([[q_pos, k_pos]])
    x = torch.zeros(1, 2, c.head_dim)
    cos, sin = rope(x, pos)                                   # 两个位置各自的 cos/sin，形状 [1, 2, 128]
    both = torch.stack([q, k]).view(1, 1, 2, c.head_dim)       # [批, 头, token, head_dim]
    rq, rk = apply_rotary_pos_emb(both, both, cos, sin)        # 源码里 Q、K 就是这样被转的
    return (rq[0, 0, 0] @ rk[0, 0, 1]).item()                  # 位置 q_pos 的 Q · 位置 k_pos 的 K


torch.manual_seed(0)
q, k = torch.randn(c.head_dim), torch.randn(c.head_dim)
print(f"\n同一对 q/k，不转时的打分 = {(q @ k).item():.3f}")
for q_pos, k_pos in [(5, 3), (1005, 1003), (30005, 30003), (5, 4), (5, 0)]:
    print(f"  Q 在位置 {q_pos:5d}，K 在位置 {k_pos:5d}，相隔 {q_pos - k_pos} 格 → 打分 {score(q, k, q_pos, k_pos):.3f}")

print("\n只改相隔距离（Q 固定在位置 4000）：")
for d in [0, 1, 2, 10, 100, 1000]:
    print(f"  相隔 {d:4d} 格 → 打分 {score(q, k, 4000, 4000 - d):7.3f}")
