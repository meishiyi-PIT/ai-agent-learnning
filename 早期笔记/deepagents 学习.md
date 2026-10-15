# Deep Agents 学习笔记

> 课件来源：`模块三：企业级 Agentic AI 开发\课件\8.DeepAgents 项目实战\1.Deep Agents 核心理论与能力边界.md`
> 学习方式：白话讲解 + 官方文档核实。本笔记随学习进度追加。

---

## 一、Deep Agents 是什么（课件第一部分）

### 1. 一句话定位

**Deep Agents 不是新模型，是一个 Agent Harness（智能体工程套件）**——把复杂 Agent 都需要的那些工程能力（规划、文件、上下文管理、子 Agent）提前装配好的"精装房"。

三层关系（谁在谁之上）：

| 层 | 干什么 | 打个比方 |
| --- | --- | --- |
| LangChain | 模型接入、工具定义、基础 Agent 循环（`create_agent`） | 发动机和零件 |
| LangGraph | 状态机、固定流程、分支/重试/中断（确定性流程） | 底盘和传动 |
| Deep Agents | 在上面两层之上预装规划、文件系统、上下文压缩、子 Agent | 开箱即用的整车 |

### 2. `create_agent` vs `create_deep_agent`

调用代码几乎一样，差异在**运行时装配的默认 Middleware（中间件）**。`create_deep_agent()` 默认多装了 6 样东西：

1. **Planning** — `write_todos` 工具 + 任务状态
2. **Virtual Filesystem** — `ls/glob/grep/read_file/write_file/edit_file` 文件工具 + 默认 `StateBackend`
3. **Context Offloading** — 工具结果太大时写入文件，上下文里只留引用
4. **Summarization** — 对话太长时用 LLM 把旧消息压成摘要
5. **Subagent Delegation** — `task` 工具，把子任务派给独立上下文的子 Agent
6. **Tool-call Recovery** — 中断后修复不完整的工具调用历史

Skills / Memory / HITL（人在回路）有统一配置入口，但**内容和策略要开发者自己给**。

### 3. 它不会自动帮你做业务

`create_deep_agent()` 只是组装入口。要成为能交付的业务 Agent，还得自己补：业务目标与输出规范、自定义业务工具、业务规则、数据与权限、测试与评测。

"满配"参数（已对照官方 API 核实，全部真实存在）：

```python
agent = create_deep_agent(
    model=model,
    system_prompt=...,      # 业务目标与执行协议
    tools=[...],            # 自定义业务工具
    subagents=...,          # 子 Agent 分工
    skills=["/skills/"],    # 技能包目录
    memory=[...],           # 长期记忆文件
    backend=...,            # 文件存到哪
    store=...,              # 跨会话存储（配 StoreBackend 用）
    permissions=...,        # 文件访问权限（需 deepagents >= 0.5.2）
    interrupt_on=...,       # 敏感工具人工审批（必须配 checkpointer）
    checkpointer=...,       # 状态检查点，中断后恢复用
)
```

补充（课件没写，官方文档有）：
- `model=None` 时默认用 Claude Sonnet 4.5；也可传 `"openai:gpt-5"` 这种字符串自动解析。
- `interrupt_on` 单独用会**不生效**，必须同时传 `checkpointer`（如 `MemorySaver()`）。

### 4. 选型口诀

| 任务特征 | 用什么 |
| --- | --- |
| 单轮问答、少量工具调用 | LangChain |
| 流程必须确定（分支、补偿、审批固定） | LangGraph |
| 大量文件、多步调查、路径没法预先定 | Deep Agents |
| 固定主流程中嵌一段开放式调查 | LangGraph + Deep Agents |

**核心原则：确定性必须来自业务代码或 Graph，不能靠更长的 Prompt。**
Prompt 是概率性的——模型可能照做也可能不照做；Graph 的边和业务代码是 100% 执行的。"付款前必须审批"这种硬规则写进 prompt 就是在赌运气。

---

## 二、Virtual Filesystem 虚拟文件系统（课件 2.1）

### 1. 解决什么问题

传统 Agent 的所有材料、工具结果、中间结论都堆在**消息历史**里。每次调用模型，全部历史都要重发一遍——任务越长，每次带的无关内容越多，又贵又容易让模型迷失。

