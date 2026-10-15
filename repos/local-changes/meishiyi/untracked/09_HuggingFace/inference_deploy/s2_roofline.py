"""
课件 5《大模型推理部署》第三部分：Roofline 性能模型——为什么 Prefill 吃算力、Decode 吃带宽

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s2_roofline.py

只有一个概念：算术强度 I = 计算量(FLOPs) ÷ 搬运量(Bytes)，
含义是"每从显存搬 1 字节回来，能配套做几次浮点运算"。
把 I 和硬件的平衡点（峰值算力 ÷ 峰值带宽）比：I 低于平衡点 = 卡带宽，高于 = 卡算力。

场景：一批 token 过一层线性层 Y = X · W
    X: [n_tokens, d_model]   W: [d_model, d_model]
- 计算量：每个输出元素要做 d_model 次乘加 = 2·d_model 次浮点运算，
  输出共 n_tokens × d_model 个元素 → FLOPs = 2 · n · d · d
- 搬运量：读 X（n·d 个数）+ 读 W（d·d 个数，**无论 n 多大都要整块搬**）+ 写 Y（n·d 个数），
  每个数 2 字节（BF16）

课件勘误（教到这里时说）：课件贴的"跑出来的结果"（n=1 时 I=2.00、n=128 时 I=255 算力受限……）
和它自己的代码对不上；下面是这段代码的真实输出，n=128 实际仍在带宽受限一侧。
"""

d_model = 7168          # DeepSeek-V3 的隐藏维度
bytes_per_elem = 2      # BF16，每个元素 2 字节

# A100 80GB：BF16 峰值算力 312 TFLOPS，HBM 带宽约 2 TB/s → 平衡点 = 312 / 2 = 156 FLOP/byte
RIDGE = 312 / 2


def arithmetic_intensity(n_tokens: int) -> float:
    """线性层的算术强度（FLOP/byte）"""
    flops = 2 * n_tokens * d_model * d_model
    bytes_moved = (2 * n_tokens * d_model + d_model * d_model) * bytes_per_elem
    return flops / bytes_moved


print(f"A100 平衡点 = 312 TFLOPS / 2 TB/s = {RIDGE:.0f} FLOP/byte\n")
for n, stage in [(1, "Decode(1 token/step)"),
                 (128, "Decode batch=128"),
                 (256, "Decode batch=256"),
                 (2048, "Prefill 2K prompt"),
                 (8192, "Prefill 8K prompt")]:
    I = arithmetic_intensity(n)
    verdict = "memory-bound" if I < RIDGE else "compute-bound"
    print(f"{stage:22s} n={n:5d}  I={I:8.2f} FLOP/byte  -> {verdict}")

# 直觉：n 很小时，搬运量被 W 那块 d·d 主导，I ≈ n（每多 1 个 token，同一块权重多算一行）；
# 所以 Decode 单 token 的 I ≈ 1，离 156 差两个数量级；把 batch 开到 ~160 才追平 A100 的平衡点。
# 这就是"连续批处理"能把 Decode 从带宽墙里救出来的数学依据。
