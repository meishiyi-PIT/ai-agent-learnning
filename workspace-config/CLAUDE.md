# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 这是什么

`C:\workspace` 不是单一代码库,而是一个人的"AI 大模型应用开发"课程学习工作区:根目录下并列着十几个互不关联的独立小项目/练习,每个项目各自管理自己的 Python 环境和(如果有)git 仓库;**根目录本身不是 git 仓库**。

在任何子目录中工作前,先确认该子目录自己的 `pyproject.toml` / `requirements.txt` / `.venv` / `.git` —— 不要假设根目录的配置对子项目生效,也不要跨子项目共用 `.env`。

## 目录速查

### 课程材料(只读参考,非代码)

- `AI大模型应用开发/` —— 当前主课程的完整课件,含模块一/二/三的 mp4/pdf/md,以及 `复习笔记/`(01-16,按课程顺序整理的复习笔记)。这是最新、最完整的一份课件。
- `课件/` —— 旧课件目录,有效内容与 `AI大模型应用开发/` 下模块二/三的课件重复;目录里还混入了一个巨大的播放器安装包(`SZPlayer(window)*/`),可以忽略。
- 根目录一批学习笔记(`a2a 学习.md`、`agentic_rag_project.md`、`deepagents 学习.md`、`langgraph_course.md`、`multi-agent 学习.md`、`rag 学习.md`)—— 早期做法留下的产物,用户已明确要求以后讲解直接写进对应代码文件(注释/docstring),不再新建这类独立 md 笔记。
- 根目录两个 `12_Agentic RAG项目实战…*.sz` —— 录播专用容器格式的课程视频,非源码。

### 课程配套练习项目(各自独立,多数用 `uv` 管理)

- `a2a/` —— Google A2A 协议演示(client/server + 有/无 A2A 集成方式对比)。
- `Agentic_Rag/` —— 电商售后场景 Agentic RAG(FastAPI + LangGraph + Milvus + SQLite + Tavily + DeepSeek)。
- `Agentic_Rag_vpn/`、`07_Agentic_Rag/` —— 从 `Agentic_Rag/` 复制出的 VPN 故障诊断变体,同架构换了业务域和数据。
- `Multi-Agent/` —— FastAPI + SSE 的多 Agent 协作演示(Supervisor / Pipeline / Debate 三种模式)。
- `MemoryAgents/` —— 已 `git init` 但尚无任何提交的空仓库。
- `ai-agent/` —— `RAG实战/`(`langchain-1`、`02_DATA_ANALYSIS`、`03_RAG`、`04_RAG_OPTIMIZE`)与 `AgenticAI/` 练习,各子目录自带 `.venv`。
- `ai-example/` —— 按课程模块编号的练习集(`01_langchain` … `08_multi_agent`,含内嵌的 `MemoryAgents/`),各子目录自带 `pyproject.toml`/`uv.lock`。
- `workspace/ai-example/` —— 上面 `ai-example` 的另一份独立 git 克隆副本。
- `meishiyi/` —— 用户自己的课程作业仓库,按模块编号镜像/备份了部分练习(`02_DATA_ANALYSIS`、`03_RAG`、`04_RAG_OPTIMIZE`、`06_MCP`、`07_Agentic_Rag` 等)。
- `p1/` —— 最小的临时脚本(`prompt.PY` + `.env`)。
- `python-for-agents/` —— 不属于官方课程,是为用户量身定制的 1 小时 Python 速成课;所有语法示例取自上面这些真实项目(对照表见 `python-for-agents/README.md`)。

## 常用命令

多数练习项目用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境和依赖,进入对应子目录后:

```bash
uv venv --python 3.11      # 首次创建虚拟环境
uv sync                    # 按 pyproject.toml / uv.lock 安装依赖
uv run <command>           # 在项目虚拟环境中运行命令
uv run pytest              # 跑测试(如 Agentic_Rag/tests)
```

Windows 下运行含中文输出的脚本容易触发编码报错,按需加上以下之一:

```bash
python -X utf8 script.py
PYTHONUTF8=1 uv run script.py
```

## 双机同步（家 ⇄ 公司）

- `ai-agent-learnning/` —— 2026-10-15 起用的 GitHub 同步仓库（`https://github.com/meishiyi-PIT/ai-agent-learnning.git`），同步 Claude 记忆副本、`学习笔记/`、课件 md、无远端的练习项目、课程仓库 bundle。完整说明见 `ai-agent-learnning/README.md`。
- 开工先跑 `ai-agent-learnning/scripts/sync-pull.bat`，收工跑 `sync-push.bat`；用户说"推送进度"就跑 `powershell -ExecutionPolicy Bypass -File ai-agent-learnning/scripts/sync-push.ps1`。
- 笔记和记忆照常写在工作区原位置（`学习笔记/`、`~/.claude/projects/C--workspace/memory/`），不要直接改仓库里的副本；`.env` 永远不进仓库。
- `sync-bundle/` 是 8 月的旧版同步包，从未推送，已被取代。

## 重要约定

- 每个带 `.git` 的子目录都是独立仓库;`git` 命令要在具体子目录里运行,根目录没有可提交的顶层仓库。
- `Agentic_Rag*` 系列项目的数据/文档路径是相对 `app/config.py` 位置解析的,不依赖运行时的当前工作目录;`.env` 保存在各自项目根目录,不要跨项目复用。
- `AI大模型应用开发/`、`课件/` 以及根目录的独立学习笔记都是只读参考资料,不是需要维护或重构的代码。
