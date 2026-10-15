"""追问：SFT 的格式就是 <|im_start|> 那样吗？和课件 4 学的 Alpaca / ShareGPT 什么关系？

两层格式：
  存储格式（Alpaca / ShareGPT JSON）：数据集文件里怎么存，人读、框架读，跟模型无关
  对话模板（chat template）：训练前框架把字段填进模板拼成一段文字，每个模型家族各有一套
同一条 ShareGPT 样本 → 换两个模型的模板 → 拼出的训练文本不一样。

运行：cd meishiyi/09_HuggingFace && .venv/Scripts/python -X utf8 arch_train/s3b_template_compare.py
"""
import json
from pathlib import Path

from transformers import AutoTokenizer

MODELS = Path(__file__).resolve().parent.parent / "models"

# 存储格式：ShareGPT（多轮用它；单轮 Alpaca 写成 instruction/input/output 三个字段，意思一样）
sharegpt = {"conversations": [
    {"from": "human", "value": "解释一下 RAG"},
    {"from": "gpt", "value": "RAG 是先检索资料、再让模型参考资料作答。"},
]}
print("存储格式（ShareGPT）：", json.dumps(sharegpt, ensure_ascii=False))

# 框架做的事：human/gpt 改名成 user/assistant，再交给各模型自己的模板
role = {"human": "user", "gpt": "assistant"}
msgs = [{"role": role[m["from"]], "content": m["value"]} for m in sharegpt["conversations"]]

for name in ["Qwen3-0.6B", "deepseek-r1-distill-qwen-tokenizer"]:
    tok = AutoTokenizer.from_pretrained(MODELS / name)
    text = tok.apply_chat_template(msgs, tokenize=False)
    print(f"\n[{name} 的模板]\n{text}")
