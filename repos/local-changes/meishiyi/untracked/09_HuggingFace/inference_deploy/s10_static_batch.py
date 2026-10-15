"""
课件 5《大模型推理部署》第 3 节 3.2.3：用 Transformers 感受静态批处理

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可，约 1 分钟）：
    .venv/Scripts/python -X utf8 inference_deploy/s10_static_batch.py

课件原代码 + 两处补充：
- 算"白算"比例：这一批一共跑了 S 步，每步 3 条请求都要过模型 → 3 × S 个位置；
  其中真正生成内容的只有各请求的有效 token，其余是短请求结束后填的 pad，每步照样算、结果扔掉。
- 计时：静态批处理里短请求也要等最长那条写完才一起返回。

与课件的差异：
- 课件写 `dtype="auto"`，这是 transformers 4.56 起的新参数名；本机 4.51 要写 `torch_dtype`
  （4.51 里写 dtype 不报错，但会被悄悄忽略）。这里用 float32，CPU 上比 bfloat16 快。
- 有效 token 数把结束符 <|im_end|> 也算进去了（它的编号不等于 pad 的编号）。

Python 语法点：
- `tokenizer.padding_side = "left"`：批里长短不一的 prompt 在左边补 pad，右端对齐，
  每条的最后一个位置都是"下一个 token 从这里接着写"。
- `(new_tokens != pad_id).sum()`：张量逐个比较得到 True/False，求和 = True 的个数。
"""
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)

prompts = [
    "用一句话介绍杭州。",
    "写一首关于秋天的五言绝句。",
    "详细解释为什么天空是蓝色的，不少于三百字。",
]
texts = [
    tokenizer.apply_chat_template(
        [{"role": "user", "content": p}], tokenize=False,
        add_generation_prompt=True, enable_thinking=False,
    )
    for p in prompts
]

tokenizer.padding_side = "left"
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
inputs = tokenizer(texts, return_tensors="pt", padding=True)
prompt_len = inputs["input_ids"].shape[1]

t0 = time.perf_counter()
outputs = model.generate(**inputs, max_new_tokens=512, do_sample=False)
sec = time.perf_counter() - t0

steps = outputs.shape[1] - prompt_len
useful = 0
for i, out in enumerate(outputs):
    new_tokens = out[prompt_len:]
    n = int((new_tokens != tokenizer.pad_token_id).sum())
    useful += n
    head = tokenizer.decode(new_tokens, skip_special_tokens=True).replace("\n", " ")[:20]
    print(f"请求 {i}: 有效生成 {n:3d} 个 token，后面 {steps - n:3d} 步在陪跑   「{head}…」")
total = 3 * steps
print(f"整批跑了 {steps} 步、{sec:.0f} 秒才一起返回；{total} 个位置里白算 {total - useful} 个（{(total - useful) / total:.0%}）")
