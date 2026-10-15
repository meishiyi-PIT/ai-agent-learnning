"""
课件 5《大模型推理部署》PD 分离第 2 节：KV Cache 要"搬家"——传一次要多久

运行（纯 Python，不需要 torch）：
    .venv/Scripts/python -X utf8 inference_deploy/s16_kv_transfer.py

场景：LLaMA-3-70B（80 层、64 个 Q 头、8 个 KV 头、头维度 128、BF16），用户丢进来 32K token 的文档。
Prefill 池 8 张 H100 算完，要把这 32K token 的 KV Cache 传给 Decode 池。
- 缓存大小：沿用 KV Cache 那章的公式 2 × 层数 × KV头数 × 头维度 × token 数 × 2 字节；
- Prefill 耗时：粗估，计算量 ÷（8 卡 × 每卡 989 TFLOPS × 40% 实际利用率）；
- 三种链路的传输耗时（都按单条链路的理论带宽，实际更慢）：
    普通 TCP 25 Gb 以太网 ≈ 3.1 GB/s；RDMA 400 Gb InfiniBand ≈ 50 GB/s；NVLink（同机卡间）≈ 450 GB/s 单向。
- 逐层流水：算完第 1 层就开始传第 1 层的 K、V，同时算第 2 层……
  只要每层"传"比"算"快，传输就几乎全藏在 Prefill 时间里，Decode 池只多等最后一层。

Python 语法点：
- `f"{x:6.2f}"`：宽 6、保留两位小数的格式化。
- 元组列表 `[("名字", 数值), ...]` 配 for 解包：一次取出名字和带宽。
"""
LAYERS, Q_HEADS, KV_HEADS, HEAD_DIM, PARAMS = 80, 64, 8, 128, 70e9
N = 32768

kv_bytes = 2 * LAYERS * KV_HEADS * HEAD_DIM * N * 2
flops = 2 * PARAMS * N + 2 * 2 * LAYERS * Q_HEADS * HEAD_DIM * N * N / 2   # 注意力按因果掩码只算一半
prefill_s = flops / (8 * 989e12 * 0.4)
print(f"32K token 的 KV Cache：{kv_bytes / 1e9:.1f} GB；8 张 H100 做 Prefill 约 {prefill_s:.1f} 秒")

for name, gbps in [("TCP 25Gb 以太网", 3.1), ("RDMA 400Gb IB", 50), ("NVLink 同机", 450)]:
    whole = kv_bytes / (gbps * 1e9)
    per_layer_send, per_layer_compute = whole / LAYERS, prefill_s / LAYERS
    pipelined = per_layer_send if per_layer_send <= per_layer_compute else whole - prefill_s + per_layer_compute
    print(f"{name:14s}：整包传完 {whole:5.2f} 秒；边算边传，Prefill 结束后还要多等 {pipelined:5.2f} 秒")
