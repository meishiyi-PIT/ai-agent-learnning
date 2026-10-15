"""
模块五 · 《注意力机制》5.4：生产环境用官方实现
================================================
手写版（multi_head.py）的价值是吃透原理；真上项目用官方的，底层做了算子融合和内存优化。

【方案一 nn.MultiheadAttention】
    和手写 MultHeadedAttention 是同一个东西：内部也是三张表 + 切头 + attention + 拼接 + 融合表。
    差别：官方把三张表合成一张 (3*d_model, d_model) 的大表一次乘完（更快），且返回关注度表。

【方案二 F.scaled_dot_product_attention（PyTorch 2.0+）】
    只做 attention() 那四行（打分/缩放/softmax/加权和），**不含三张表和切头**，
    你要自己先乘表、自己 view/transpose 成 [B, H, L, d] 再喂它。
    好处：底层按硬件自动选 FlashAttention 等最优内核，长序列省显存。

【课件勘误——两条都是实测的（torch 2.3.0）】
  1. 课件说"PyTorch 2.x 里 batch_first=True 是默认行为"——**错**。默认仍是 batch_first=False，
     即输入要是 [seq, batch, d_model]。想传 [batch, seq, d_model] 必须显式写 batch_first=True，
     漏写不会报错，只会把"句子"和"词"两个维度理解反，结果全错还不告诉你。
  2. 课件说 attn_weights 形状 [4, 30, 30] 是"把 batch 和 head 拍到了一个维度里"——**错**。
     默认 average_attn_weights=True，返回的是 8 个头的关注度表**取平均**后的 [batch, seq, seq]；
     传 average_attn_weights=False 才得到每头各一张的 [batch, heads, seq, seq]。

运行：
    cd C:\\workspace\\deepLearning
    PYTHONUTF8=1 uv run python attention/official.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

q = k = v = torch.randn(4, 30, 256)          # batch=4，每句 30 词，d_model=256

# 方案一：必须显式 batch_first=True
mha = nn.MultiheadAttention(embed_dim=256, num_heads=8, batch_first=True)
out, attn_weights = mha(q, k, v)
print("nn.MultiheadAttention 输出:", tuple(out.shape))                  # (4, 30, 256)
print("attn_weights（8 头取平均）:", tuple(attn_weights.shape))          # (4, 30, 30)
_, per_head = mha(q, k, v, average_attn_weights=False)
print("attn_weights（每头一张）  :", tuple(per_head.shape))              # (4, 8, 30, 30)

# 方案二：只做四行核心计算，多头要自己切
out2 = F.scaled_dot_product_attention(q, k, v)
print("scaled_dot_product_attention（未切头，当单头用）:", tuple(out2.shape))   # (4, 30, 256)

qh = q.view(4, 30, 8, 32).transpose(1, 2)    # 自己切成 8 头 × 32 维 → [4, 8, 30, 32]
out3 = F.scaled_dot_product_attention(qh, qh, qh)
print("scaled_dot_product_attention（切 8 头后）    :", tuple(out3.shape))     # (4, 8, 30, 32)
