---
name: module6-lesson6-7-plan
description: 2026-09-29 模块六课件 6、7 的学习顺序：课件 6 下半篇 → 课件 7 文件夹四篇（RMSNorm、GQA、RoPE、MoE）→ 回头重讲课件 6 的 LLaMA 结构图；课件 5 笔记里还有未记完的部分
metadata:
  node_type: memory
  type: project
  originSessionId: ff981577-db45-4261-b7f0-7b0e82dd7cef
  modified: 2026-10-02T11:38:12.360Z
---

2026-09-29 开学《6.大模型架构与训练全流程》。上半篇（架构之争）已讲完，笔记已追加；用户对 3.2 末尾"Transformer vs LLaMA"图说"还不太理解，先往后学，学完再重新理解"。

用户随后提醒 `课件/7.大模型模块详解/` 是一个**文件夹**（不是单个 md），含四篇 md（各有同名 pdf）：RMSNorm、从MHA到MQA与GQA、RoPE旋转位置编码、图解MOE结构——正好是 LLaMA 图里的零件。

**顺序：** 课件 6 下半篇（第二节起：Token/6400 词表 → 预训练 → 后训练 → 微调 → 推理 → 七~十节）→ 课件 7 按 RMSNorm → GQA → RoPE → MoE → 回到 LLaMA 图重讲（一层的顺序 + 四个替换各配一个动机）。

**MiniMind 用法（用户问"我们能用它来做吗"后定）：** 官方 README（raw.githubusercontent.com 可 curl，github.com 网页 WebFetch 被拦）确认 minimind-3 = 64M、d_model 768、8 层、8 Q 头 / 4 KV 头、RoPE、词表 6400；3090 上 pretrain_mini + sft_mini 各 1 轮约 2.31h / 3 元。计划：课件 7 学完后，用 MiniMind 的模型代码对照重讲 LLaMA 图（本机 CPU 可下权重聊天、跑 LoRA）；从零预训练 + SFT 放租卡日。

**MiniMind 训练命令留到最后**（用户讲预训练时说"训练留在最后，先继续下一节"）：课件每节的 🔧 MiniMind 实战命令讲课时只一句带过（"命令留到最后"），不逐条解释；整篇讲完后统一过一遍/动手跑。本机概念 demo（Qwen3-0.6B / -Base 对比）照旧当场跑。

**进度（2026-09-30）：** 课件 6 全篇讲完；课件 7 四篇（RMSNorm、GQA、RoPE、MoE）全部讲完并写入笔记（demo s7–s15 在 meishiyi/09_HuggingFace/arch_train）；2026-10-02 已用 MiniMind 模型代码重讲 LLaMA 图（含 SwiGLU，demo s16_llama_walk.py，minimind_model.py 为官方源码拷贝），笔记已写。剩下：MiniMind 训练命令统一过 / 动手（本机 CPU：minimind-3 聊天 + LoRA；租卡：预训练 + SFT），然后进入模块六后续课件。

**Why:** 用户卡在 LLaMA 图是因为零件还没学；课件 7 就是零件拆解。
**How to apply:** 新窗口接课件 6/7 时先读《大模型微调.md》末尾"架构与训练全流程"章看停在哪，按上面顺序走；课件 7 学完务必回头重讲 LLaMA 图。笔记规则见 [[module6-notes-doc]]，图片读取见 [[teach-directly-no-line-refs]]。
