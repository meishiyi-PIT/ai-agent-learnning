"""
课件 5《大模型推理部署》第四部分第 4 节补充：一个真实部署的 KV Cache 账 + 缓存怎么拖低算术强度 I

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s5_kvcache_example.py

场景：AutoDL 上一张 RTX 4090（24 GB），用 vLLM 部署 DeepSeek-R1-Distill-Qwen-7B（Qwen2.5-7B 结构：
28 层、28 个 Q 头、4 个 KV 头、头维度 128、76.2 亿参数）。

第一段：显存怎么分，缓存池能装多少 token，同时能服务几个请求。
    vLLM 默认 gpu_memory_utilization=0.9 → 可用 21.6 GB；减去权重和运行时预留，剩下的全给 KV Cache。
    （vLLM 启动日志里的 "GPU KV cache size: N tokens" 和 "Maximum concurrency ..." 就是这笔账。）
    运行时预留 1.4 GB 是估计值（激活、CUDA 图等），实际以启动日志为准。

第二段：一步 Decode 的算术强度 I = 计算量 ÷ 搬运量。
    计算量 = 批里每个请求 × (2 × 参数量 + 注意力部分 2×2×层数×Q头数×头维度×上下文长度)
    搬运量 = 权重（全批共用，只搬一次）+ 每个请求自己的 KV Cache（不能共用，批越大搬得越多）
    两个效应：
    - 显存装不下 → 批凑不大 → 分子上不去（同样的缓存总量，请求少、每个请求长，I 更低）；
    - 上下文越长 → 每步要读的 KV Cache 越多 → 分母变大，I 下降。
"""

GB = 1e9

# ---- 模型：DeepSeek-R1-Distill-Qwen-7B（Qwen2.5-7B 结构）----
PARAMS = 7.62e9
LAYERS, Q_HEADS, KV_HEADS, HEAD_DIM = 28, 28, 4, 128
BYTES = 2  # BF16
kv_per_token = 2 * LAYERS * KV_HEADS * HEAD_DIM * BYTES   # 57,344 字节

# ---- 第一段：显存账 ----
usable = 24 * 0.9 * GB
weights = PARAMS * BYTES
runtime = 1.4 * GB
pool = usable - weights - runtime
pool_tokens = pool / kv_per_token
print(f"可用 {usable / GB:.1f} GB = 权重 {weights / GB:.1f} + 预留 {runtime / GB:.1f} + 缓存池 {pool / GB:.1f} GB")
print(f"每 token 缓存 {kv_per_token / 1e3:.0f} KB → 缓存池装 {pool_tokens / 1e3:.0f}K 个 token")
for ctx in (2048, 4096, 8192, 32768):
    print(f"  每个请求 {ctx // 1024:2d}K token → 最多同时服务 {pool_tokens / ctx:5.1f} 个请求")

# ---- 第二段：一步 Decode 的 I ----
def decode_intensity(batch, ctx):
    flops = batch * (2 * PARAMS + 2 * 2 * LAYERS * Q_HEADS * HEAD_DIM * ctx)
    kv = batch * ctx * kv_per_token
    return flops / (weights + kv), kv


print("\n一步 Decode 的 I（每搬 1 字节配几次运算）：")
for batch, ctx in [(1, 4096), (20, 512), (20, 4096), (5, 16384)]:
    I, kv = decode_intensity(batch, ctx)
    print(f"  {batch:2d} 个请求 × 每个 {ctx:5d} token：要搬权重 {weights / GB:.1f} GB + 缓存 {kv / GB:.1f} GB → I = {I:4.1f}")
