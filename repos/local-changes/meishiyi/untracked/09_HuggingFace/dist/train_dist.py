"""
模块六 · 《3.大模型分布式训练实战指南》租卡实验：单卡 → DDP → ZeRO-2 → ZeRO-3 → ZeRO-3+Offload
=========================================================================================

课件 5.3 只给了 ds_config、没给训练脚本（缺了 5.4），这个文件就是那份缺的脚本。
一份脚本跑完所有对比，只换启动命令和 --run，其余全部一样，测出来的数字才可比。

【租 2 张卡（Linux）后按顺序跑的四组】
    ① 单卡全参基线          CUDA_VISIBLE_DEVICES=0 python train_dist.py --run single
    ② 两卡 DDP              torchrun --nproc_per_node=2 train_dist.py --run ddp
    ③ 两卡 ZeRO-2           torchrun --nproc_per_node=2 train_dist.py --run zero2
    ④ 两卡 ZeRO-3+Offload   torchrun --nproc_per_node=2 train_dist.py --run zero3_offload
    可选 ⑤ ZeRO-3 不 offload：--run zero3        ⑥ 任一组加 --lora：亲眼看 LoRA 下 ZeRO 几乎不省
    每组跑完自动往 results.csv 追加一行：run, rank, 峰值显存 GB, 预留显存 GB, 每秒步数, 总秒数
    另开一个终端 nvidia-smi -l 2，对照看每张卡的显存。

【为什么默认"全参微调 0.5B"而不是课件的"LoRA 7B"】
    看 ZeRO 效果要有可观的优化器状态：0.5B 全参 ≈ 0.5B × 16 字节 = 8 GB/卡（DDP），ZeRO-2 两卡 ≈ 4.5 GB，ZeRO-3 ≈ 4 GB。
    LoRA 可训练参数只有几百万，优化器状态几十 MB，ZeRO-1/2 切它没意义（⑥ 亲眼验证）。
    7B 只在最后可选：--model Qwen/Qwen2.5-7B-Instruct --lora --dtype bf16 --run zero3（两张 24GB 卡也放得下）。

【一个课件没说的顺序坑】
    ZeRO-3 时必须"先建 TrainingArguments，再 from_pretrained 加载模型"（HF 官方文档明确要求）：
    TrainingArguments 里的 deepspeed= 会先注册配置，随后 from_pretrained 才知道要把参数切着加载，反过来写 ZeRO-3 就白开了。
    所以下面 main() 的顺序是：参数 → TrainingArguments → 模型 → 数据 → Trainer。

【本机 CPU 预跑（不租卡，只验证脚本通）】
    cd C:\\workspace\\meishiyi\\09_HuggingFace
    PYTHONUTF8=1 uv run python dist/train_dist.py --run single --tiny --steps 3
    --tiny = 用 lora/s4c 那套缩小版 Qwen2（随机初始化）跑，数字没有意义，只看能不能跑完并写出 results.csv。

【AutoDL 上的准备（租 2 × RTX 4090 的实例，不是 1 张）】
    nvidia-smi                                                  # 确认 2 张卡
    df -h /root/autodl-tmp                                      # 数据盘余量（0.5B 约 1 GB，7B 约 15 GB）
    mkdir -p /root/autodl-tmp/code/03                           # 分布式课件的代码目录（02 是量化那篇，别混）
    # 把本机 dist/ 里 5 个文件上传到 /root/autodl-tmp/code/03/
    pip install "transformers==4.51.3" peft datasets accelerate deepspeed ninja modelscope
    （钉 4.51.3 = 本机验证过的版本；5.x 里 torch_dtype 改名 dtype、默认精度改 auto，能跑但会多出警告和未验证的差异）
    modelscope download --model Qwen/Qwen2.5-0.5B-Instruct --local_dir /root/autodl-tmp/code/model_qwen05b
    export MODEL_DIR=/root/autodl-tmp/code/model_qwen05b         # 脚本 --model 的默认值读这个环境变量（每个模型一个文件夹，不复用 code/model）
    cd /root/autodl-tmp/code/03 && bash run_all.sh              # 或者按文件顶部四条命令一条条敲
"""

import argparse
import csv
import os
from pathlib import Path

import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Qwen2Config,
    Qwen2ForCausalLM,
    Trainer,
    TrainingArguments,
    default_data_collator,
)

HERE = Path(__file__).resolve().parent

# --run 的值 → 用哪份 ds_config；None = 不用 DeepSpeed（single 是单卡，ddp 靠 torchrun 起 2 个进程）
DS_CONFIG = {
    "single": None,
    "ddp": None,
    "zero2": HERE / "ds_zero2.json",
    "zero3": HERE / "ds_zero3.json",
    "zero3_offload": HERE / "ds_zero3_offload.json",
}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--run", choices=list(DS_CONFIG), required=True)
    # 默认值先看环境变量 MODEL_DIR（AutoDL 上指向 /root/autodl-tmp/code/model_qwen05b），没设就用 Hub id 走 hf-mirror 下载
    p.add_argument("--model", default=os.environ.get("MODEL_DIR", "Qwen/Qwen2.5-0.5B-Instruct"))
    p.add_argument("--dtype", choices=["fp32", "bf16"], default="fp32")   # 全参用 fp32 加载（16 字节/参数那笔账）；7B LoRA 用 bf16
    p.add_argument("--steps", type=int, default=60)      # 只跑 60 步：够看显存和速度，不为学出东西
    p.add_argument("--bsz", type=int, default=4)         # 每张卡每步喂几条
    p.add_argument("--seqlen", type=int, default=512)    # 每条固定 512 个 token，四组显存才可比
    p.add_argument("--lora", action="store_true")        # 加了就挂 LoRA，只训 A/B
    p.add_argument("--tiny", action="store_true")        # 本机 CPU 预跑用
    return p.parse_args()


