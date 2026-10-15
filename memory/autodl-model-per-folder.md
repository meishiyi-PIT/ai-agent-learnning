---
name: autodl-model-per-folder
description: AutoDL 上下载模型时每个模型单独一个文件夹（--local_dir 用新名字 + 运行时 MODEL_DIR 指过去），绝不复用已有的 model 目录；附当前 AutoDL 目录布局
metadata:
  node_type: memory
  type: feedback
  originSessionId: a137d506-ffb7-46b1-90b7-511eb33de4e8
  modified: 2026-09-28T10:48:09.264Z
---

2026-09-28 在 AutoDL（RTX 4090）上跑模块六代码时，用户问"每次下载新模型，model 是不是会被覆盖"，我解释同一个 `--local_dir` 会让同名文件（config.json、tokenizer.json）被覆盖、不同名的 safetensors 混在一起成坏模型后，用户说"下次记住帮我每个模型一个文件夹"。

**Why:** 复用同一目录会静默拼出一个坏模型，加载报错或输出乱码，排查成本高；用户 Python/Linux 基础弱，不会自己想到换目录。

**How to apply:**
- 给任何模型下载命令（modelscope download / snapshot_download / hf download）时，`--local_dir` 一律写新文件夹，命名 `/root/autodl-tmp/code/model_<简称>`（如 `model_qwen7b`），并配套给出运行时的 `MODEL_DIR=/root/autodl-tmp/code/model_<简称> python xxx.py`。
- 下载前附一句 `df -h /root/autodl-tmp` 看数据盘剩余（7B 约 15 GB）。
- 当前布局（2026-09-28）：`/root/autodl-tmp/code/model` = DeepSeek-R1-Distill-Qwen-7B（`C:\workspace\code\lora\` 下各脚本的 MODEL_DIR 默认值，保持不动）；用户把 quant_demo.py、lora_train_fixed.py 等六个文件放在 `/root/autodl-tmp/code/02`，脚本输出按脚本所在目录落地；第三篇分布式课件的代码计划放 `03`。
- 同理，不同实验的脚本也各放各的子目录，避免 fined/、merge/ 互相覆盖。
