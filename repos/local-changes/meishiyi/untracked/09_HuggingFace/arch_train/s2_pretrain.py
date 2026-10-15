"""课件 6 下半篇第三节：预训练 = 文字接龙；预训练模型为什么还不能上岗。

实验 1：给"人工智能正在改变"，看预训练模型对下一个 token 的候选概率，
        以及真实答案"世界"的 loss（= -log 概率），这就是预训练每一步在优化的数。
实验 2：同一个问题"解释一下 RAG"，分别喂给
        Base 模型（只做过预训练）和 Qwen3-0.6B（做过后训练），不套对话模板、贪心生成，
        看 Base 是"回答"还是"续写"。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s2_pretrain.py
"""
import math
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODELS = Path(__file__).resolve().parent.parent / "models"
BASE = MODELS / "Qwen3-0.6B-Base"
CHAT = MODELS / "Qwen3-0.6B"


def load(path):
    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForCausalLM.from_pretrained(path, torch_dtype=torch.float32)
    model.eval()
    return tok, model


# ---------- 实验 1：下一个 token 的候选 + loss ----------
tok, base = load(BASE)
prefix = "人工智能正在改变"
ids = tok(prefix, return_tensors="pt").input_ids
with torch.no_grad():
    logits = base(ids).logits[0, -1]          # 最后一个位置 = 对"下一个 token"的打分
probs = torch.softmax(logits, dim=-1)
top = torch.topk(probs, 5)
print(f"实验 1：'{prefix}' 的下一个 token 候选（Base 模型）")
for p, i in zip(top.values, top.indices):
    print(f"  {tok.decode([int(i)])!r:10s} 概率 {p.item():.3f}")

target_id = tok.encode("世界")[0]
p_true = probs[target_id].item()
print(f"  若真实下一个是 {tok.decode([target_id])!r}：概率 {p_true:.3f}，loss = -ln({p_true:.3f}) = {-math.log(p_true):.2f}")


# ---------- 实验 2：Base 续写 vs 后训练模型回答 ----------
def gen(tok, model, text, n=60):
    x = tok(text, return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**x, max_new_tokens=n, do_sample=False)
    return tok.decode(out[0, x.input_ids.shape[1]:], skip_special_tokens=True).replace("\n", "⏎")


tok_c, chat = load(CHAT)
# 第二个问题是闲聊，没有"标准网页答案"可模仿，更能看出 Base 在续写还是在回应人
for question in ["解释一下 RAG", "我今天心情不好"]:
    print(f"\n实验 2：直接喂 '{question}'，贪心生成 60 个 token")
    print("  [Base，只做过预训练]", gen(tok, base, question))
    msgs = [{"role": "user", "content": question}]
    prompt = tok_c.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    print("  [Qwen3-0.6B，做过后训练，套对话模板]", gen(tok_c, chat, prompt))
