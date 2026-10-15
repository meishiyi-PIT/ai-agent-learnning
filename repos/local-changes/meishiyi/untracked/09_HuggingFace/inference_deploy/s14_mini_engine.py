"""
课件 5《大模型推理部署》第 4 节：一条请求在 vLLM 里的九驿站 —— 用 transformers 手写一个单请求版

运行（在 meishiyi/09_HuggingFace 目录下，CPU 即可）：
    .venv/Scripts/python -X utf8 inference_deploy/s14_mini_engine.py

不调 generate，自己把 ②~⑧ 站一步步写出来（① API Server 和多请求调度省掉）：
    ② InputProcessor：套对话模板 + 分词，文字 → token 编号
    ③④⑤ 调度 + GPU 执行 Prefill：整段编号过一遍模型，得到每层的 KV Cache 和最后一个位置的打分
    ⑦ Sampler：从打分里挑下一个 token（这里用贪心，等于 temperature=0）
    ⑥ Decode 循环：每步只送上一步挑出的 1 个 token + 旧缓存，拿回新打分和追加过的缓存
    ⑧ Detokenize：增量转回文字——把"到目前为止全部编号"解码，减去上次已输出的部分
    ⑨ 流式输出：这里用 print(..., end="", flush=True) 代替 SSE，每步蹦几个字
注意 ⑤~⑨ 不是只走一次：每一步都 采样 → 转文字 → 推给客户端，首 token 也是 Sampler 挑出来的。

Python 语法点：
- `logits[0, -1].argmax()`：取批里第 0 条、最后一个位置的打分，最高分的下标就是下一个 token 编号。
- `.item()`：把只含一个数的张量变成普通 Python int。
- 增量解码为什么不直接 decode 新 token：生僻字、新 emoji 可能被切成几个 token，单独解码会得到乱码"�"，
  所以每次解码全部编号，再切掉已输出的前缀；结尾还是"�"说明字没凑齐，这一步先不输出（演示见 s15）。
- 缓存长度 = 输入 token 数 + Decode 步数：每步送进去 1 个刚挑出的 token，它的 K、V 追加进缓存；
  最后挑出的结束符不再送进模型，所以不算在内。
"""
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "models/Qwen3-0.6B"
MAX_NEW = 60
tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
model = AutoModelForCausalLM.from_pretrained(MODEL_DIR, torch_dtype=torch.float32)
model.eval()

# ② InputProcessor
text = tokenizer.apply_chat_template(
    [{"role": "user", "content": "用两句话介绍长城。"}], tokenize=False,
    add_generation_prompt=True, enable_thinking=False,
)
ids = tokenizer(text, return_tensors="pt")["input_ids"]
print(f"② 分词：{ids.shape[1]} 个 token")

with torch.no_grad():
    # ③④⑤ Prefill
    t0 = time.perf_counter()
    out = model(input_ids=ids, use_cache=True)
    ttft = time.perf_counter() - t0
    cache = out.past_key_values
    print(f"⑤ Prefill 一步 {ttft * 1000:.0f} 毫秒，缓存 {len(cache.key_cache)} 层 × {cache.key_cache[0].shape[2]} 个 token")

    generated, shown, t1 = [], "", time.perf_counter()
    print("⑨ 流式输出：", end="", flush=True)
    for step in range(MAX_NEW):
        next_id = out.logits[0, -1].argmax().item()          # ⑦ Sampler
        if next_id == tokenizer.eos_token_id:                 # 结束条件 → 回收缓存
            break
        generated.append(next_id)
        full = tokenizer.decode(generated)                    # ⑧ 增量 Detokenize
        if not full.endswith("�"):                            # 结尾是半个字就先不推，等凑齐（见 s15）
            print(full[len(shown):], end="", flush=True)      # ⑨ 推给客户端
            shown = full
        out = model(input_ids=torch.tensor([[next_id]]), past_key_values=cache, use_cache=True)  # ⑥ Decode 一步
        cache = out.past_key_values
    per = (time.perf_counter() - t1) / max(len(generated), 1)
print(f"\n⑥ Decode {len(generated)} 步，平均每步 {per * 1000:.0f} 毫秒；遇到结束符，缓存 {cache.key_cache[0].shape[2]} 个 token 回收")
