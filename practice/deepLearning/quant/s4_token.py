"""
【token 是什么 / Embedding 为什么是"查表" / "生成 64 个 token"是什么意思】
配合 C:\\workspace\\code\\lora\\quant_demo.py 在 AutoDL 上的输出讲解（2026-09-28）。

1. token = 模型读写文字的最小单位。分词器（tokenizer）把一句话切成一段段，每段对应词表里的一个编号（token id）。
   中文里常见词整词一个 token（"模型""量化"），生僻组合会拆成单字；标点也是 token。
   本模型词表约 15 万个 token；Embedding 表正好每个编号一行（152064 行 × 3584 列，行数比词表略多是为了对齐补的空行）。

2. Embedding 是"按编号取第几行"，不是矩阵乘法 —— 所以它不是线性层，bitsandbytes 不替换它：
       "量化" 的 id = 108048  →  embed_tokens.weight[108048]   （直接取出这一行的 3584 个数）
   线性层才是"输入向量 × 权重矩阵"，每个权重每个 token 都要参与乘法。

3. 生成 = 一次只往后写一个 token 的循环：读"问题 + 已写的部分" → 算出下一个 token → 接到末尾 → 再来。
   quant_demo.py 的 max_new_tokens=64 就是这个循环最多转 64 圈，所以输出在"以"字处被截断；
   token/s = 每秒转多少圈。每转一圈都要把全部权重从显存读一遍，所以权重越小、读得越快（前提是计算不添乱，见 int8 反例）。

用法（本机，只下分词器几个小文件，不下 15 GB 权重）：
    C:\\workspace\\meishiyi\\09_HuggingFace\\.venv\\Scripts\\python.exe -X utf8 s4_token.py

2026-09-28 本机实测输出（transformers 4.51.3）：
    词表大小: 151665
    14 个字 -> 8 个 token
    <｜begin▁of▁sentence｜>(151646) | 用(11622) | 一句话(105321) | 解释(104136) | 什么是(106582) | 模型(104949) | 量化(108048) | ：(5122)
    35 个字 -> 25 个 token
    <｜begin▁of▁sentence｜>(151646) | 模型(104949) | 量化(108048) | 是(20412) | 将(44063) | 模型(104949) | 的(9370) | 参数(32665) | ...
    第一个 <｜begin▁of▁sentence｜> 是分词器自动加的"开头标记"，不是文字。
"""

import os

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from transformers import AutoTokenizer  # noqa: E402

tok = AutoTokenizer.from_pretrained("deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
print(f"词表大小: {len(tok)}")

texts = [
    "用一句话解释什么是模型量化：",  # quant_demo.py 的 PROMPT
    "模型量化是将模型的参数转换为更小的数值范围，以减少模型的大小和计算量。",  # bf16 输出的第一句
]
for text in texts:
    ids = tok(text)["input_ids"]
    pieces = [tok.decode([i]) for i in ids]
    print(f"\n{len(text)} 个字 -> {len(ids)} 个 token")
    print(" | ".join(f"{p}({i})" for p, i in zip(pieces, ids)))
