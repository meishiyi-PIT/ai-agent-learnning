"""
模块六 · 《1.大模型LoRA微调》第四章 4.3（中）：PEFT 三步 + TrainingArguments + collator 对比 + Trainer 真跑
==============================================================================================================

本机没有显卡，7B 跑不了。这里用 DeepSeek-R1-Distill-Qwen-1.5B 的 config.json 改小（隐藏维 64、2 层）拼一个随机初始化的
迷你 Qwen2 模型（约 1 千万参数，主要是词表 151936×64 的嵌入），tokenizer 用真的。流程、API、形状和课件完全一样，只是学不出东西。

【PEFT 三步（对应课件 4.3 中段）】
    ① LoraConfig：
        r=8                  秩（第 3 站）
        lora_alpha=16        缩放分子，scaling = α/r = 2
        target_modules=[...] 给哪些 nn.Linear 挂旁路。PEFT 按"模块名后缀"匹配：'self_attn.q_proj' 能匹配到 model.layers.0.self_attn.q_proj 等所有层
        lora_dropout=0.05    旁路输入上的 dropout（只作用于 A x 那条路，原路不动）
        bias='none'          不训 bias（第 3 站 3.5：bias 默认别碰）
        task_type=CAUSAL_LM  告诉 PEFT 这是自回归语言模型（决定包装成哪种 PeftModel）
    ② model = get_peft_model(model, config)：
        把 target_modules 里的每个 nn.Linear 换成 peft 的 lora.Linear（内部：原 Linear 冻结 + lora_A + lora_B），其余参数全部 requires_grad=False。
        demo 1 打印替换后的 q_proj，能看到 lora_A: Linear(64→8)、lora_B: Linear(8→64)，lora_B 权重全 0（第 3 站 3.3）。
    ③ Trainer(model, args, data_collator, train_dataset).train()

【TrainingArguments 课件用到的参数（demo 3）】
    output_dir / overwrite_output_dir        checkpoint 和日志存哪
    num_train_epochs=20                      课件 4.4 自己说"第 3 轮以后多半是过拟合"，20 轮自相矛盾（勘误⑤）；这里用 max_steps 跑 4 步意思一下
    per_device_train_batch_size=6            每张卡每步喂几条
    gradient_accumulation_steps=16           累积 16 个小批的梯度再更新一次 = 等效 batch 96，显存只按 6 算
    gradient_checkpointing=True              不存所有层的激活值，反向时重算 → 省显存换时间（第 1 站四笔账的④）；配合 PEFT 要先 model.enable_input_require_grads()
    save_strategy="epoch" / save_steps=10    有 save_strategy="epoch" 时 save_steps 不生效（勘误⑤）；save_total_limit=5 只留最近 5 个 checkpoint
    prediction_loss_only=True                评估时只算 loss；但课件没设 eval_strategy，训练中根本不会评估（勘误⑤）
    report_to="tensorboard" / logging_dir    训练曲线上报；这里改 "none"
    label_names=["labels"]                   告诉 Trainer 哪个字段是标签

【collator 对比（demo 2）—— 课件最隐蔽的坑】
    DataCollatorForLanguageModeling(mlm=False)：把 batch 拼起来后 labels = input_ids.clone()，再把 pad 位置设 -100（transformers 4.51.3 data_collator.py:1028-1031）。
        后果 1：你在 preprocess 里做的 prompt 屏蔽被整个覆盖 —— 训的是"整段对话"包括 system prompt 和问题；
        后果 2：这套 tokenizer pad == eos，句末 EOS 也被当 pad 屏蔽 → 模型学不会停（4a 事实 1）。
    DataCollatorForSeq2Seq(label_pad_token_id=-100)：按 batch 内最长动态填充 input_ids / attention_mask，labels 用 -100 填，不覆盖。SFT 该用它。
    另外训练时把 tokenizer.padding_side 改成 "right"：这套 tokenizer 默认左填充（是为推理 generate 准备的），训练时右填充更常规。

运行（在 meishiyi/09_HuggingFace 目录）：
    PYTHONUTF8=1 uv run python lora/s4c_peft_trainer.py
"""

import shutil
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    DataCollatorForSeq2Seq,
    Qwen2Config,
    Qwen2ForCausalLM,
    Trainer,
    TrainingArguments,
)

from s4b_preprocess import SAMPLES, preprocess_courseware, preprocess_fixed

HERE = Path(__file__).resolve().parent
TOK_DIR = HERE.parent / "models" / "deepseek-r1-distill-qwen-tokenizer"
OUT = HERE / "out"
BASE_DIR = OUT / "base"
ADAPTER_DIR = OUT / "adapter"

tokenizer = AutoTokenizer.from_pretrained(TOK_DIR)
tokenizer.padding_side = "right"


def build_tiny_model() -> Qwen2ForCausalLM:
    config = Qwen2Config.from_pretrained(TOK_DIR)       # 1.5B 的真实配置
    config.hidden_size = 64
    config.intermediate_size = 128
    config.num_hidden_layers = 2
    config.num_attention_heads = 4
    config.num_key_value_heads = 2
    config.tie_word_embeddings = True
    config.use_cache = False
    torch.manual_seed(0)
    return Qwen2ForCausalLM(config)


