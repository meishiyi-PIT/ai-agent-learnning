"""练习 3:情感分类微调全流程(文档 Part 1)—— 挖空版

流程(文档 1.2):
    CSV 数据 -> datasets 加载清洗 -> Tokenizer 分词 -> 动态 padding
    -> Trainer 训练 -> 评估 acc/F1 -> pipeline 推理

底座模型 hfl/rbt3:38M 参数,CPU 可训(约 10~20 分钟/5轮,先用 1 轮试跑)。

准备工作(只需一次):
    1. 下载数据集 CSV(约 2MB,curl 直连即可):
       curl -L -o ChnSentiCorp_htl_all.csv https://raw.githubusercontent.com/SophonPlus/ChineseNlpCorpus/master/datasets/ChnSentiCorp_htl_all/ChnSentiCorp_htl_all.csv
    2. 模型走 hf-mirror 下载(本机 NO_PROXY 已配好),脚本里已设置 HF_ENDPOINT。

运行:  uv run python -X utf8 03_sentiment_train.py
通过标准:验证集 acc > 0.85,且最后两条 pipeline 推理输出正确的好评/差评。
"""

import os

# 本机代理环境:HF 下载走镜像(必须在 import transformers 之前设置)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import numpy as np
import torch
import evaluate
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    DataCollatorWithPadding,
    TrainingArguments,
    Trainer,
    pipeline,
)

# ---------- 1. 加载与清洗数据 ----------
dataset = load_dataset("csv", data_files="ChnSentiCorp_htl_all.csv", split="train")

# 清洗:review 为空的行留着只会让训练报莫名其妙的错
dataset = dataset.filter(lambda x: x["review"] is not None)

# 9:1 切分训练/验证集;seed 固定保证可复现
splits = dataset.train_test_split(test_size=0.1, seed=42)

# ---------- 2. 分词 ----------
tokenizer = AutoTokenizer.from_pretrained("hfl/rbt3")


def tokenize_fn(examples):
    # max_length=128:酒店评论大多几十个字,足够覆盖;超长截断
    out = tokenizer(examples["review"], max_length=128, truncation=True)
    # 关键坑:Trainer 只认 "labels" 这个字段名来算损失,写错名字不报错但不训练
    out["labels"] = list(examples["label"])
    return out


tokenized = splits.map(
    tokenize_fn, batched=True, remove_columns=splits["train"].column_names
)

# ---------- 3. 模型 ----------
# num_labels=2 决定分类头输出维度;二分类恰好是默认值,但显式写出是好习惯
model = AutoModelForSequenceClassification.from_pretrained("hfl/rbt3", num_labels=2)

# ---------- 4. 评估指标 ----------
acc_metric = evaluate.load("accuracy")
f1_metric = evaluate.load("f1")


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    # logits 是每个类别的原始打分,argmax 取最大者的下标当预测类别
    preds = np.argmax(logits, axis=-1)
    acc = acc_metric.compute(predictions=preds, references=labels)
    f1 = f1_metric.compute(predictions=preds, references=labels)
    return {**acc, **f1}


# ---------- 5. 训练配置(文档 1.7 表格的最小可用版) ----------
train_args = TrainingArguments(
    output_dir="./checkpoints",
    per_device_train_batch_size=32,
    per_device_eval_batch_size=64,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    learning_rate=2e-5,          # BERT 系黄金学习率
    weight_decay=0.01,
    num_train_epochs=1,          # 试跑 1 轮;跑通后改 3~5 轮
    metric_for_best_model="f1",
    load_best_model_at_end=True,
    logging_steps=50,
)

collator = DataCollatorWithPadding(tokenizer=tokenizer)

trainer = Trainer(
    model=model,
    args=train_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
    processing_class=tokenizer,   # 旧写法 tokenizer=... 已弃用
    data_collator=collator,
    compute_metrics=compute_metrics,
)

trainer.train()
print(trainer.evaluate(tokenized["test"]))

# ---------- 6. 推理 ----------
model.eval()
# 把数字标签映射回文字,否则 pipeline 输出 LABEL_0 没人看得懂
model.config.id2label = {0: "差评", 1: "好评"}

pipe = pipeline("text-classification", model=model, tokenizer=tokenizer, device=-1)
print(pipe("这家麻辣烫绝了,汤底我都喝完了!"))      # 期望: 好评
print(pipe("等了俩小时,送到的时候汤都凝成冻了。"))  # 期望: 差评
