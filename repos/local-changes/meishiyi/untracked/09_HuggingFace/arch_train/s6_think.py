"""课件 6 下半篇 5.5 推理能力训练："先想后答"在模型输出里长什么样。

同一个模型（Qwen3-0.6B）、同一道题，只切一个开关：
  enable_thinking=False：模板预先塞一个空的 <think>\n\n</think>，模型直接答
  enable_thinking=True ：模板只开到 assistant，模型自己先写 <think>…</think> 再答
MiniMind 的 open_thinking=0/1 是同一个设计（README "open_thinking" 一节）。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s6_think.py
"""
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B"
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()

q = "一个笼子里有鸡和兔共 10 只，脚共 28 只，兔有几只？"
for think in [False, True]:
    prompt = tok.apply_chat_template([{"role": "user", "content": q}], tokenize=False,
                                     add_generation_prompt=True, enable_thinking=think)
    ids = tok(prompt, return_tensors="pt").input_ids
    with torch.no_grad():
        out = model.generate(ids, max_new_tokens=1200, do_sample=False)
    text = tok.decode(out[0, ids.shape[1]:], skip_special_tokens=True)
    thought, _, answer = text.rpartition("</think>")
    thought = thought.replace("<think>", "").strip()
    print(f"\n=== enable_thinking={think} ===")
    print("模板结尾：", repr(prompt[-30:]))
    print(f"生成 {out.shape[1] - ids.shape[1]} 个 token；思考部分 {len(thought)} 字：{thought[:100]}…")
    print("最终回答：", answer.strip()[:150].replace("\n", " "))