def demo_peft_three_steps(model):
    print("=" * 64)
    print("demo 1：PEFT 三步之 ① LoraConfig ② get_peft_model")
    print("=" * 64)
    names = [n for n, _ in model.named_modules() if n.startswith("model.layers.0.") and n.endswith("proj")]
    print("  第 0 层里能挂 LoRA 的 Linear：")
    for n in names:
        print(f"    {n}")
    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj", "self_attn.o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    n_base = sum(p.numel() for p in model.parameters())
    model = get_peft_model(model, lora_config)
    print("  get_peft_model 之后第 0 层的 q_proj 变成了：")
    print("    " + repr(model.base_model.model.model.layers[0].self_attn.q_proj).replace("\n", "\n    "))
    q = model.base_model.model.model.layers[0].self_attn.q_proj
    print(f"  lora_A 权重形状 {tuple(q.lora_A['default'].weight.shape)}，lora_B 权重形状 {tuple(q.lora_B['default'].weight.shape)}，"
          f"lora_B 全 0？ {bool((q.lora_B['default'].weight == 0).all())}，scaling = {q.scaling['default']}")
    # 课件的手工计数循环
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"  课件计数循环：可训练 {trainable:,} / 总 {total:,} = {100 * trainable / total:.2f}%（原模型 {n_base:,}，多出来的全是 A、B）")
    print("  PEFT 自带的一行：", end="")
    model.print_trainable_parameters()
    print()
    return model


def demo_collators():
    print("=" * 64)
    print("demo 2：两种 collator 对 labels 做了什么")
    print("=" * 64)
    course = preprocess_courseware(SAMPLES, max_length=256)
    feats = [{k: course[k][i] for k in course} for i in range(2)]
    before = sum(1 for t in feats[0]["labels"] if t != -100)
    batch = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)(feats)
    after = int((batch["labels"][0] != -100).sum())
    same = bool(torch.equal(batch["labels"][0][batch["labels"][0] != -100], batch["input_ids"][0][batch["labels"][0] != -100]))
    print(f"  [LanguageModeling(mlm=False)] 喂课件版特征：进去时可训 label {before} 个 → 出来 {after} 个（= 全部真 token 减去 EOS）")
    print(f"      非 -100 的 labels 和 input_ids 逐个相等？ {same}   ← labels 被 input_ids.clone() 覆盖，prompt 屏蔽没了，system+问题全在训")
    print(f"      序列末尾 token id = {int(batch['input_ids'][0][-1])}（EOS id {tokenizer.eos_token_id}），它的 label = {int(batch['labels'][0][-1])}   ← EOS 因为 == pad 被屏蔽成 -100")
    fixed = preprocess_fixed(SAMPLES)
    feats = [{k: fixed[k][i] for k in fixed} for i in range(2)]
    batch = DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100)(feats)
    lens = [len(f["input_ids"]) for f in feats]
    print(f"  [Seq2Seq] 喂修正版特征：两条原长 {lens} → 填充到 {tuple(batch['input_ids'].shape)}")
    for i in range(2):
        n_tr = int((batch["labels"][i] != -100).sum())
        n_ans = sum(1 for t in feats[i]["labels"] if t != -100)
        print(f"      样本 {i}：可训 label {n_tr} 个（= 回答 token 数 {n_ans}），attention_mask 之和 {int(batch['attention_mask'][i].sum())}（= 原长 {lens[i]}）")
    print()
    return feats


def demo_trainer(model, feats):
    print("=" * 64)
    print("demo 3：TrainingArguments + Trainer 在 CPU 上真跑 4 步")
    print("=" * 64)
    ds = Dataset.from_list(feats)
    model.config.use_cache = False
    model.enable_input_require_grads()          # 开梯度检查点时 PEFT 要求这一步
    args = TrainingArguments(
        output_dir=str(OUT / "ckpt"),
        overwrite_output_dir=True,
        label_names=["labels"],
        per_device_train_batch_size=2,
        gradient_accumulation_steps=2,          # 每 2 个小批更新一次
        gradient_checkpointing=True,
        max_steps=4,                            # 用步数代替 num_train_epochs，意思一下
        learning_rate=2e-4,
        logging_steps=1,
        save_strategy="no",
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=args,
        data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, padding=True, label_pad_token_id=-100),
        train_dataset=ds,
    )
    trainer.train()
    losses = [round(h["loss"], 3) for h in trainer.state.log_history if "loss" in h]
    print(f"  4 步的 loss：{losses}（随机初始化的迷你模型，loss ≈ ln(词表 151936) ≈ 11.9 是正常起点）")
    shutil.rmtree(ADAPTER_DIR, ignore_errors=True)
    model.save_pretrained(ADAPTER_DIR)          # 只存 A、B
    print("  save_pretrained 只存了 adapter：")
    for f in sorted(ADAPTER_DIR.iterdir()):
        print(f"    {f.name:28s} {f.stat().st_size / 1024:.0f} KB")
    print()


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    (OUT / ".gitignore").write_text("*\n")
    base = build_tiny_model()
    shutil.rmtree(BASE_DIR, ignore_errors=True)
    base.save_pretrained(BASE_DIR)              # 4d 合并时要用同一份基座
    tokenizer.save_pretrained(BASE_DIR)
    peft_model = demo_peft_three_steps(base)
    feats = demo_collators()
    demo_trainer(peft_model, feats)
