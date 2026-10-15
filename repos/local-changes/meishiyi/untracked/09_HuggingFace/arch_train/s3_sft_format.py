"""课件 6 下半篇第四节 SFT：一条"指令 → 回答"样本进模型前长什么样。

1. 用 Qwen3 的对话模板把一问一答拼成一整段文字（特殊标记标出谁在说话）
2. 算 loss 掩码：用户那段的 label 填 -100 不算 loss，只让模型学"回答"那段
   —— loss 公式和预训练一模一样（预测下一个 token），SFT 只换了数据、加了掩码
（课件 4 第三章 + code/lora/05_format_and_mask.py 做过同样的事，这里只看一条最短的）

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s3_sft_format.py
"""
from pathlib import Path

from transformers import AutoTokenizer

tok = AutoTokenizer.from_pretrained(Path(__file__).resolve().parent.parent / "models" / "Qwen3-0.6B")

msgs = [
    {"role": "user", "content": "解释一下 RAG"},
    {"role": "assistant", "content": "RAG 是先检索资料、再让模型参考资料作答。"},
]

full = tok.apply_chat_template(msgs, tokenize=False, enable_thinking=False)
print("1. 拼好的训练文本：")
print(full)

# 用户部分 = 模板渲染到"assistant 开口"为止
prompt = tok.apply_chat_template(msgs[:1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
n_prompt = len(tok(prompt).input_ids)
n_full = len(tok(full).input_ids)
print(f"2. 共 {n_full} 个 token：前 {n_prompt} 个（用户 + 模板）label = -100 不算 loss，"
      f"后 {n_full - n_prompt} 个（回答 + 结束标记）算 loss")
