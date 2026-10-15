"""
课件 5《大模型推理部署》第 3 节 3.4：调度器两个参数的吞吐 / 延迟权衡

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可，约 1 分钟）：
    .venv/Scripts/python -X utf8 inference_deploy/s12_batch_tradeoff.py

第一段对应 max_num_seqs（一步最多跑几个请求）：
    同一个 prompt 复制成 1 / 4 / 16 份一起 Decode 32 步，
    看"一步多久"（= 每个用户感受到的 token 间隔 ITL）和"每秒一共产出几个 token"（= 吞吐）。
第二段对应 max_num_batched_tokens（一步最多处理几个 token）：
    一步里如果混进一大段新请求的 prompt（Prefill），这一步要多久——
    同一步里正在 Decode 的请求都得等它，它们的 token 间隔就被拉长。

CPU 上的数字只看趋势，GPU 上绝对值差很多，但方向一样。

Python 语法点：
- `[text] * bs`：把列表重复 bs 次，得到 bs 个一样的 prompt。
- `torch.randint(0, V, (1, n))`：随机造 n 个 token 编号，只为测一步前向要多久，不关心内容。
"""
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"
STEPS = 32
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()

text = tokenizer.apply_chat_template(
    [{"role": "user", "content": "介绍一下长城的历史。"}], tokenize=False,
    add_generation_prompt=True, enable_thinking=False,
)
model.generate(**tokenizer([text], return_tensors="pt"), max_new_tokens=4)  # 预热

# ---- 第一段：批里的请求数 ----
for bs in (1, 4, 16):
    inputs = tokenizer([text] * bs, return_tensors="pt")
    t0 = time.perf_counter()
    model.generate(**inputs, max_new_tokens=STEPS, min_new_tokens=STEPS, do_sample=False,
                   pad_token_id=tokenizer.eos_token_id)
    sec = time.perf_counter() - t0
    print(f"{bs:2d} 个请求一起跑：一步 {sec / STEPS * 1000:4.0f} 毫秒（每个用户的 token 间隔），"
          f"一共每秒产出 {bs * STEPS / sec:5.1f} 个 token")

# ---- 第二段：一步里处理的 token 数 ----
with torch.no_grad():
    for n in (1, 512):
        ids = torch.randint(0, model.config.vocab_size, (1, n))
        t0 = time.perf_counter()
        model(input_ids=ids)
        print(f"一步里处理 {n:4d} 个 token：{(time.perf_counter() - t0) * 1000:5.0f} 毫秒")
