---
name: zhibaotong-stage1
description: "智保通只是每日滚动课程里\"当前的一个项目\"（非终点）；模块四保险Agent实战，第一阶段代码在 harness_zbt，Harness理论+对照地图已备"
metadata: 
  node_type: memory
  type: project
  originSessionId: 84fc497e-d743-4269-9233-53c7b90bf3a1
  modified: 2026-09-04T08:40:04.920Z
---

> ⚠️ **定位（别再框错）**：智保通只是**当前正在学的一个项目**，不是重心、更不是终点。用户的课程**几乎每天更新**、实战项目一个接一个到货（见 [[study-plan-sep12]]）；**不要把"把这个项目所有文件从头读到尾/打勾读完"当成目标**。真正的重心是一套**可复用、每天都能套用的"自己动手 + 高效"学习打法**——智保通只是今天用来练这套打法的素材。今天学它就用这套打法带，明天来新项目同样这套打法。

"智保通"= 模块四《Harness 架构与保险 Agent 项目实战》里第一个实战项目的产品名，和计划里说的"保险 Agent"是同一个东西。三阶段包含式演进：①智能投保闭环 ②知识RAG+长期记忆+多模态 ③保单生命周期工作流+人工审批+退款Worker+MCP。

第一阶段代码：`harness_zbt/backend/src/zbt/`（Python 3.12 + FastAPI + LangChain `create_agent` + DeepSeek + MySQL/Redis；一个 Agent Kernel 承载"客户顾问/运营助手"两个人格）。课件：`AI大模型应用开发/模块四.../03-项目一.../01-智保通第一阶段....md`。

**代码按阶段切 git 分支**（别再误判"二三阶段没代码"）：`harness_zbt` 是 git 仓库，三分支对应三阶段、包含式演进——`phaseOne`(当前所在) / `origin/phaseTwo` / `origin/phaseThree`。二/三阶段要读代码就 checkout 对应分支。⚠️ 当前 `backend/.env`（用户密钥）和 `uv.lock` 有本地改动，切分支前先保住 `.env`。视频是 `.sz` 录播（模块四根目录）：`02上+03下`=第一阶段、`04`=第二阶段、`05`=第三阶段、`01`=Harness理论。

**周末目标（用户 2026-08-08 坚持）+ 省时打法**：这周末把智保通**三阶段全部学完**（理解型）。关键 = **不重学整个系统，只学分支增量**：phaseOne 吃透打底，二/三阶段用 `git diff phaseOne origin/phaseTwo`、`git diff origin/phaseTwo origin/phaseThree` 看新增模块，只问"新增了什么、怎么挂到同一个 Kernel 上"。实测后端核心增量——**二阶段**（67文件/+4948行）三块：Agentic RAG(`domains/knowledge/`+milvus+embedding/bge+reranker)、长期记忆(`domains/agent/memory.py`+milvus memory_index)、多模态材料识别(`domains/service_request/`+documents/parser+qwen/bailian vision_gateway)；**三阶段**（66文件/+6104行）四块：退保 LangGraph 编排(`domains/surrender/workflow|rules|refund`)、退款 Worker(`commands/run_refund_worker`+redis worker_lock/registry)、MCP(`mcp/partner_resources_server`+infra/mcp)、可观测性(`core/observability.py`)+langgraph_checkpoint。

**进度锚点（2026-09-04 更新）**：当前在 `phaseThree` 分支，**续保规划作业九个步骤已全部动笔（首稿完成、未跑通）**。已写：`domains/renewal/{models,service}.py`、`api/v1/renewal_advice.py`、`harness/assets/skills/renewal-planning/SKILL.md`（front matter 与注册工具名一致 ✅）、`tools.py` 三个新工具 + 注册项、`schemas.py` RenewalAdviceBlock、`registries.py` customer 人格挂载、知识 seed 文档。**未做：步骤 9 装配（main.py 无任何 renewal 字样，router/service 没挂）、步骤 6 校验5（事实性结论需直接证据）、service.py 知识引用还原 resolve_chunks**。2026-09-04 已交付首轮批改（分 A 语法/B Java习惯/C 架构级/D 未写/E 拼写五组），核心两条：①Block 必须放 `HarnessToolResult.blocks=` 不能放 `data=`（kernel.py:166 cards 只从 blocks 来，这是用户"不知道从哪拿结果"的根因）②引用校验要先并成 set 再判、不能在 executions 循环里逐个判。等用户按批改自行修复后复批。

（历史）phaseOne 全部完成。**phaseTwo 全部完成（S0-S4，G1-G6 验收✅）**，全部 Q&A/修正已落笔记「phaseTwo 读码 Q&A」区（含 S2-S4 详录 + G2 关卡对照表）。用户吸收要点：①3把工具挂原Kernel+材料识别旁路；②引用闭环=声称∩真实执行；③闸门下沉/深层不信上层（发布过滤在服务端、语义层再验、repository 兜底 index）；④身份永远从 context 焊死不让模型传（quote/memory/analytics 三次重演）；⑤软硬分工判定标准=代码判得了的硬拦、只有对话里才知道的（授权语义）交 prompt+硬约束封顶伤害；⑥人工环节长成 API 边界形状（识别/生效拆两接口）；⑦分析库=白名单点菜+物理爆炸半径隔离。收官考暴露的坑（复习时重点）：把授权门当成硬约束、把 owner_id 当成"会话生成的"、"SQL 写死"表述不准。**待办：①看视频04验证补漏；②phaseThree 读码**（`git diff origin/phaseTwo origin/phaseThree`，四块：退保 LangGraph 工作流 / 退款 Worker / MCP / 可观测性；切分支前照旧保住 backend/.env）；**③续保规划作业**（第三阶段课件04的动手作业，在 phaseThree 分支上做；开工指南+22条Python语法清单已备好在 `C:\workspace\学习笔记\续保规划作业-开工指南与Python语法清单.md`，含抄/写分工、file:line 预习地图、两道预测题——教练模式，等用户答预测题/交批改）。学法照旧：预测题→自读先答→代码校对+架构why→填三问。

**Why**：会话经常断，重连时靠这条 + 对照地图快速接上，不用重新扫全仓。
**How to apply**：新会话先读 [[study-plan-sep12]] 核实进度→打开对照地图当读码清单→讲解按 [[learning-requirements]] 写进 harness_zbt 代码注释（不新开 md），并按 [[tutor-role]] 出挖空/预测题、卡壳20分钟兜底。
