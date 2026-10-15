"""
课件 5《大模型推理部署》PD 分离第 4 节：KV Offloading —— 显存不够，内存/磁盘来凑

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可，约半分钟）：
    .venv/Scripts/python -X utf8 inference_deploy/s18_kv_offload.py

问题：一个请求被抢占（显存不够，调度器把它踢出运行集合），它的 KV Cache 怎么办？
- 方案 A 扔掉：恢复时把整段上下文重新 Prefill 一遍（重算）；
- 方案 B 换出：把 KV 存到下一级存储，恢复时读回来（Offloading）。
本机实测：Qwen3-0.6B 读一段约 1000 token 的上下文，比较"重算"和"存盘再读回"各要多久，
并检查读回来的缓存接着生成，挑出的下一个 token 和原来一模一样（换出不改结果）。
最后按 4090 + Qwen2.5-7B 粗估 GPU 上的同一笔账（纯算术，不跑）。

勘误：课件说"HBM 微秒级、CPU 内存百微秒级、NVMe 百微秒到毫秒级"是单次访问延迟的量级；
搬一整块 KV 时真正决定耗时的是带宽：HBM 约 1 TB/s、PCIe 4.0 x16 实际约 25 GB/s、NVMe 约 7 GB/s。

Python 语法点：
- `cache.to_legacy_cache()` / `DynamicCache.from_legacy_cache(...)`：缓存对象和"每层一个 (K, V) 元组"互转，
  元组好存盘（transformers 4.51 的写法）。
- `torch.save(obj, path)` / `torch.load(path)`：把张量存成文件、再读回来。
- `os.path.getsize(path)`：文件字节数。
"""
import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, DynamicCache

MODEL_DIR = "models/Qwen3-0.6B"
PATH = "inference_deploy/_kv_swap.pt"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()

context = "长城是中国古代的军事防御工程，东起山海关，西至嘉峪关，绵延上万里。" * 40
ids = tokenizer(context, return_tensors="pt")["input_ids"]
nxt = tokenizer("它", return_tensors="pt")["input_ids"]          # 恢复后要接着处理的下一个 token

with torch.no_grad():
    model(input_ids=ids[:, :16])                                 # 预热一次，别把首次启动开销算进重算时间
    t = time.perf_counter()
    out = model(input_ids=ids, use_cache=True)                   # 方案 A 的代价：整段重新 Prefill
    recompute = time.perf_counter() - t
    cache = out.past_key_values

    t = time.perf_counter()
    torch.save(cache.to_legacy_cache(), PATH)                    # 换出：存盘
    swap_out = time.perf_counter() - t
    t = time.perf_counter()
    restored = DynamicCache.from_legacy_cache(torch.load(PATH))  # 换入：读回
    swap_in = time.perf_counter() - t

    a = model(input_ids=nxt, past_key_values=cache, use_cache=True).logits[0, -1].argmax().item()
    b = model(input_ids=nxt, past_key_values=restored, use_cache=True).logits[0, -1].argmax().item()

size = os.path.getsize(PATH)
os.remove(PATH)
print(f"上下文 {ids.shape[1]} 个 token，KV Cache {size / 1e6:.0f} MB")
print(f"方案 A 重算 Prefill：{recompute:.2f} 秒")
print(f"方案 B 存盘 {swap_out:.2f} 秒，读回 {swap_in:.2f} 秒；读回后下一个 token 和原来一样：{a == b}")

# GPU 粗估：Qwen2.5-7B（28 层、4 个 KV 头、头维度 128、BF16），4K token，4090（BF16 约 165 TFLOPS，按 40% 利用率）
kv = 2 * 28 * 4 * 128 * 2 * 4096
pre = 2 * 7.6e9 * 4096 / (165e12 * 0.4)
print(f"4090 + 7B + 4K token：KV {kv / 1e6:.0f} MB，重算 {pre:.2f} 秒，"
      f"从 CPU 内存换回 {kv / 25e9:.3f} 秒，从 NVMe 换回 {kv / 7e9:.3f} 秒")
