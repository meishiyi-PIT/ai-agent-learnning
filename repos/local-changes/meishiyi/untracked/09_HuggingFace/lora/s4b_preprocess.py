"""
模块六 · 《1.大模型LoRA微调》第四章 4.3（上）：课件 preprocess_function 走读、勘误复现、修正版
=================================================================================================

【SFT 数据处理要做的事，一句话】
    把一条 (问题, 思维链, 回答) 变成模型能吃的三样：
        input_ids      整段对话的 token id（模板 + 问题 + 回答 + EOS）
        attention_mask 哪些位置是真 token（1）、哪些是 pad（0）
        labels         每个位置"该预测什么"；prompt 部分填 -100（不算 loss），回答部分填真实 id
    -100 是 PyTorch CrossEntropyLoss 的 ignore_index（模块五翻译项目里 ignore_index=PAD_ID 是同一个机制）：
        prompt 是用户给的，不需要模型学着"背题"，只学"怎么答"。

【课件的五步，每步在哪里出问题（demo 1 复现）】
    Step 1  full_text = apply_chat_template(messages)             ← 4a 事实 3：assistant 里的 <think>…</think> 被模板丢掉，cot 没进训练文本
    Step 2  prompt_text = apply_chat_template(messages[:-1], add_generation_prompt=True)
                                                                  ← 末尾多出 "<｜Assistant｜><think>\\n"，而 full_text 里没有 → prompt 不是 full 的前缀
    Step 3  tokenizer.encode(..., padding="max_length", max_length=1024, truncation=True)
                                                                  ← padding="max_length" 把 prompt_ids 也填到 1024（这套 tokenizer 是左填充，pad 在前面）
    Step 4  if len(full_ids) > max_length: 截断+补 EOS             ← truncation=True 已经截过，len 恒等于 1024，这段永远走不到
    Step 5  labels = [-100]*len(prompt_ids) + full_ids[len(prompt_ids):]
                                                                  ← len(prompt_ids) 恒等于 1024 → labels 全是 -100，一个 token 都不训
            attention_mask = [1]*len(ids)                         ← pad 位置也标成 1，模型会"看"到 pad
    （4c 还会看到：后面的 DataCollatorForLanguageModeling 会把 labels 整个覆盖掉，等于这五步白做。）

【修正版 preprocess_fixed 的思路（demo 2）】
    ① prompt 用模板渲染（add_generation_prompt=True，末尾自带 "<think>\\n"）；
    ② 回答部分自己拼："{cot}\\n</think>\\n{response}" + EOS —— 不经过模板，cot 保住，prompt 天然是前缀；
    ③ prompt 和回答分别 encode，不 padding；input_ids = 两段相接，labels = [-100]*len(prompt) + 回答 id；
    ④ 超长就截断，但保证最后一个 token 是 EOS（模型要学会"停"）；
    ⑤ 不在这里 pad：长短不一的样本交给 4c 的 DataCollatorForSeq2Seq 按 batch 内最长动态填充，labels 用 -100 填。
    （分别 encode 再拼接，边界处 BPE 合并可能和整段 encode 差一两个 token，业界 TRL 也是这么做的，可接受。）

运行（在 meishiyi/09_HuggingFace 目录）：
    PYTHONUTF8=1 uv run python lora/s4b_preprocess.py
"""

from pathlib import Path

from transformers import AutoTokenizer

TOK_DIR = Path(__file__).resolve().parent.parent / "models" / "deepseek-r1-distill-qwen-tokenizer"
tokenizer = AutoTokenizer.from_pretrained(TOK_DIR)

SYSTEM = "您是一位在临床推理、诊断和治疗计划方面具有高级知识的医学专家。请回答以下医学问题。"

# 模拟 medical-o1-reasoning-SFT 数据集的两条样本（列名和课件一致：Question / Complex_CoT / Response）
SAMPLES = {
    "Question": [
        "患者咳嗽两周，夜间加重，无发热，最可能的诊断是什么？",
        "一位 30 岁男性突发右下腹痛伴发热，查体麦氏点压痛，首先考虑什么？",
    ],
    "Complex_CoT": [
        "夜间加重的干咳、无发热，先考虑咳嗽变异性哮喘或上气道咳嗽综合征。",
        "右下腹痛、发热、麦氏点压痛三联征指向急性阑尾炎。",
    ],
    "Response": [
        "最可能是咳嗽变异性哮喘，建议做支气管激发试验。",
        "首先考虑急性阑尾炎，建议血常规和腹部超声。",
    ],
}


