"""
检查课件最新代码目录 C:/workspace/code/lora 里的 train.json / validation.json：
① load_dataset("json") 能否直接读 JSON 数组格式；② 用真 tokenizer 统计 prompt+回答 的 token 长度分布，决定 max_length。
运行：cd meishiyi/09_HuggingFace && PYTHONUTF8=1 uv run python lora/check_course_data.py
"""

import random
from pathlib import Path

from datasets import load_dataset
from transformers import AutoTokenizer

COURSE = Path("C:/workspace/code/lora")
TOK_DIR = Path(__file__).resolve().parent.parent / "models" / "deepseek-r1-distill-qwen-tokenizer"
tokenizer = AutoTokenizer.from_pretrained(TOK_DIR)
SYSTEM = "您是一位在临床推理、诊断和治疗计划方面具有高级知识的医学专家。请回答以下医学问题。"

ds = load_dataset("json", data_files={"train": str(COURSE / "train.json"), "valid": str(COURSE / "validation.json")})
print(ds)

rows = ds["train"].shuffle(seed=0).select(range(1000))
lens = []
for r in rows:
    prompt = tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": r["Question"]}],
        tokenize=False, add_generation_prompt=True)
    answer = f"{r['Complex_CoT']}\n</think>\n{r['Response']}{tokenizer.eos_token}"
    lens.append(len(tokenizer.encode(prompt, add_special_tokens=False)) + len(tokenizer.encode(answer, add_special_tokens=False)))
lens.sort()
n = len(lens)
print(f"抽样 {n} 条 token 总长：中位数 {lens[n // 2]}，90% 分位 {lens[int(n * 0.9)]}，99% 分位 {lens[int(n * 0.99)]}，最大 {lens[-1]}")
for cap in (512, 768, 1024, 1536):
    print(f"  max_length={cap:4d} 时被截断的比例：{100 * sum(1 for x in lens if x > cap) / n:.1f}%")