虚拟文件系统给 Agent 一个**有地址的文件柜**：材料有路径，Agent 可以先搜索（`grep`）、再分段读（`read_file` + offset/limit）、把结论写回文件（`write_file`）。

> 价值不是"无限上下文"，而是：**不必一直随身携带全部内容 + 需要时能凭路径找回原始证据**。

### 2. 谁调用，谁执行（三方分工）

```
模型：只负责"选工具 + 生成参数"（它生成一段 JSON，从不碰磁盘）
  → Deep Agents 文件中间件：接住这个工具调用
  → Backend（存储后端）：真正执行读写
  → 结果返回给模型
```

开发者的职责：配置 Backend、权限、放入初始材料。不需要手动执行文件工具。

### 3. 六个内置文件工具

`ls` / `glob` / `grep` / `read_file` / `write_file` / `edit_file`

- 名字像 Shell 命令，但**不是**在操作系统终端执行的命令，是框架内置工具。
- ⚠️ `grep` 的 pattern 是**字面量匹配，不是正则**（官方源码注释："Literal string to search for (NOT regex)"）。想找多个关键词就分多次调用。底层有 ripgrep 就用 ripgrep（fixed-string 模式），没有就退化为子串搜索。

### 4. 开发者代码 vs Agent 运行轨迹（课件 2.1.4 的重点区分）

- **开发者写的**：`create_deep_agent(backend=StateBackend())` + `agent.invoke({"messages": [...], "files": {"/data-room/x.md": create_file_data(text)}})`
- **Agent 自动产生的**：运行时的 `ls/grep/read_file/write_file` 调用轨迹，不需要人写。

要点：
- 虚拟路径必须以 `/` 开头；`StateBackend` 下文件存在 Agent State 里，操作系统里并不存在这些目录。
- `create_file_data()` 把字符串包装成后端要求的文件数据结构——官方明确**不支持直接传原始字符串**。

### 5. Backend 决定文件的"寿命"

| Backend | 文件活多久 | 典型用途 |
| --- | --- | --- |
| `StateBackend`（默认） | 当前 Thread（一次会话） | 草稿、todo、大结果卸载 |
| `FilesystemBackend` | 真实磁盘，长期 | CLI 工具、代码库 |
| `StoreBackend` | 跨 Thread / 跨会话 | 用户记忆、Agent 经验 |
| `SandboxBackend` | 跟随沙箱 | 隔离执行代码/命令 |

`CompositeBackend` 按路径前缀路由：如 `/workspace/` → StateBackend，`/memories/` → StoreBackend。

安全要点：
- `FilesystemBackend(root_dir=..., virtual_mode=True)` 把 Agent 关在 root_dir 里（挡住 `..`、`~`、外部绝对路径）。
- 但 **virtual_mode 不会隐藏敏感文件**：`.env`、密钥在 root_dir 里照样能被读。要么移出目录，要么用 `permissions` 明确禁读。别把服务器根目录直接交给 Agent。

---

## 课件勘误表

| 位置 | 课件写法 | 实际情况 | 来源 |
| --- | --- | --- | --- |
| 2.4.1 `write_todos` 示例 | `{"subject": "...", "status": ...}` | 官方字段名是 **`content`**，不是 `subject`。状态值 `pending/in_progress/completed` 是对的；另外官方约束"同一时刻最多一个 in_progress" | LangChain 官方 todo-list 文档、实际调用日志 |
| 1.3 `permissions` 参数 | 未提版本要求 | 需要 **deepagents ≥ 0.5.2**；且只约束内置文件工具，管不住自定义工具和 MCP 工具 | LangChain 官方 Permissions 文档 |

---

## 参考来源

- [create_deep_agent API 参考](https://reference.langchain.com/python/deepagents/graph/create_deep_agent)
- [Deep Agents 官方文档 - Customization](https://docs.langchain.com/oss/python/deepagents/customization)
- [Deep Agents 官方文档 - Permissions](https://docs.langchain.com/oss/python/deepagents/permissions)
- [Deep Agents 官方文档 - Todo list](https://docs.langchain.com/oss/python/deepagents/frontend/todo-list)
- [langchain-ai/deepagents GitHub](https://github.com/langchain-ai/deepagents)
