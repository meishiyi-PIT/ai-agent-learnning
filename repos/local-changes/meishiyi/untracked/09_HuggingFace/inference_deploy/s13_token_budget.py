"""
课件 5《大模型推理部署》第 3 节 3.4 补充：max_num_batched_tokens 怎么调

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可，约半分钟）：
    .venv/Scripts/python -X utf8 inference_deploy/s13_token_budget.py

vLLM 官方文档（docs/configuration/optimization.md，"Performance Tuning with Chunked Prefill"）：
- 每一步先把所有 Decode 请求排进来（各占 1 个 token），预算还有剩才排 Prefill；
  新请求的 prompt 放不下剩余预算，就自动切块，分几步做完（Chunked Prefill）。
- 小值（如 2048）→ ITL 更好，混进来拖慢 Decode 的 Prefill 少；
  大值 → TTFT 更好，一步能多处理 Prefill；追求吞吐建议 > 8192，尤其是大显卡跑小模型。

场景：8 个请求正在 Decode，这时来了一个 2000 token 的新请求。
预算 B 时：每步 = 8 个 Decode token + (B - 8) 个 Prefill token。
- 正在 Decode 的 8 个用户：token 间隔 = 这一步的耗时；
- 新请求：TTFT ≈ 要切成几步 × 每步耗时。
每步耗时直接在本机实测"一步处理 B 个 token 要多久"。

Python 语法点：
- `math.ceil(a / b)`：向上取整，2000 个 token 每步做 248 个，要 9 步。
"""
import math
import time

import torch
from transformers import AutoModelForCausalLM

MODEL_DIR = "models/Qwen3-0.6B"
PROMPT, DECODING = 2000, 8
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()


def step_ms(n):
    ids = torch.randint(0, model.config.vocab_size, (1, n))
    with torch.no_grad():
        t0 = time.perf_counter()
        model(input_ids=ids)
    return (time.perf_counter() - t0) * 1000


step_ms(8)  # 预热
for budget in (256, 1024, 2048):
    ms = step_ms(budget)
    steps = math.ceil(PROMPT / (budget - DECODING))
    print(f"预算 {budget:4d}：一步 {ms:5.0f} 毫秒 → 8 个老用户的 token 间隔 {ms:5.0f} 毫秒；"
          f"新请求切 {steps} 步，TTFT ≈ {steps * ms / 1000:4.1f} 秒")
