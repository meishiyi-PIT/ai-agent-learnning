# AI Agent 课程 · 学习状态同步仓库（交接文档）

> 用途：家里电脑 ⇄ 公司电脑之间同步"我学到哪了 + AI 助教该怎么教我 + 学习资料"。
> 两边都是 **开工先 pull，收工必 push**，AI 在哪台机器上都能接着上一次的进度继续带学。
> **仓库里没有任何密钥**（`.env` 永远不进来）。

---

## 1. 仓库里有什么 / 没有什么

| 路径 | 内容 | 铺回本机后的位置 |
|---|---|---|
| `memory/` | **Claude Code 的记忆**（29 个 md，`MEMORY.md` 是索引）。记录了我的水平、带学规矩、各条学习线的进度锚点 | `%USERPROFILE%\.claude\projects\C--workspace\memory\`（Claude Code 自动加载） |
| `学习笔记/` | 全部学习笔记：智服中台、Agent 复习计划（面试向）、模块五六底层原理复习（总纲/知识地图/全量清单）、Harness 智保通、DeepAgents… | `C:\workspace\学习笔记\` |
| `学习计划-冲刺9.12.md` | 早期冲刺计划（已过期，留作参考） | `C:\workspace\` |
| `课件/AI大模型应用开发/` | 主课件的 **md / 图 / docx**（模块一～六 + `复习笔记/01~16` + 模块六我自己的汇总 `大模型微调.md`）。视频 `.sz`、PDF 不带 | `C:\workspace\AI大模型应用开发\` |
| `课件/AI大模型应用开发/1.智服中台…/zhifu-courseware/` | 智服中台网页课件（`articles/lesson-01~06.md/html` + 图），双击 `index.html` 可离线看 | 同上 |
| `课件/AI大模型应用开发课件/` | 另一份课件目录（内容大体重复，多了 `简历模板/` 四个 docx 和两张上课画图） | `C:\workspace\AI大模型应用开发课件\` |
| `repos/*.bundle` | 四个课程代码仓库的 git 打包（全部分支+标签）：`zhifu-platform`、`harness_zbt`、`DeepAgent`、`meishiyi` | `C:\workspace\<仓库名>\`（`setup-company` 自动 clone） |
| `repos/local-changes/` | 上述仓库里 **尚未 commit 的我的改动**（续保规划作业、随堂注释、09_HuggingFace 练习）：`tracked.patch` + `untracked/` | `setup-company` 自动打回去 |
| `practice/` | 我自己写的、没有远端仓库的练习：`python-for-agents`、`fastapi-practice`、`DeepAgent-novapay-practice`、`nlp-practice`、`deepLearning`（不含数据集/权重）、`tools` | `C:\workspace\<同名目录>\` |
| （不同步）`简历/`、`学习笔记/简历梳理.md` | 简历草稿、定稿、面试表达稿。**不上传**：已从同步脚本去掉，`.gitignore` 再兜底挡一次 | 只在家里机 `C:\workspace\简历\` |
| `resume-refs/` | OCP 官方文档副本（写简历项目四用） | `C:\workspace\resume-refs\` |
| `画图/` | excalidraw 画图 | `C:\workspace\画图\` |
| `早期笔记/` | 7 月的独立 md 笔记（a2a / agentic rag / langgraph / multi-agent…），只读参考 | `C:\workspace\` 根目录 |
| `workspace-config/` | 工作区根目录的 `CLAUDE.md`、`AGENTS.md`、`.claude/settings.local.json`（权限白名单） | `C:\workspace\` |
| `scripts/` | 三个脚本：`setup-company`（首次）、`sync-pull`（开工）、`sync-push`（收工），每个都有 `.bat` 双击版 | — |
| `启动提示词.md` | 给 **非 Claude Code** 的 AI 用的开场提示词（Cursor / 网页版 Claude / 其它） | — |
| `CLAUDE.md` / `AGENTS.md` | 给 AI 看的仓库说明 | — |

**不在仓库里的**（太大或有密钥）：课程视频 `.sz`/`.mp4`、课件 PDF、各项目 `.venv`、模型权重、数据集（CIFAR/MNIST/ag_news）、`code/`（老师的模块五六代码库，1.9 GB，公司机需要时自己 `git clone https://git.miaoatech.cn/ryanxiao/code.git`）、所有 `.env`。

---

## 2. 公司电脑首次安装（只做一次）

前提：装好 **Git for Windows**（https://git-scm.com/download/win）。

```bat
mkdir C:\workspace
cd C:\workspace
git clone https://github.com/meishiyi-PIT/ai-agent-learnning.git
```

然后双击 `C:\workspace\ai-agent-learnning\scripts\setup-company.bat`。它会：

1. 把笔记、课件、练习项目、`CLAUDE.md` 铺到 `C:\workspace\`
2. 把 `memory/` 装到 `%USERPROFILE%\.claude\projects\C--workspace\memory\`
3. 用 `repos\*.bundle` 把四个课程代码仓库 clone 到 `C:\workspace\` 并切到学习分支，再把我未提交的改动打回去
4. 打印验证步骤

> 工作区路径请保持 `C:\workspace`。记忆和笔记里写的都是这个绝对路径；换了路径也能用，但要口头告诉 AI。

**装 AI**（任选）：
- Claude Code：需要 Node.js 18+，`npm install -g @anthropic-ai/claude-code`，然后 `cd C:\workspace` 再 `claude`。记忆会自动加载。
- 其它 AI（Cursor / Codex / 网页版）：打开 `启动提示词.md` 整段贴进去，并让它先读 `memory/MEMORY.md`。

**验证**：对 AI 说
> 读一下你的记忆索引，再读 `学习笔记/Agent复习计划-面试向.md` 和 `学习笔记/大模型底层原理复习/复习-模块五六-总纲.md` 末尾的进度锚点，告诉我现在学到哪、下一步做什么。

它应该能答出 §5 里的内容，就说明同步成功。

---

## 3. 每天怎么用

| 时机 | 做什么 | 怎么做 |
|---|---|---|
| **开工**（到公司 / 回到家） | 把另一台机器推上来的进度拉下来 | 双击 `scripts\sync-pull.bat` |
| 学习中 | 正常用 AI 带学。AI 会改 `memory/`（记忆）和 `学习笔记/`（锚点、Q&A） | — |
| **收工**（离开公司 / 睡前） | 把今天的进度推上去 | 双击 `scripts\sync-push.bat` |

脚本的拷贝规则是 **"新者为准、不删除"**：两边同一个文件，谁的修改时间新就用谁的。只要守住"先 pull 后 push、同一时间只在一台机器上学"，就不会丢东西。

如果 push 时报 `pull --rebase 失败`，说明两台机器都改了同一个文件（忘了 pull 就学了）。处理：在仓库目录 `git status` 看冲突文件 → 手动合并 → `git add .` → `git rebase --continue` → 再双击 `sync-push.bat`。

**课程代码仓库**（zhifu-platform 等）日常不参与同步。只有当我在某台机器上改了它们的代码（做作业、加注释）又没 commit 时，收工用命令行跑一次：
```bat
powershell -ExecutionPolicy Bypass -File scripts\sync-push.ps1 -WithRepos
```
另一台机器拉下来后，手动把 `repos\local-changes\<仓库>\tracked.patch` 用 `git apply --3way` 打上、`untracked\` 里的文件拷过去（首次安装时 `setup-company` 会自动做这一步）。

---

## 4. 工作区长什么样（铺回之后）

```
C:\workspace\
├─ ai-agent-learnning\        ← 本仓库（唯一需要 git pull/push 的地方）
├─ CLAUDE.md / AGENTS.md       ← 给 AI 的工作区说明（来自 workspace-config/）
├─ 学习笔记\                   ← 所有笔记和进度锚点（AI 会往里写）
├─ AI大模型应用开发\            ← 课件 md（视频/PDF 不在）
├─ AI大模型应用开发课件\
├─ zhifu-platform\             ← 当前主线：智服中台（course/00~09 分支 + course-00~09 标签）
├─ harness_zbt\                ← 模块四智保通（phaseOne/Two/Three）+ 我的续保规划作业（未提交）
├─ DeepAgent\  meishiyi\       ← DeepAgents 课程仓库 / 我的作业仓库
├─ python-for-agents\ fastapi-practice\ DeepAgent-novapay-practice\ nlp-practice\ deepLearning\ tools\
├─ 简历\  resume-refs\  画图\
└─ 学习计划-冲刺9.12.md, a2a 学习.md 等早期笔记
```

---

## 5. 当前进度快照（2026-10-15）

> 这一节只是快照，**真正的锚点在各计划文件末尾**，AI 开工先读它们。

三条学习线并行，重心是第一条：

1. **Agent 面试向复习（主线）** —— 锚点 `学习笔记/Agent复习计划-面试向.md` §8；笔记 `学习笔记/智服中台.md` §7/§8；地图 `学习笔记/agent复习/面试复习-00-主线地图.md`。
   以智服中台五课为主干（zhifu-platform，读码停在最终版 `course/09-course-delivery`）。2026-10-11 定的做法：不手写代码、不起环境，拿仓库里老师真实跑过的记录当线索沿代码走。**下一步：用 `order-list-01`（"查看我的订单"）这条记录走第一课 §5 执行流程，从 `conversations/api.py accept_message` 进入。**
   学法四条：三问即止（是什么/为什么/怎么选）、30 分钟定时盒、先看 diff 再讲原理、没懂先记录。

2. **模块五六底层原理复习** —— 锚点 `学习笔记/大模型底层原理复习/复习-模块五六-总纲.md` §5。
   六个重点（Transformer / RoPE+RMSNorm / GQA+KV Cache / MoE / LoRA / QLoRA / vLLM）的公式、代码走读、三条融合主线已全部完成（2026-10-11）。**下一步：租 GPU 日按总纲 §3 执行单跑 ⓪~④，把实测数字填回各节。** 公司机没 GPU，这条线在公司只能复习不能实跑。

3. **简历** —— 文件只在家里机 `C:\workspace\简历\`（不同步）：`简历定稿-v2-浓缩版.md`（可直接用）、`简历草稿-v1.md`（设计稿 + 知识补充清单）、`项目二-面试表达.md`。四个项目已定稿（数据编排 Agent / 工单诊断 Agent / LoRA 微调 / 运维知识库 RAG）。下一步：按各项目末尾"知识补充清单"补知识。

旧线（已完成或暂停）：模块四智保通 harness_zbt phaseThree 已学完，续保规划作业的代码在 `repos/local-changes/harness_zbt/`；DeepAgents NOVAPAY 作业在 `practice/DeepAgent-novapay-practice/`。

带学规矩全部在 `memory/` 里（`tutor-role`、`pacing-small-chunks`、`teaching-map-before-code`、`teach-directly-no-line-refs`、`quiz-frequency-feedback`、`explain-demo-output`、`interview-goal` 等），AI 读 `MEMORY.md` 索引即可。

---

## 6. 隐私与密钥

- **仓库目前是 public。** 简历相关（`简历/`、`学习笔记/简历梳理.md`）已从同步脚本里去掉并被 `.gitignore` 兜底，不会上传。`memory/` 里仍有学习/求职背景的概述，若介意，到 GitHub → Settings → General → Danger Zone → Change visibility 改成 **Private**。
- 提交者邮箱已设为 GitHub 的 noreply 地址（仓库本地配置），不会把手机号邮箱暴露在提交记录里。
- `.env` 一律不进仓库，`sync-push` 会主动删除混进来的 `.env` 并扫描疑似 API key。公司机需要跑代码时手动建：

| 项目 | 文件 | 里面的变量（只列名字） |
|---|---|---|
| `harness_zbt/backend/.env`（没有 example） | 需要整套基础设施（MySQL/Redis/Milvus/BGE 模型），公司机基本只读码不跑 | `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`DASHSCOPE_API_KEY`、`LANGSMITH_API_KEY`、`MYSQL_*`、`REDIS_URL`、`MILVUS_URI`、`BGE_M3_MODEL_PATH`、`JWT_*`、`FIELD_ENCRYPTION_KEY` 等 |
| `DeepAgent/.env`、`DeepAgent-novapay-practice/.env` | 两个文件内容相同 | `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL_NAME`、`DEEPSEEK_ANSWER_THINKING`、`LANGSMITH_TRACING`、`LANGSMITH_API_KEY`、`LANGSMITH_PROJECT`、`APP_ENV`、`LANGSMITH_HIDE_INPUTS`、`LANGSMITH_HIDE_OUTPUTS` |
| `zhifu-platform/.env` | 复制 `.env.example`（仓库里有三份 example） | 读码不需要；跑起来才需要 |
| `Agentic_Rag*`（不在同步范围） | 各自目录 | DeepSeek、Tavily |

key 的传递方式：手机备忘录 / 密码管理器，不要走聊天工具和本仓库。

---

## 7. 常见问题

- **AI 说"没有记忆/不知道进度"**：检查 `%USERPROFILE%\.claude\projects\C--workspace\memory\MEMORY.md` 是否存在；没有就双击 `sync-pull.bat`。工作区必须是 `C:\workspace`（目录名 `C--workspace` 就是由它来的）。
- **PowerShell 脚本无法运行 / 中文乱码**：用 `.bat` 双击版（内置 `-ExecutionPolicy Bypass` 和 UTF-8）；或命令行 `powershell -ExecutionPolicy Bypass -File scripts\xxx.ps1`。
- **公司访问不了 `git.miaoatech.cn`**：没关系，四个课程仓库都用 bundle 还原，不需要联网；只有 `code/`（模块五六老师代码）没带，需要时在家 push 一次 bundle 或直接看课件 md。
- **想把 PDF 课件也带上**：PDF 大约 150 MB，GitHub 单文件 100 MB 以下都能传。把 `.gitignore` 里的 `*.pdf` 去掉、在 `scripts/common.ps1` 的 `$CourseMasks` 里加 `'*.pdf'` 即可。
- **`sync-bundle/` 和这个仓库什么关系**：`C:\workspace\sync-bundle\` 是 8 月做的旧版同步包，从未推送过，已被本仓库取代，可以删。
