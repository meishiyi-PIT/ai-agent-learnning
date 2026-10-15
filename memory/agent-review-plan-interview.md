---
name: agent-review-plan-interview
description: 2026-10-07 起的 Agent 面试向复习：以智服中台五课为主干、课件知识按需倒着插、7 站主线防孤岛、四条学习方式规则；计划文件位置与锚点
metadata:
  node_type: memory
  type: project
  originSessionId: ff02f94c-a617-4b19-9b5c-e918f2f79d14
  modified: 2026-10-09T01:08:11.046Z
---

计划文件：`C:\workspace\学习笔记\Agent复习计划-面试向.md`（mermaid 流程图 + 7 站表 + 五课路线表 + 课件索引 + 待深挖清单 + 锚点）。笔记写 `学习笔记/智服中台.md`，地图填 `学习笔记/面试复习-00-主线地图.md`。

**主干 = 智服中台五课**（tag 00/01 → 02/03/04 → 05 → 06/07 → 08/09），课件知识不通读、读到某站需要时当场插一段。RAG 大块复习（模块二四篇 + 本机跑 03_RAG / 04_RAG_OPTIMIZE）插在第三课；LangGraph State/Edge 插第一课，Send/reducer/interrupt/Middleware 插第二课，记忆五范式/上下文工程插第四课，LangSmith 插第五课。收尾补智服中台没有的：Agentic RAG 多源路由、MCP/A2A/Skills、ReAct vs P&E、Harness 对照。简历定稿后做第二遍「简历项目映射 7 站」。

**7 站主线**（一条请求的生命线）：1 入口 / 2 编排 / 3 状态与记忆 / 4 知识获取 / 5 外部能力 / 6 控制与护栏 / 7 出口与观测。每课开头答「动哪几站、上一课哪里不够」，课末填地图。

**Why:** 用户 2026-10-07 明确：简历未定稿不按简历学；直接以智服中台为切入点；用户自述「要全懂原理才放心、浪费时间」，故定学习方式规则。模型底层（模块五/六）另有计划不碰。

**抓大放小（用户 2026-10-09 确认）**：用 Agent 应用开发眼光取舍，代码实现不花过多时间。计划 §3.5 分三档：🔴 精=runtime 图+tools、worker 租约、collaboration 并行、state_merge、branch_store、context 预算、streaming；🟡 懂为什么=售后审批链、提醒同事务、检索缓存、连接复用、用量；🟢 跳过=代理/事件循环、索引 EXPLAIN、迁移/备份/HAProxy/发布、计量调度、thread_bridge、前端、各课实验作业。读码停在最终版 09，只看入口签名+关键 5~10 行，必要时单文件 tag diff。

**How to apply:** 每次先读计划文件末尾锚点。四条规则由 Claude 执行：①三问即止（是什么/为什么要/怎么选，标准=不看笔记讲 2 分钟+接一次追问）；②每个点 30 分钟定时盒，超时记入计划 §7 待深挖清单，同一条三课反复出现才回头挖；③先用后懂（先切 tag 看 diff / 跑动作再讲原理，原理到"为什么这样设计"为止）；④没懂记录不当场解决。Claude 通读课件按小节讲，用户不自读。相关：[[zhifu-platform-course]]、[[interview-goal]]、[[resume-project]]、[[review-module5-6]]。
