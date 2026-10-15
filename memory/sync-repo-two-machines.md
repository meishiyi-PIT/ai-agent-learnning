---
name: sync-repo-two-machines
description: 2026-10-15 起家里机⇄公司机用 GitHub 仓库 ai-agent-learnning 同步记忆/笔记/课件/练习；开工 sync-pull、收工 sync-push；仓库 public 期间简历被 gitignore 挡住
metadata:
  node_type: memory
  type: project
  originSessionId: 7d0791f3-e194-4fa9-9858-702628d2a16d
  modified: 2026-10-15T13:51:02.006Z
---

用户从 2026-10-15 起在公司电脑也用 AI 学习，两台机器靠 GitHub 仓库 `https://github.com/meishiyi-PIT/ai-agent-learnning.git` 同步，本地在 `C:\workspace\ai-agent-learnning\`（交接文档 `README.md`，给 AI 的说明 `CLAUDE.md`，非 Claude Code 用 `启动提示词.md`）。

仓库里同步的东西：`memory/`（这套记忆的副本）、`学习笔记/`、课件 md（`课件/`，无视频 PDF）、`practice/`（无远端的练习项目）、`repos/*.bundle`（zhifu-platform / harness_zbt / DeepAgent / meishiyi 的 git 打包 + `local-changes/` 未提交改动）、`workspace-config/`（工作区 CLAUDE.md 等）。`.env` 永远不进。

**Why:** 会话历史不能跨机器，但进度全在记忆 + 各计划文件末尾锚点里，靠这两样就能接续。仓库是 public，用户明确说 `简历/` 不传：已从同步脚本去掉并被 `.gitignore` 兜底，简历只在家里机。

**How to apply:**
- 用户说"推送/同步/上传进度"→ 跑 `powershell -ExecutionPolicy Bypass -File C:\workspace\ai-agent-learnning\scripts\sync-push.ps1`（改过课程仓库代码加 `-WithRepos`）；说"拉取/同步下来"→ `sync-pull.ps1`。规则：开工先 pull、收工必 push，拷贝是"新者为准、不删除"。
- 新会话若发现锚点和记忆对不上（比如公司机学了没 push），先提醒用户跑一次 pull/push。
- 笔记和记忆照常写在工作区原位置（`C:\workspace\学习笔记\`、记忆目录），不要直接改仓库里的副本。
- 旧的 `C:\workspace\sync-bundle\` 是 8 月未推送的旧版，已被取代。
相关：[[tutor-role]] [[agent-review-plan-interview]] [[review-module5-6]] [[resume-project]]
