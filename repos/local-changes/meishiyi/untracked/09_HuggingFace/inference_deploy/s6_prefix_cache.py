"""
课件 5《大模型推理部署》第四部分第 6 节：前缀缓存（Prefix Caching）

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可）：
    .venv/Scripts/python -X utf8 inference_deploy/s6_prefix_cache.py

场景：客服机器人，每个请求 = 同一段很长的"系统提示词 + 产品手册" + 不同的用户问题。
- 不用前缀缓存：每个请求都把"手册 + 问题"整段 Prefill 一遍；
- 用前缀缓存：手册那段的 KV Cache 只算一次存起来，之后每个请求复制一份，只 Prefill 自己的问题。
能这么做的原因：每个 token 的 K、V 只取决于它自己和它前面的 token，
同一段开头，不管后面接什么问题，算出来的 K、V 都一模一样。

第三组对照：在手册最前面加了一行"当前时间"（每个请求都不同），开头第一个 token 就变了，
后面所有 token 的 K、V 全跟着变，缓存一个都用不上——这就是"不变的放前面，会变的放后面"。

Python 语法点：
- `copy.deepcopy(cache)`：深拷贝一份缓存。直接传原缓存进去会被追加改掉，下个请求就脏了。
- `torch.allclose(a, b, atol=...)`：两个张量在误差范围内是否相等。
"""
import copy
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()

manual = ("You are a support agent for NovaRouter. Product manual: "
          + "The router supports WiFi 6, has four LAN ports, and resets by holding the button for 10 seconds. " * 60)
question = " Question: how do I reset the router? Answer:"

prefix_ids = tokenizer(manual, return_tensors="pt")["input_ids"]
q_ids = tokenizer(question, add_special_tokens=False, return_tensors="pt")["input_ids"]
full_ids = torch.cat([prefix_ids, q_ids], dim=1)


def timed(fn):
    t0 = time.perf_counter()
    with torch.no_grad():
        out = fn()
    return out, time.perf_counter() - t0


model(input_ids=full_ids[:, :8])  # 预热

# ① 不用前缀缓存：整段 Prefill
out_full, t_full = timed(lambda: model(input_ids=full_ids, use_cache=True))

# ② 前缀缓存：手册的缓存提前算好（只算一次，不计入每个请求的时间），请求来了只 Prefill 问题
with torch.no_grad():  # 必须在 no_grad 里：带梯度记录的张量不能 deepcopy
    prefix_cache = model(input_ids=prefix_ids, use_cache=True).past_key_values
out_hit, t_hit = timed(lambda: model(input_ids=q_ids, past_key_values=copy.deepcopy(prefix_cache), use_cache=True))

same = torch.allclose(out_full.logits[0, -1], out_hit.logits[0, -1], atol=1e-3)
print(f"手册 {prefix_ids.shape[1]} token + 问题 {q_ids.shape[1]} token")
print(f"① 整段 Prefill        : {t_full:5.2f} 秒")
print(f"② 命中前缀，只算问题  : {t_hit:5.2f} 秒   快 {t_full / t_hit:.0f} 倍，下一个词的打分一致: {same}")

# ③ 开头加一行会变的内容：和缓存里的前缀从第一个 token 就对不上
changed = tokenizer("Time: 2026-09-29 15:42. " + manual, return_tensors="pt")["input_ids"]
n_same = 0
for a, b in zip(prefix_ids[0].tolist(), changed[0].tolist()):
    if a != b:
        break
    n_same += 1
print(f"③ 开头加一行时间后，和缓存前缀相同的开头 token 数: {n_same} → 缓存全部作废，只能整段重算")