def preprocess_courseware(examples, max_length=1024):
    """课件 4.3 的 preprocess_function 原样照抄（只加了标注），用来复现问题。"""
    input_ids_list, labels_list = [], []
    for question, cot, response in zip(examples["Question"], examples["Complex_CoT"], examples["Response"]):
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
            {"role": "assistant", "content": f"<think>\n{cot}\n</think>\n{response}"},
        ]
        full_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        prompt_messages = messages[:-1]
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        full_ids = tokenizer.encode(full_text, add_special_tokens=False,
                                    max_length=max_length, padding="max_length", truncation=True)
        prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False,
                                      max_length=max_length, padding="max_length", truncation=True)
        if len(full_ids) > max_length:                      # 永远 False
            full_ids = full_ids[:max_length - 1]
            full_ids.append(tokenizer.eos_token_id)
        prompt_len = len(prompt_ids)                        # 恒等于 max_length
        labels = [-100] * prompt_len + full_ids[prompt_len:]
        labels = labels[:len(full_ids)]
        input_ids_list.append(full_ids)
        labels_list.append(labels)
    return {
        "input_ids": input_ids_list,
        "attention_mask": [[1] * len(ids) for ids in input_ids_list],
        "labels": labels_list,
    }


def preprocess_fixed(examples, max_length=1024):
    """修正版：cot 保住、prompt 是前缀、只训回答、保 EOS、不在这里 pad。"""
    out = {"input_ids": [], "attention_mask": [], "labels": []}
    for question, cot, response in zip(examples["Question"], examples["Complex_CoT"], examples["Response"]):
        prompt_messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": question},
        ]
        prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
        answer_text = f"{cot}\n</think>\n{response}{tokenizer.eos_token}"
        prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)   # 模板已含 bos，别再加
        answer_ids = tokenizer.encode(answer_text, add_special_tokens=False)
        input_ids = prompt_ids + answer_ids
        labels = [-100] * len(prompt_ids) + answer_ids
        if len(input_ids) > max_length:                    # 截断也要保住最后的 EOS
            input_ids = input_ids[:max_length - 1] + [tokenizer.eos_token_id]
            labels = labels[:max_length - 1] + [tokenizer.eos_token_id]
        out["input_ids"].append(input_ids)
        out["attention_mask"].append([1] * len(input_ids))
        out["labels"].append(labels)
    return out


def demo_courseware_bugs():
    print("=" * 64)
    print("demo 1：课件 preprocess_function 原样跑一遍（max_length=1024）")
    print("=" * 64)
    res = preprocess_courseware(SAMPLES)
    ids, labels, mask = res["input_ids"][0], res["labels"][0], res["attention_mask"][0]
    n_pad = 0
    while ids[n_pad] == tokenizer.pad_token_id:     # 只数开头的 pad（末尾那个同 id 的是 EOS，不是 pad）
        n_pad += 1
    print(f"  样本 0：len(input_ids) = {len(ids)}，其中开头 pad 有 {n_pad} 个，真 token 只有 {len(ids) - n_pad} 个（含末尾 EOS）")
    print(f"          pad 在哪头？前 3 个 id = {ids[:3]}，后 3 个 id = {ids[-3:]}  （pad_token_id = {tokenizer.pad_token_id}，左填充）")
    print(f"          attention_mask 之和 = {sum(mask)}  ← pad 位置也标成了 1")
    n_train = sum(1 for t in labels if t != -100)
    print(f"          labels 里参与训练的 token 数 = {n_train}  ← 全是 -100，一个都不训")
    text = tokenizer.decode([t for t in ids if t != tokenizer.pad_token_id])
    print(f"          去掉 pad 后解码，cot 在里面吗？ {SAMPLES['Complex_CoT'][0] in text}")
    print()


def demo_fixed():
    print("=" * 64)
    print("demo 2：修正版 preprocess_fixed")
    print("=" * 64)
    res = preprocess_fixed(SAMPLES)
    for i in range(2):
        ids, labels = res["input_ids"][i], res["labels"][i]
        n_prompt = sum(1 for t in labels if t == -100)
        trained = [t for t in labels if t != -100]
        print(f"  样本 {i}：总长 {len(ids)}，prompt {n_prompt} 个 token 不训，回答 {len(trained)} 个 token 参与训练，最后一个是 EOS？ {ids[-1] == tokenizer.eos_token_id}")
        print("          参与训练的部分解码 = " + tokenizer.decode(trained).replace("\n", "\\n"))
    print("  两条样本长度不同 → 4c 用 DataCollatorForSeq2Seq 按 batch 动态填充，labels 用 -100 填。")
    print()


if __name__ == "__main__":
    demo_courseware_bugs()
    demo_fixed()
