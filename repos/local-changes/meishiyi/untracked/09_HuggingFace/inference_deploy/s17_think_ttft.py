"""
课件 5《大模型推理部署》PD 分离第 3 节认知点 1：首 token 不一定是可见字符

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可，约半分钟到一分钟）：
    .venv/Scripts/python -X utf8 inference_deploy/s17_think_ttft.py

打开 Qwen3 的思考模式（enable_thinking=True），手写 Decode 循环（同 s14），记三个时间：
- 引擎的 TTFT：Prefill 完、挑出第 1 个 token 的时间——这个 token 是 <think>，用户看不见；
- 思考阶段：<think> … </think> 之间的 token，前端通常折叠成"思考中…"；
- 用户真正看到第一个答案字的时间。
监控里的 TTFT 和用户体感的"首字时间"差的就是整段思考，而思考全在 Decode 池里跑。

Python 语法点：
- `tokenizer.convert_tokens_to_ids("</think>")`：按 token 文字查编号（Qwen3 里是 151668）。
- `generated.index(END)`：列表里第一次出现某个值的位置。
"""
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"
MAX_NEW = 400
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()
END = tokenizer.convert_tokens_to_ids("</think>")

text = tokenizer.apply_chat_template(
    [{"role": "user", "content": "3 个苹果吃掉 1 个还剩几个？一句话回答。"}], tokenize=False,
    add_generation_prompt=True, enable_thinking=True,
)
ids = tokenizer(text, return_tensors="pt")["input_ids"]

generated, t_first, t_answer = [], None, None
t0 = time.perf_counter()
with torch.no_grad():
    out = model(input_ids=ids, use_cache=True)
    for _ in range(MAX_NEW):
        nid = out.logits[0, -1].argmax().item()
        now = time.perf_counter() - t0
        if t_first is None:
            t_first = now
        if nid == tokenizer.eos_token_id:
            break
        generated.append(nid)
        if t_answer is None and END in generated[:-1] and tokenizer.decode(nid).strip():
            t_answer = now                      # </think> 之后第一个非空白 token
        out = model(input_ids=torch.tensor([[nid]]), past_key_values=out.past_key_values, use_cache=True)

k = generated.index(END)
print(f"引擎 TTFT：{t_first:.2f} 秒，第 1 个 token 是 {tokenizer.decode(generated[0])!r}（用户看不见）")
print(f"思考了 {k - 1} 个 token：{tokenizer.decode(generated[1:k]).strip()[:40]}…")
print(f"用户看到第一个答案字：{t_answer:.2f} 秒；答案：{tokenizer.decode(generated[k + 1:]).strip()}")
