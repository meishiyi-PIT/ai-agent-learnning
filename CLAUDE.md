# CLAUDE.md（本仓库）

这是一个人的 **AI Agent 课程学习状态同步仓库**，不是代码项目。它在家里电脑和公司电脑之间同步"学到哪了 + AI 助教怎么教 + 学习资料"。真正的工作区是上一级目录（通常 `C:\workspace`），本仓库 clone 在 `C:\workspace\ai-agent-learnning`。人类可读的完整说明见 `README.md`。

## 你（AI）开工时按这个顺序做

1. 读 `memory/MEMORY.md`（记忆索引），再按需读索引指向的记忆文件。它们记录了用户是谁、Python/数学水平、带学规矩、每条学习线的状态。
   - 如果你是 Claude Code 且工作区是 `C:\workspace`，这些记忆已在 `~/.claude/projects/C--workspace/memory/` 自动加载，不必重复读。
2. 读三个进度锚点，确认"现在学到哪、下一步做什么"：
   - `学习笔记/Agent复习计划-面试向.md` 最末 §8（主线）
   - `学习笔记/大模型底层原理复习/复习-模块五六-总纲.md` 最末 §5
   - `学习笔记/智服中台.md` 最末 §9
3. 先用一两句复述进度和下一步，和用户对齐后再开始带学（记忆 `tutor-role` 里有"每次会话先核实进度"的要求）。

## 写东西的规矩

- 笔记、Q&A、进度锚点写进 **工作区的** `C:\workspace\学习笔记\...`（不是本仓库里的副本；副本由 `scripts/sync-push` 收工时拷过来）。记忆写进 Claude 的记忆目录，同理。
- 不往 `课件/` 里写（只读课件；模块六汇总笔记 `大模型微调.md` 是例外，规矩见记忆 `module6-notes-doc`）。
- 不往课程仓库（`zhifu-platform` 等）写注释，见记忆 `zhifu-platform-course`。
- 绝不把 `.env` / API key 放进本仓库。
- 本仓库的 `git add/commit/push` 由 `scripts/sync-push.ps1` 统一做；用户让你推送时直接跑它：`powershell -ExecutionPolicy Bypass -File scripts/sync-push.ps1`。

## 本机常见坑

- 这台家里机器的 Bash 命令串里含中文会直接失败（exit 127），中文路径改用 Read/Grep/Edit/Write 工具或先写成脚本再跑（记忆 `bash-chinese-chars-fail`）。公司机未必有此问题，先试一次再定。
- Windows 下跑含中文输出的 Python 加 `-X utf8` 或 `PYTHONUTF8=1`。
- 课程代码仓库的分支：`zhifu-platform` 用 `course/00~09` 分支和 `course-00~09` 标签（看 diff 用 tag，切换用 checkout）；`harness_zbt` 用 `phaseOne/Two/Three`。
