"""
模块六 · 《1.大模型LoRA微调》第四章 4.3（下）+ 4.4–4.6：合并权重、推理模板一致、超参/评测/坑清单
====================================================================================================

先跑 s4c_peft_trainer.py（它把迷你基座存到 lora/out/base、adapter 存到 lora/out/adapter）。

【合并（课件 4.3 第二段代码）—— demo 1】
    base  = AutoModelForCausalLM.from_pretrained(基座)
    model = PeftModel.from_pretrained(base, adapter 目录)      ← 把 A、B 挂回去（此时还是两条路）
    model = model.merge_and_unload()                          ← W_new = W + (α/r)·B·A 写回原 Linear，拆掉旁路，返回普通模型
    model.save_pretrained(合并目录)                            ← 第 3 站 demo 4 的"合并"用法；课件漏了 tokenizer.save_pretrained，部署时要一起存
    demo 1 验证：合并前后同一输入 logits 逐元素一致；合并后参数量 = 基座参数量；q_proj 变回普通 nn.Linear。

【推理时模板必须和训练一致（课件 4.3 第三段代码的勘误⑥）—— demo 2】
    训练用的是 chat template（<｜User｜>…<｜Assistant｜><think>\\n…），推理却用 Alpaca 风格的 "### 任务描述 / ### 问题 / ### 回答"。
    模型在训练里从没见过 "### 问题:" 这种格式，效果打折。正确做法：推理时同样 apply_chat_template(add_generation_prompt=True)。
    generate 常用参数：max_new_tokens 最多生成几个 token；streamer=TextStreamer 边生成边打印；
        这里模型是随机初始化的迷你模型，生成的是乱码，看的是"prompt 怎么拼"，不看质量。

【4.4 超参心法（顺序别乱）】
    1 先保守跑通：r=8 或 16，α=2r，lr=2e-4，3 个 epoch，q_proj+v_proj —— 先证明流程通、数据格式对；
    2 小数据配小秩：<5K 样本 r=8；>50K 再考虑 r=32+；
    3 复杂任务组合拳：r 到 32/64 + rsLoRA（PEFT use_rslora=True，缩放改 α/√r）+ 挂到 FFN；
    4 多挂几层 > 单层加大 r（第 3 站 3.5 论文结论）；
    5 lr 别贪：1e-4 ~ 3e-4，超过 5e-4 容易说胡话。

【4.5 评测：别只盯 loss】
    loss 降只说明在"背"训练数据。三组对比：裸基座 / 基座 + 好提示词 / LoRA 后 —— 微调打不过一个好提示词，这轮微调价值存疑。
    分类算准确率/F1；生成做人工评分或强模型打分；业务任务建固定 Bad Case 集每轮原样重测。看格式稳定性、风格一致性、边界输入、幻觉。

【4.6 坑清单（本站亲眼见过的打 ✔）】
    数据越多越好 ✘ / 目标太抽象 / 拿知识库需求去微调 / 没有测试集 / ✔ 训练推理模板不一致（demo 2）/ epoch 贪多（课件自己 20 轮）/
    "玄学"结果 → 先查数据（✔ 本站 4b：labels 全 -100、cot 丢失，这种就是"玄学"的真身），再调参数，最后才换方案。

运行（在 meishiyi/09_HuggingFace 目录，先跑 s4c）：
    PYTHONUTF8=1 uv run python lora/s4d_merge_infer.py
"""

import shutil
from pathlib import Path

import torch
from peft import PeftModel
from torch import nn
from transformers import AutoModelForCausalLM, AutoTokenizer, TextStreamer

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
BASE_DIR, ADAPTER_DIR, MERGED_DIR = OUT / "base", OUT / "adapter", OUT / "merged"

SYSTEM = "您是一位在临床推理、诊断和治疗计划方面具有高级知识的医学专家。请回答以下医学问题。"
QUESTION = "患者咳嗽两周，夜间加重，无发热，最可能的诊断是什么？"


def demo_merge():
    print("=" * 64)
    print("demo 1：PeftModel.from_pretrained → merge_and_unload → save_pretrained")
    print("=" * 64)
    tokenizer = AutoTokenizer.from_pretrained(BASE_DIR)
    base = AutoModelForCausalLM.from_pretrained(BASE_DIR, local_files_only=True)
    n_base = sum(p.numel() for p in base.parameters())
    model = PeftModel.from_pretrained(base, ADAPTER_DIR)
    n_peft = sum(p.numel() for p in model.parameters())
    x = tokenizer("患者咳嗽两周", return_tensors="pt")
    with torch.no_grad():
        logits_before = model(**x).logits
    merged = model.merge_and_unload()
    n_merged = sum(p.numel() for p in merged.parameters())
    with torch.no_grad():
        logits_after = merged(**x).logits
    q = merged.model.layers[0].self_attn.q_proj
    print(f"  参数量：基座 {n_base:,} → 挂 adapter {n_peft:,} → 合并后 {n_merged:,}（= 基座）")
    print(f"  合并后 q_proj 的类型：{type(q).__name__}，是普通 nn.Linear？ {type(q) is nn.Linear}")
    print(f"  合并前后 logits 最大差：{(logits_before - logits_after).abs().max().item():.2e}")
    shutil.rmtree(MERGED_DIR, ignore_errors=True)
    merged.save_pretrained(MERGED_DIR)
    tokenizer.save_pretrained(MERGED_DIR)        # 课件漏了这一步
    print(f"  已存到 {MERGED_DIR.relative_to(HERE.parent)}：{[f.name for f in sorted(MERGED_DIR.iterdir())]}")
    print()
    return merged, tokenizer


def demo_inference_template(model, tokenizer):
    print("=" * 64)
    print("demo 2：推理 prompt 两种拼法 —— 课件的 Alpaca 风格 vs 和训练一致的 chat template")
    print("=" * 64)
    prompt_style = """以下是描述任务的说明，并附有提供进一步背景的输入。
请写一个恰当的回应，完成该任务。
在回答之前，请仔细思考问题，并创建一个逐步的思维链，以确保逻辑清晰且准确。

### 任务描述:
{}

### 问题:
{}

### 回答:
<think>{}"""
    wrong = prompt_style.format(SYSTEM, QUESTION, "")
    right = tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": QUESTION}],
        tokenize=False, add_generation_prompt=True,
    )
    print("  [课件 prompt_style，训练时从没见过这种格式]")
    print("  " + wrong[:60].replace("\n", "\\n") + " …")
    print("  [apply_chat_template(add_generation_prompt=True)，和 4b 训练文本同一模板]")
    print("  " + right.replace("\n", "\\n"))
    inputs = tokenizer(right, return_tensors="pt", add_special_tokens=False)
    print(f"  输入 token 数 {inputs['input_ids'].shape[1]}，generate 10 个 token（迷你随机模型，内容是乱码，只看流程）：")
    print("  ", end="")
    model.generate(**inputs, streamer=TextStreamer(tokenizer, skip_prompt=True), max_new_tokens=10, do_sample=False)
    print()


if __name__ == "__main__":
    merged, tok = demo_merge()
    demo_inference_template(merged, tok)
