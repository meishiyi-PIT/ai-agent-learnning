"""课件 6 下半篇 5.2 RLHF / 5.3 DPO：偏好学习在优化什么。

一条偏好数据 = 同一个问题 + 一个好回答（chosen）+ 一个差回答（rejected），
和课件 4 第三章的 chosen/rejected 格式一致。

这里只做一件事：用 Qwen3-0.6B 算"模型生成这两个回答的概率"（每个 token 的平均 log 概率），
看模型现在更偏向哪个。DPO 训练做的就是：把 chosen 的概率往上推、rejected 的往下压，
并以训练前的自己（参考模型）为基准，防止跑太远。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s4_preference.py
"""
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B"
tok = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32).eval()

question = "用一句话解释什么是 RAG"
pair = {
    "chosen": "RAG 是先从知识库检索相关资料，再把资料和问题一起交给大模型生成答案，用来减少幻觉、补充最新知识。",
    "rejected": "RAG 是一种很厉害的 AI 技术，可以让 AI 变得更聪明，用处非常多。",
}

prompt = tok.apply_chat_template([{"role": "user", "content": question}], tokenize=False,
                                 add_generation_prompt=True, enable_thinking=False)
n_prompt = len(tok(prompt).input_ids)

for name, answer in pair.items():
    ids = tok(prompt + answer + "<|im_end|>", return_tensors="pt").input_ids
    with torch.no_grad():
        logp = torch.log_softmax(model(ids).logits[0, :-1], dim=-1)   # 第 t 位预测第 t+1 个 token
    target = ids[0, 1:]
    token_logp = logp.gather(1, target[:, None])[:, 0][n_prompt - 1:]  # 只取回答部分
    print(f"{name:8s} 回答 {len(token_logp)} 个 token，平均 log 概率 {token_logp.mean().item():.2f}")
