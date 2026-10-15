"""课件 6 下半篇第二节：文字 → Token → ID → 向量。

用 Qwen3-0.6B 走一遍课件图里的流水线：
  1. 分词器把一句话切成 token
  2. 每个 token 查表得到 ID
  3. Embedding 层按 ID 取出一行向量
再算一笔账：词表大小 × 隐藏维度 = Embedding 层参数量，对比 MiniMind 的 6400 词表。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s1_tokenize.py
"""
from pathlib import Path

import torch
from transformers import AutoConfig, AutoTokenizer
from safetensors import safe_open

MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B"

tok = AutoTokenizer.from_pretrained(MODEL_DIR)
cfg = AutoConfig.from_pretrained(MODEL_DIR)

text = "我想学习大模型"
ids = tok.encode(text)
# ByteLevel BPE 的 token 是字节串，直接打印是乱码；逐个 decode 回人话
pieces = [tok.decode([i]) for i in ids]
print("1. 切成 token:", pieces)
print("2. 查表得 ID :", ids)

# 3. 只读 embedding 那一张表，不加载整个模型
with safe_open(MODEL_DIR / "model.safetensors", framework="pt") as f:
    emb = f.get_tensor("model.embed_tokens.weight")
print("3. Embedding 表形状:", tuple(emb.shape), "(词表行数 × 每行向量长度)")
vec = emb[ids[0]].float()
print(f"   第一个 token '{pieces[0]}' 的向量前 5 维:", [round(x, 4) for x in vec[:5].tolist()])

# 账：embedding 占多少参数
emb_params = cfg.vocab_size * cfg.hidden_size
print(f"\nQwen3-0.6B: 词表 {cfg.vocab_size:,} × 维度 {cfg.hidden_size} = {emb_params/1e6:.0f}M 参数")
mini = 6400 * 768
print(f"MiniMind  : 词表 6,400 × 维度 768 = {mini/1e6:.1f}M 参数")

# 特殊标记：工具调用和思考从分词器层就预留了
for s in ["<think>", "<tool_call>", "<tool_response>"]:
    print(f"特殊标记 {s:16s} → ID {tok.convert_tokens_to_ids(s)}（整体算 1 个 token）")
