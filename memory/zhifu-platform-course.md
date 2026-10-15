---
name: zhifu-platform-course
description: "2026-09-29 开学的新课程\"智服中台\"（企业级客服中台 Agent 后端工程，5 次直播 + 6 篇文章 + 10 个代码阶段）：资料/代码位置、分支用法、学法约定、进度锚点"
metadata:
  node_type: memory
  type: project
  originSessionId: 8cc92186-b4e6-4362-bfc0-3943c8b8b3de
  modified: 2026-09-29T02:03:36.563Z
---

**课程定位**：`AI大模型应用开发/1.智服中台：企业级客服中台Agent系统/` 是 2026-09-28 到货的新课（与 9/12 冲刺计划无关，那份计划已过期）。主题是**后端工程**（并发、状态一致、任务恢复、性能测量、流式、部署运维），Agent 只是载体。课件是离线网页：`zhifu-courseware/index.html`；正文 md 在 `zhifu-courseware/articles/lesson-01.md`~`lesson-06.md`（第 6 篇 = 简历与面试表达）；`materials/branch-guide.md` 讲分支与环境。

**代码**：`C:\workspace\zhifu-platform`（ASCII 路径，Bash 可用）。2026-09-29 从课件 `downloads/zhifu-course.bundle` 拉入 10 个本地分支 `course/00-handover`…`course/09-course-delivery` 和 10 个 tag `course-00-…`；同仓库还有用户 9/28 克隆的 `origin/main`（老师原始项目，3 个提交，与教学分支不同源，不用）。当前检出 `course/09-course-delivery`。`.venv` 已用 `uv sync --frozen --no-group inference` 建好（Python 3.12，跳过 torch）。**这台机器 git 无 `switch`，用 `git checkout`**。读增量一律 diff **tag**（分支比 tag 各多 2 个前端提交）。切分支前 `git status --short` 必须为空，练习代码放个人分支 `study/*`。

**学法约定（本项目）**：
- 00 基线理解型（懂架构 + 两条主链路 + 能跑通），01~09 只读相邻 tag 的 diff（各 3~12 个文件，最大 +478 行）；08 无 src 改动。
- 讲解与 Q&A 写进用户笔记 `C:\workspace\学习笔记\智服中台.md`（已建：部署拓扑 + 链路 A 聊天→Agent→回复 + 链路 B 确认→审批→提醒→履约→OMS 的 Mermaid 流程图、十阶段增量表、第一课 🔴🟡🟢 路线、三问占位、Q&A 区、进度锚点）。**不往 course 仓库源码里写注释**（会弄脏 git status、阻碍切阶段）。
- 课件架构图（docs/architecture/*.png）标"目标架构"：Celery、OSS、OpenTelemetry、Nginx、K8s 在代码里不存在（多副本入口是 HAProxy）——教到第一课 §2 时再说。
- 实验环境重（Docker 十个容器 + BGE-M3 + Milvus，需 PowerShell 7 的 `scripts/course/environment.ps1`）；按 [[interview-goal]] 深度标尺，实验细节一笔带过，动手攒到讲完再统一做。

**进度锚点**：2026-09-29 架构地图完成，尚未开始第一课；下一步 = 第一课 §1-§3 自读 + 路线 1~6 步。

**Why:** 会话常断，重连时靠这条直接接上；避免再误把 origin/main 当教学代码、或用 `git switch` 报错。
**How to apply:** 新会话先读 `学习笔记/智服中台.md` 的进度锚点，再按 [[tutor-role]]、[[pacing-small-chunks]]、[[quiz-frequency-feedback]] 的微步模板带学；每课开始前先在笔记第 6 节追加该课的 🔴🟡🟢 路线。
