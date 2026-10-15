"""
课件 5《大模型推理部署》第四部分第 1 节：为什么需要 KV Cache

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可）：
    .venv/Scripts/python -X utf8 inference_deploy/s3_kvcache_speed.py

实验：同一个问题、同样贪心解码、同样写 200 个 token，只切换 use_cache：
- use_cache=True：每步只把新 token 过一遍模型，历史 token 的 K、V 从缓存里取；
- use_cache=False：每步把"输入 + 已生成的全部 token"整段重新过一遍模型，重算所有历史 K、V。
两次输出应该一字不差（缓存只省重复计算，不改结果），差别只在耗时。

课件勘误（教到这里时说）：课件说 KV Cache "加速的是 Q·Kᵀ 与加权求和 V 这两次矩阵相乘"不准。
开了缓存，每步照样要用新 token 的 Q 去乘全部历史 K、再加权全部历史 V；
真正省掉的是历史 token 每步重新过整个模型（每层的 K/V 投影、MLP 等全部运算）。

Python 语法点：
- `time.perf_counter()`：高精度计时，两次相减得秒数。
- `min_new_tokens=N` 配 `max_new_tokens=N`：强制正好写 N 个 token，两种模式工作量一样才好比。
"""
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"
N_NEW = 200

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()

messages = [{"role": "user", "content": "介绍一下长城的历史。"}]
text = tokenizer.apply_chat_template(
    messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
)
inputs = tokenizer(text, return_tensors="pt")
prompt_len = inputs["input_ids"].shape[1]


def run(use_cache: bool):
    t0 = time.perf_counter()
    with torch.no_grad():
        ids = model.generate(
            **inputs, max_new_tokens=N_NEW, min_new_tokens=N_NEW, do_sample=False,
            use_cache=use_cache, pad_token_id=tokenizer.eos_token_id,
        )
    sec = time.perf_counter() - t0
    return ids[0][prompt_len:], sec


run(True)  # 预热一次，排除第一次调用的初始化开销

new_on, sec_on = run(True)
new_off, sec_off = run(False)

print(f"输入 {prompt_len} 个 token，每种模式都写 {N_NEW} 个 token")
print(f"开缓存: {sec_on:6.1f} 秒  每个 token {sec_on / N_NEW * 1000:6.0f} 毫秒")
print(f"关缓存: {sec_off:6.1f} 秒  每个 token {sec_off / N_NEW * 1000:6.0f} 毫秒")
print(f"关缓存慢 {sec_off / sec_on:.1f} 倍；两次输出完全一样: {torch.equal(new_on, new_off)}")
