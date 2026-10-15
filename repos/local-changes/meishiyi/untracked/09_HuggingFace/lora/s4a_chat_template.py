"""
模块六 · 《1.大模型LoRA微调》第四章 4.1–4.2：工具链 + 数据 —— chat template 到底长什么样
==========================================================================================

第 4 站分四小块：4a 工具链与数据格式（本文件）→ 4b 课件 preprocess_function 走读与勘误 → 4c PEFT + Trainer 真代码 → 4d 合并推理 + 超参/评测/坑
本站用 `models/deepseek-r1-distill-qwen-tokenizer/`（DeepSeek-R1-Distill-Qwen-1.5B 的 tokenizer，和课件 7B 同一套 chat_template）。

【4.1 工具链三选一】
    LLaMA-Factory：一站式框架带 WebUI，不想写代码选它；
    Hugging Face PEFT：官方库，代码最灵活，课件 4.3 用的就是它（LoraConfig / get_peft_model / PeftModel）；
    Unsloth：手写 Triton 内核的加速库，显存紧张选它，但有模型适配清单。
    三家都支持 LoRA/QLoRA 和 DeepSeek/Qwen 全系。本站用 PEFT，因为要看清每一步。

【4.2 数据：质量 > 数量】
    LoRA 微调 = 用一批高质量、目标明确的样本把模型往你要的方向"轻轻推过去"，几百条精品常吊打几万条脏数据。
    好数据六标准：任务目标单一 / 输入贴近真实 / 输出格式统一 / 答案互不冲突 / 要有边界样本 / 留验证集测试集。
    两种格式：
        Alpaca：{"instruction", "input", "output"} 单轮指令；
        messages（ShareGPT）：{"messages": [{"role","content"}, ...]} 多轮对话，聊天模型常用。
    模型训练时看到的不是 JSON，是 tokenizer.apply_chat_template 把 messages 渲染成的一长串文本 —— demo 1 看真实样子。
    铁律：训练时的对话模板和推理时必须一致。模板 = 那些 <｜User｜> <｜Assistant｜> 之类的特殊记号怎么摆；对不上，模型不知道"该谁说话了"。

【这套 tokenizer 的三个事实（demo 2、3 亲眼看，4b 的勘误全由它们引出）】
    事实 1：pad_token 和 eos_token 是同一个记号 <｜end▁of▁sentence｜>。
        后果：凡是"把 pad 位置屏蔽掉"的代码，会连句末的 EOS 一起屏蔽 → 模型学不会"说完了该停"。
    事实 2：add_generation_prompt=True 时，模板在末尾追加 "<｜Assistant｜><think>\\n"（R1 系列强制先思考）。
    事实 3：assistant 消息里若含 "</think>"，模板只保留 "</think>" 之后的内容（历史对话不回放思考过程）。
        后果：课件把 "<think>\\n{cot}\\n</think>\\n{response}" 塞进 assistant content 再渲染，cot 被整段丢掉，
        且渲染出的 full_text 里没有 "<think>"，而 prompt_text 末尾有 → prompt 不是 full 的前缀，靠 len(prompt_ids) 切 labels 的前提就塌了。

运行（在 meishiyi/09_HuggingFace 目录）：
    PYTHONUTF8=1 uv run python lora/s4a_chat_template.py
"""

from pathlib import Path

from transformers import AutoTokenizer

TOK_DIR = Path(__file__).resolve().parent.parent / "models" / "deepseek-r1-distill-qwen-tokenizer"
tokenizer = AutoTokenizer.from_pretrained(TOK_DIR)

SYSTEM = "您是一位在临床推理、诊断和治疗计划方面具有高级知识的医学专家。请回答以下医学问题。"
QUESTION = "患者咳嗽两周，夜间加重，无发热，最可能的诊断是什么？"
COT = "夜间加重的干咳、无发热，先考虑咳嗽变异性哮喘或上气道咳嗽综合征。"
RESPONSE = "最可能是咳嗽变异性哮喘，建议做支气管激发试验。"


def demo_special_tokens():
    print("=" * 64)
    print("demo 1：这套 tokenizer 的特殊记号")
    print("=" * 64)
    print(f"  bos = {tokenizer.bos_token!r} (id {tokenizer.bos_token_id})")
    print(f"  eos = {tokenizer.eos_token!r} (id {tokenizer.eos_token_id})")
    print(f"  pad = {tokenizer.pad_token!r} (id {tokenizer.pad_token_id})   ← 事实 1：pad == eos → {tokenizer.pad_token_id == tokenizer.eos_token_id}")
    print(f"  padding_side = {tokenizer.padding_side}")
    print(f"  '<think>' id = {tokenizer.convert_tokens_to_ids('<think>')}，'</think>' id = {tokenizer.convert_tokens_to_ids('</think>')}")
    print()


def demo_alpaca_to_messages_and_render():
    print("=" * 64)
    print("demo 2：Alpaca 样本 → messages → apply_chat_template 渲染出的真实训练文本")
    print("=" * 64)
    alpaca = {"instruction": SYSTEM, "input": QUESTION, "output": RESPONSE}
    messages = [
        {"role": "system", "content": alpaca["instruction"]},
        {"role": "user", "content": alpaca["input"]},
        {"role": "assistant", "content": alpaca["output"]},
    ]
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)
    print("  [完整对话 add_generation_prompt=False]")
    print("  " + full.replace("\n", "\\n"))
    print("  [只有 prompt add_generation_prompt=True]")
    print("  " + prompt.replace("\n", "\\n"))
    print(f"  事实 2：prompt 末尾是 {prompt[-20:]!r}")
    print(f"  prompt 是 full 的前缀吗？ {full.startswith(prompt)}   ← 没有 <think> 时也不是：full 里 assistant 后直接接正文")
    print()


def demo_think_is_stripped():
    print("=" * 64)
    print("demo 3：把 <think>…</think> 塞进 assistant content 会怎样（课件 4.3 的写法）")
    print("=" * 64)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": QUESTION},
        {"role": "assistant", "content": f"<think>\n{COT}\n</think>\n{RESPONSE}"},
    ]
    full = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    print("  渲染结果：")
    print("  " + full.replace("\n", "\\n"))
    print(f"  cot 还在吗？ {COT in full}   ← 事实 3：模板 split('</think>')[-1]，思维链整段丢失")
    print(f"  '<think>' 还在吗？ {'<think>' in full}")
    print()
    print("  正确做法（4b 用）：不让模板渲染 assistant 部分，自己拼：")
    prompt = tokenizer.apply_chat_template(messages[:-1], tokenize=False, add_generation_prompt=True)
    answer = f"{COT}\n</think>\n{RESPONSE}{tokenizer.eos_token}"
    print("  " + (prompt + answer).replace("\n", "\\n"))
    print("  prompt 以 '<think>\\n' 结尾，answer 从 cot 接上，prompt 天然是前缀，cot 也保住了。")
    print()


if __name__ == "__main__":
    demo_special_tokens()
    demo_alpaca_to_messages_and_render()
    demo_think_is_stripped()
