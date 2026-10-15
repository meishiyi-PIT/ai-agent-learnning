---
name: teach-directly-no-line-refs
description: "2026-09-29 学课件 5《大模型推理部署》时用户定的新规矩：不再提课件行号（用户看的是渲染后的 md，不是原始行）；用户不再自己读课件，Claude 通读全篇后直接按小节讲；本篇改为边学边跑（本地 CPU 跑 transformers 小实验），并要求尽量快"
metadata:
  node_type: memory
  type: feedback
  originSessionId: c1e4ccc3-1298-408d-9268-4e64ff3f4686
  modified: 2026-09-29T09:15:03.803Z
---

2026-09-29 开学模块六《5.大模型推理部署》时，用户三条纠正：

1. **"你不要再说课件多少行了"**：用户在编辑器里看的是 Markdown 渲染后的阅读视图，行号对他没有意义。定位只能用**小节标题 + 编号站点**（"第二部分第 3 节 Prefill"），不能用"第 41~64 行"。
2. **"你需要读所有的课件，并且直接教我，我不会再去看课件了"**：从这篇起，"👉 你做：读课件第 X~Y 行"这一步取消。Claude 备课时通读全篇，然后按小节顺序把内容**完整讲出来**（格式仍按 [[interview-goal]] 第二次纠正的骨架：📍位置 → 是什么 → 为什么/类比 → 跟一个具体样本走 → 架构层为什么 → 🔖 要记），用户只回"下一节"或追问。
3. **"直接边学边跑吧，尽量快点学完"**：本篇的代码实验不再攒到最后（覆盖 [[quiz-frequency-feedback]] 第五次补充的"攒到整篇讲完"），讲到哪节有代码就当场跑：Claude 本机跑（`meishiyi/09_HuggingFace/.venv`，CPU 版 torch + transformers 4.51.3，模型放 `meishiyi/09_HuggingFace/models/Qwen3-0.6B`），把输出贴进讲解；vLLM 相关的（`vllm serve`、调度参数）本机跑不了，留到租卡日。节奏上两个短小节可并成一步。

4. **课件里的图默认也要读**（2026-09-29 课件 6 时用户说"md 文档有图，以后图的部分你也默认读取"）：md 里的图是语雀 CDN 链接（cdn.nlark.com），OCR 注释常为空。备课时用 Bash curl 下载到 Temp 的纯 ASCII 文件名（如 arch_img.png），再用 Read 看图，讲到那一节时把图的内容一起讲。

**Why:** 行号是 Claude 视角的坐标，用户视角看不到；"用户自读 + Claude 提问"在用户不熟的领域效率低，用户明确要 Claude 直接讲；边学边跑是因为本地 CPU 就能跑这篇大部分 demo，没必要攒。

**How to apply:** 讲课件类内容时定位一律用小节标题；每步把该小节的知识点讲全（用户不会去看原文），但仍一屏一步、不铺开；有代码的小节先跑后讲。与 [[pacing-small-chunks]]、[[teaching-map-before-code]]、[[interview-goal]] 配合。
