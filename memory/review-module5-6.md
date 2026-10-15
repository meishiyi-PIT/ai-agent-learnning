---
name: review-module5-6
description: 2026-10-02 起的模块五+六复习项目：六个重点、三份交付物位置、GPU 实跑状态、复习顺序与四步法
metadata:
  node_type: memory
  type: project
  originSessionId: ef79bfe5-3edc-43f1-9f33-9474906e84f3
  modified: 2026-10-02T15:08:51.603Z
---

2026-10-02 用户进入"大模型底层原理复习"阶段，重点六项：Transformer、RoPE(+RMSNorm/Pre-Norm)、GQA/KV Cache、MoE、LoRA、QLoRA/量化、vLLM 部署（vLLM + KV Cache + PagedAttention）。目标三件：记公式结论、熟完整代码流程、GPU 亲手跑。

交付物（都在 `C:\workspace\学习笔记\大模型底层原理复习\`，用户 10-02 自己移进这个子目录）：
- `复习-模块五六-总纲.md`：复习目标矩阵（六重点 × 公式/代码/GPU 勾选）、三条融合主线、GPU 执行单、进度锚点——**每次复习会话先读它的"进度锚点"**
- `复习-模块五六-知识地图.md` + `.mm`：思维导图，用户用 ProcessOn 导入 .mm；改 md 后跑 `python tools/build_review_map.py` 重新生成
- `知识点全量清单-模块五/六上/六下(自动提取).md`：课件逐条大纲，查细节用

GPU 状态：quant_demo bf16/int8/nf4 已在 4090 跑过（9-28）；LoRA 训练、QLoRA、merge/infer、评估、vLLM、分布式都未跑。vLLM 脚本尚未写，留到部署专题时补。

**How to apply:** 复习顺序 Transformer → RoPE/RMSNorm → GQA/KV Cache → MoE → LoRA → QLoRA/量化 → vLLM → 租卡日。每个重点四步：公式卡(≤5条) → 代码走读(按小节不提行号) → 本机 CPU 跑 demo → 用户复述。讲解写进代码 docstring，总纲只更新勾选和锚点。相关：[[zhibaotong-stage1]] [[module6-notes-doc]] [[autodl-model-per-folder]] [[interview-goal]]