def build_tokenizer_and_model(args):
    """--tiny 用本地 tokenizer + 缩小版随机 Qwen2；否则从 Hub 下真模型。"""
    if args.tiny:
        tok_dir = HERE.parent / "models" / "deepseek-r1-distill-qwen-tokenizer"
        tokenizer = AutoTokenizer.from_pretrained(tok_dir)
        config = Qwen2Config.from_pretrained(tok_dir)
        config.hidden_size, config.intermediate_size, config.num_hidden_layers = 64, 128, 2
        config.num_attention_heads, config.num_key_value_heads = 4, 2
        config.tie_word_embeddings, config.use_cache = True, False
        torch.manual_seed(0)
        model = Qwen2ForCausalLM(config)
    else:
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        dtype = torch.float32 if args.dtype == "fp32" else torch.bfloat16
        model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype)
        model.config.use_cache = False
    tokenizer.padding_side = "right"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer, model


def build_dataset(tokenizer, n: int, seqlen: int) -> Dataset:
    """合成数据：内容不重要，重要的是每条都定长 seqlen，四组的显存和速度才可比。"""
    filler = "一二三四五六七八九十" * 60                      # 600 个汉字，够撑满 512 token
    texts = [f"问题{i}：请把数字 {i} 用中文读出来。回答：{filler}" for i in range(n)]
    enc = tokenizer(texts, max_length=seqlen, truncation=True, padding="max_length")
    # labels = input_ids，pad 位置设 -100（不算 loss）；zip 把两个列表按位置配对
    enc["labels"] = [
        [tok if m == 1 else -100 for tok, m in zip(ids, mask)]
        for ids, mask in zip(enc["input_ids"], enc["attention_mask"])
    ]
    return Dataset.from_dict(enc)


def main():
    args = parse_args()
    use_cuda = torch.cuda.is_available()
    rank = int(os.environ.get("RANK", 0))           # torchrun 给每个进程发的编号；单进程时没有这个变量 → 0

    # ---------- 1. TrainingArguments 先建（ZeRO-3 的顺序坑，见文件顶部） ----------
    ds_path = DS_CONFIG[args.run]
    training_args = TrainingArguments(
        output_dir=str(HERE / "out" / args.run),
        max_steps=args.steps,
        per_device_train_batch_size=args.bsz,
        gradient_accumulation_steps=1,
        learning_rate=1e-5,
        bf16=use_cuda,                               # 有卡才开 bf16 混合精度；CPU 预跑用 fp32
        logging_steps=10,
        save_strategy="no",                          # 不存 checkpoint，只测显存和速度
        report_to="none",
        dataloader_num_workers=0,
        deepspeed=str(ds_path) if ds_path else None, # 课件 5.5 说的"关键就这一行"
        ddp_find_unused_parameters=False,
        seed=0,
    )

    # ---------- 2. 模型（ZeRO-3 时 from_pretrained 会自动按分片方式加载） ----------
    tokenizer, model = build_tokenizer_and_model(args)
    if args.lora:
        from peft import LoraConfig, TaskType, get_peft_model
        lora_cfg = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, bias="none",
                              target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                              task_type=TaskType.CAUSAL_LM)
        model = get_peft_model(model, lora_cfg)
        if rank == 0:
            model.print_trainable_parameters()

    # ---------- 3. 数据 ----------
    train_ds = build_dataset(tokenizer, n=2000, seqlen=args.seqlen)

    # ---------- 4. Trainer ----------
    trainer = Trainer(model=model, args=training_args, train_dataset=train_ds,
                      data_collator=default_data_collator)   # 数据已定长，用默认 collator 直接堆成张量
    if use_cuda:
        torch.cuda.reset_peak_memory_stats()
    result = trainer.train()

    # ---------- 5. 记账：每个进程（每张卡）各写一行 ----------
    m = result.metrics
    peak = torch.cuda.max_memory_allocated() / 1e9 if use_cuda else 0.0      # 真正被张量占用的峰值
    reserved = torch.cuda.max_memory_reserved() / 1e9 if use_cuda else 0.0   # PyTorch 向显卡要走的峰值，更接近 nvidia-smi 的数
    row = [args.run + ("+lora" if args.lora else ""), rank,
           f"{peak:.2f}", f"{reserved:.2f}", f"{m['train_steps_per_second']:.3f}", f"{m['train_runtime']:.1f}"]
    csv_path = HERE / "results.csv"
    new_file = not csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["run", "rank", "peak_alloc_GB", "peak_reserved_GB", "steps_per_s", "runtime_s"])
        w.writerow(row)
    print(f"[rank {rank}] {row}")


if __name__ == "__main__":
    main()
