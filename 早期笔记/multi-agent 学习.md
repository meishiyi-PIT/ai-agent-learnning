# Multi-Agent 学习（Supervisor 模式）

> 课件：`课件\模块二：RAG开发实战\模块三：企业级 Agentic AI 开发\6.Multi-Agent 架构：从单兵作战到团队协作.md`
> 2026-07-25 第一次学习：第一、二部分（概念）+ 全文代码预核查

---

## 一、为什么需要 Multi-Agent：单 Agent 的三个结构性局限

### 局限 1：工具越多，选错越多

一个 Agent 挂 20 个工具，模型每次都要在 20 个里挑，挑错、传错参数的概率上升。

**真实研究数据（查漏补缺）：**
- LongFuncEval（Kate et al. 2025）：工具目录变大后，函数调用性能损失 7%~85%
- 约 50 个工具时，前沿模型选对工具的准确率还有 84~95%；超过 100 个工具时，部分测试掉到 13~15%（接近乱猜）
- 下降不是平滑的，而是"平台期 → 断崖"：某测试中从 207 个工具增加到 417 个，准确率从 64% 掉到 20%
- 缓解方案除了拆 Multi-Agent，还有 **Tool RAG**（先检索相关工具，再喂给模型）

**⚠ 课件配图勘误：** 首图 OCR 写"工具选择幻觉概率随工具数量**指数增长**"——没有研究支持"指数"这个说法，实际是非线性的"先平台后断崖"。课件正文（"10 个不是普适阈值，应通过评测确定拆分边界"）反而是对的，以正文为准。

### 局限 2：上下文堆积，关键信息被淹没

多轮 tool call 的返回结果（每次 1500~3000 tokens）快速填满上下文，早期的核心指令被"淹没"。

**真实研究数据：**
- **Lost in the Middle**（Liu et al. 2023, arXiv:2307.03172）：关键信息在上下文中间位置时，性能比在开头/结尾低 30%+，呈 U 型曲线；在 GPT-4、Claude 等六个模型家族上复现
- 后续研究：性能下降远早于窗口上限——有模型多加 1000 tokens 就掉 16 个百分点

**补充：** 多 Agent 的"上下文隔离"只是解法之一，同类解法还有：上下文压缩/摘要（compaction）、把中间结果落盘只传引用。工程上常常先做上下文管理，不够了再拆 Agent。

### 局限 3：推理路径难调试

单 Agent 出错时，搜索、推理、代码生成全混在一条消息历史里，只能从最终输出倒推根因。

**更准确的说法（查漏补缺）：** 单 Agent 并非完全"黑箱"——用 LangSmith 也能看到每一步 trace。真正的问题是**故障域不隔离**：所有职责混在一个流程里，无法按模块定位和单独测试。多 Agent 的价值是每个 Agent 可以独立测试、独立看日志。

---

## 二、Supervisor 模式：总控 + 专家

### 核心思想：职责分离

- **Supervisor（前台经理）**：拆解任务 → 路由调度 → 整合输出。自己不干活。
- **Worker（厨师）**：只做分到的子任务，不关心任务来源、别人的状态、结果怎么组合。

### 单个 Agent 的三个设计组件

| 组件 | 回答的问题 |
| --- | --- |
| Model | 需要什么推理能力/上下文长度/速度（不必都用最贵的） |
| Tools | 能对外部世界做什么（名称、描述、参数要清晰） |
| Instructions | 负责什么、不负责什么、结果交给谁 |

检验标准：一个 Worker 的职责能用一句话说清，且能单独测试。

### 编排的本质：Graph / Node / Edge / Handoff

- Graph = 整个流程 + 共享状态；Node = 一个 Agent 或工具/校验步骤；Edge = 节点间的转移条件
- **Handoff = 控制权交接。实现上就是一个工具调用**：Supervisor 拿着 `transfer_to_research_agent` 这样的路由工具，模型"调用这个工具"= 把控制权交给对应 Worker；Worker 干完再交回来
- **关键区分：控制权转移 ≠ 消息传递**。路由决定"下一步谁干"，还要单独设计"下一个 Agent 能看到哪些历史"（`output_mode` 等参数控制）。只传太少 → Worker 缺事实；全量传 → 上下文膨胀又回来了

---

## 📋 课件代码勘误表（已核实，2026-07-25）

| # | 位置 | 问题 | 修正 |
| --- | --- | --- | --- |
| 1 | 3.4 `create_supervisor(system_prompt=...)` | 参数名是 `prompt`，不是 `system_prompt`。**且不会报错**：源码末尾有 `**deprecated_kwargs`，未知参数被静默吞掉 → Supervisor 在"没有任何指令"状态下裸奔（比崩溃更隐蔽） | 改为 `prompt=(...)`。注意 3.2 的 `create_agent` 用 `system_prompt` 是对的，两个库参数名就是不一致 |
| 2 | 3.2 `TavilySearchResults`（langchain_community） | 官方已标记 **deprecated**，能跑但有弃用警告 | `pip install langchain-tavily` → `from langchain_tavily import TavilySearch` |
| 3 | 3.1 pip install 缺 `langchain` | `create_agent` 来自 `langchain` 包（需 ≥1.0），命令没显式装，版本不受控 | 加上 `pip install -U "langchain>=1.0"` |
| 4 | 3.4 注释 `draw_mermaid_png("workflow.png")` | 该方法参数是 keyword-only，位置传参会 TypeError | `draw_mermaid_png(output_file_path="workflow.png")`（还需联网，默认走 mermaid.ink API） |
| 5 | 7.4 `LANGCHAIN_API_KEY = "ls-你的key"` | LangSmith 现在的 key 是 `lsv2_` 开头；环境变量新命名为 `LANGSMITH_TRACING` / `LANGSMITH_API_KEY`（旧名仍兼容） | 用新命名 + `lsv2_` key |
| 6 | 3.5 示例 GDP 数字 | 课件已自注"不作为事实"。真实值（BEA）：2024 美国名义 GDP ≈ **29.3 万亿**美元，纽约州 ≈ **2.32 万亿**，占比 ≈ **8%**（课件示例 28.18 / 1.671 / 5.93% 均偏离）。实跑验证：我们的 Agent 搜出的就是 29.30 / 2.32 / 7.93% ✓ | 演示用可以，别当事实记 |
| 7 | 3.2 `model="deepseek-chat"` | **模型名已失效**：2026-07 实测 DeepSeek API 报 400，只接受 `deepseek-v4-pro` / `deepseek-v4-flash` | 改用 `deepseek-v4-flash` |

**参数速查（create_supervisor，来自官方 reference）：**
`prompt`（注意不是 system_prompt）、`output_mode`（默认 `"last_message"`，可选 `"full_history"`）、`add_handoff_messages`、`add_handoff_back_messages`、`handoff_tool_prefix`（默认工具名 `transfer_to_<agent名>`）、`parallel_tool_calls`（仅 OpenAI/Anthropic 支持）、`include_agent_name`

---

## 三、代码实战记录（2026-07-25 第二次学习，✅ 已跑通；第三次学习：逐段精讲 3.4）

### 3.4 配置 Supervisor —— 逐参数精讲

```python
supervisor = create_supervisor(
    agents=[research_agent, math_agent],
    model=model,
    prompt=(...),                     # 课件误写 system_prompt，见勘误表 #1
    add_handoff_back_messages=True,
    parallel_tool_calls=False,
    output_mode="full_history",
)
graph = supervisor.compile()
```

`create_supervisor` 不是"调用"某个 Agent，而是**拼一张图**：把两个已编译好的子图（`research_agent`、`math_agent`）当节点塞进一张更大的图，外加一个负责路由的 `supervisor` 节点，`.compile()` 后才是可执行对象。

- **`prompt`**：Supervisor 自己的系统提示词，告诉它手上有哪些 Agent、该派给谁。课件写成 `system_prompt=` 是错的（勘误 #1），且这个错误**不会报错**——函数签名末尾有 `**deprecated_kwargs` 兜底吞掉未知参数，Supervisor 会在完全没有指令的情况下裸奔，比语法错误更难发现。
- **`add_handoff_back_messages=True`**：Worker 交还控制权时，是否在消息历史里留一条"已交还"的记录，方便调试时看清控制权流向。我们跑出的日志里 `Successfully transferred back to supervisor` 就是它。
- **`parallel_tool_calls=False`**：限制 Supervisor 一次只能路由给一个 Worker。详细原理见下面的深挖。
- **`output_mode="full_history"`**：呼应第二部分"控制权转移 ≠ 消息传递"。默认值是 `"last_message"`（课件没提这是默认）——只带回 Worker 最后一句话；`"full_history"`（课件选的）连 Worker 内部每一轮工具调用都原样带回。教学演示用 `full_history` 能看清 Worker 内部发生了什么，但生产环境更常用默认的 `last_message`，因为 `full_history` 会让 Supervisor 的上下文越滚越大——这正是第一部分讲的"上下文堆积"局限，`full_history` 相当于把它带回来了一部分。

### 深挖：`parallel_tool_calls=True` 打开后具体会坏在哪（追问，已核实真实 bug 记录）

`parallel_tool_calls` **不是图层面的开关**，是原样转发给底层 LLM API 的标志（OpenAI/Anthropic 各自的同名参数），控制"模型能不能在一条 AIMessage 里吐出多个 tool_call"。Supervisor 场景下，工具就是 handoff 工具，打开并行 = 模型同时决定"交给研究 Agent 也交给数学 Agent"。

**故障链路 1（已有实锤 bug）：** OpenAI/Anthropic 硬性要求每个 `tool_call` 在下次调模型前必须有对应 `ToolMessage`。多个 handoff 同时存在时，一个 handoff 的 `Command(goto=...)` 会立刻跳走，另一个 tool_call 来不及生成 `ToolMessage`，变成"孤儿"，下次调模型直接报错 `Found AIMessages with tool_calls that do not have a corresponding ToolMessage`。—— [langchain-ai/langgraph#5277](https://github.com/langchain-ai/langgraph/issues/5277)

**故障链路 2（语义层面，更本质）：** 即便执行层面的冲突被处理掉，子任务之间如果有数据依赖（我们的例子：数学 Agent 要算的百分比依赖研究 Agent 先搜出的数字），并行派发会导致数学 Agent 一开局无数可算。**并行只对真正互相独立的子任务有意义**，Supervisor 通常无法提前判断这一点，所以库默认 `False`——不是保守选择，是唯一正确选择。

**库的自救措施：** `langgraph-supervisor` 检测到一条消息里有 >1 个 tool_call 时，会用 `Command(goto=[Send(agent, state), ...])`（LangGraph 的 `Send` API，用于 map-reduce 式扇出）做真正的并发分支，并过滤掉非 handoff 的工具调用。库作者愿意为这个边界情况专门写容错代码，反过来说明默认状态下这事有多脆弱。

**结论：** 真要并行处理无依赖的子任务，工程上更常见做法是不依赖 LLM 自己决定并行，而是图里显式写一个扇出节点同时调用多个 Worker，绕开 LLM 并行 tool_call 这条不稳定路径。

来源：[langgraph-supervisor handoff 工具实现（DeepWiki）](https://deepwiki.com/langchain-ai/langgraph-supervisor-py/3.2-handoff-tools) · [langchain-ai/langgraph#6436](https://github.com/langchain-ai/langgraph/issues/6436)（Command goto 与静态边冲突）· [langchain-ai/langgraph#5277](https://github.com/langchain-ai/langgraph/issues/5277)（并行 handoff 报错）· [LangChain 官方 handoffs 文档](https://docs.langchain.com/oss/python/langchain/multi-agent/handoffs)

---

**代码位置：** `ai-example/08_multi_agent/supervisor_demo.py`（修正版，可直接复跑）

```bash
cd ai-example/08_multi_agent
PYTHONUTF8=1 uv run supervisor_demo.py math      # 单测数学 Agent
PYTHONUTF8=1 uv run supervisor_demo.py research  # 单测研究 Agent
PYTHONUTF8=1 uv run supervisor_demo.py full      # Supervisor 复合任务
```

环境：uv 项目，langchain 1.3.14 / langgraph 1.2.9 / langgraph-supervisor 0.0.31 / langchain-tavily 0.2.18。key 在本目录 `.env`（已 gitignore）。

### 实跑踩到的两个新坑（课件没写）

**坑 A：`deepseek-chat` 模型名失效**（勘误 #7）。报错信息直接给出了答案：只接受 `deepseek-v4-pro` / `deepseek-v4-flash`。

**坑 B：DeepSeek v4 思考模式 × LangChain 工具调用 = 400 报错。**
- 现象：单测两个 Agent 都正常，一进 Supervisor 编排就报 `The reasoning_content in the thinking mode must be passed back to the API`
- 原因：v4 是混合思考模型，官方规定**带工具调用的多轮对话必须回传 `reasoning_content` 字段**，而 LangChain 的 ChatOpenAI 重建消息历史时把这个字段丢了（社区已知 bug，DeepSeek 官方文档 api-docs.deepseek.com/guides/thinking_mode 有说明）
- 解法（工具密集场景推荐）：关思考模式
  ```python
  model = ChatOpenAI(..., extra_body={"thinking": {"type": "disabled"}})
  ```
- 教训：**"单测通过 ≠ 编排后能跑"**——Supervisor 会来回搬运消息历史，消息序列化的边角问题只在多 Agent 场景暴露

### 实跑链路（26 条消息，印证第二部分概念）

```
Human 提问（GDP 复合任务）
→ supervisor 调工具 transfer_to_research_agent      ← handoff 就是一次 tool call！
→ research_agent 连做 4 轮共 6 次 tavily_search
→ transfer_back_to_supervisor（交还控制权）
→ supervisor 调工具 transfer_to_math_agent
→ math_agent：divide(2.32, 29.30) → multiply(结果, 100) = 7.93
→ transfer_back_to_supervisor
→ supervisor 整合输出最终表格
```

验证点：
- ✓ 职责分离真实发生：搜索全在 research_agent，计算全在 math_agent，supervisor 只路由和整合
- ✓ `add_handoff_back_messages=True` 让每次交接都在历史里留了 `Successfully transferred ...` 记录，调试时一眼看清控制权流向
- ✓ 搜出的 GDP 与 BEA 真实数据一致（29.30 万亿 / 2.32 万亿 / 7.93%），课件示例数字确实过时
- 观察：research_agent 搜了 6 次才罢休——这就是第四部分说的"成本叠加"，实际 LLM 调用次数远大于 N+1

### 3.5 `stream_mode="values"` 的隐藏坑：`chunk["messages"][-1]` 会漏消息（已用脚本实测验证）

课件 3.5 的打印方式：

```python
for chunk in graph.stream(inputs, stream_mode="values"):
    chunk["messages"][-1].pretty_print()
```

`stream_mode="values"` 每一步吐出的是**当前完整状态快照**（不是增量 diff）。这行代码隐含假设"每一步只新增一条消息"，但只要某一步里 `ToolNode` 一次性执行了同一条 AIMessage 里的多个 `tool_call`，这一步就会一口气新增 ≥2 条 ToolMessage，只打印 `[-1]` 会**默默漏掉前面那条，且不报错、不提示**。

**实测验证**（脚本：`ai-example/08_multi_agent/check_stream_values.py`，用一个会被同时调用 `add` 又 `multiply` 的问题强迫模型一步内调两次工具）：

```
--- step 0: messages 总数=1, 最后一条类型=HumanMessage ---
--- step 1: messages 总数=2, 最后一条类型=AIMessage ---
--- step 2: messages 总数=4, 最后一条类型=ToolMessage ---   ← 一步新增 2 条，[-1] 只会打到其中 1 条
--- step 3: messages 总数=5, 最后一条类型=AIMessage ---
```

我们自己的 `supervisor_demo.py` 用的是 `state["messages"][seen:]` 配合计数器切片、逐条打印新增消息（见下方 Python 知识点），天然避开了这个坑。这是**运行时才会暴露**的问题，光看课件代码文本看不出来。

---

## 四、Supervisor 模式的优缺点（用实跑数据量化，2026-07-25）

课件原文对"成本叠加"只说"往往是单 Agent 的数倍"，没给数字。用 `run_full.log`（3.4 节那次完整复合任务、共 26 条消息）实测统计：

```bash
grep -c "^================================== Ai Message" run_full.log   # 13
grep -A1 "^================================== Ai Message" run_full.log | grep "^Name:" | sort | uniq -c
  4 Name: math_agent
  6 Name: research_agent
  3 Name: supervisor
```

| 角色 | 实际 LLM 调用次数 | 具体在干什么 |
| --- | --- | --- |
| supervisor | 3 | 路由到 research_agent → 路由到 math_agent → 整合最终输出 |
| research_agent | 6 | 4 轮 `tavily_search` + 1 次中间小结 + 1 次交还控制权 |
| math_agent | 4 | `divide` → `multiply` → 生成答案 → 交还控制权 |
| **总计** | **13** | |

课件的"朴素估算"是 N+1（2 个 Worker + 1 个 Supervisor = 3 次），实测是 13 次，**约 4.3 倍**。差距主要来自 Worker 自己内部还要多轮调用（尤其 research_agent 反复搜索），这部分课件完全没提，是"成本叠加"被低估的真正原因。

延迟数字没测（没加计时埋点），这里不编——以后如果专门讲性能优化，可以加 `time.perf_counter()` 实测再补。

**优点**（课件原文 + 实跑印证）：
- 职责分离、故障域隔离：出错能精确定位到具体 Worker（见 3.4 实跑链路）
- 加新能力只需加一个 Worker，不用改已有 Agent 的 prompt/工具列表

**缺点**（课件原文 + 量化补充）：
- **成本叠加**：实测约 4.3 倍于朴素估算，且倍数不好预先估计——取决于 Worker 内部要跑几轮，Supervisor 自己控制不了
- **延迟叠加**：多次 LLM 调用是串行的（Supervisor 必须等 Worker 交还控制权才能继续），默认没有并行，原理同前面 `parallel_tool_calls` 那段
- **路由质量强依赖 Supervisor 的 prompt**：呼应勘误 #1——如果 `prompt` 参数传错（比如误传成 `system_prompt`），路由直接失灵且不报错，比崩溃更难排查

---

## 五、更多 Multi-Agent 模式（2026-07-25）

Supervisor 只是入门。5.1~5.4 本质上都是"Graph + Node + Edge + Handoff"这套已经吃透的骨架的变体，课件没给代码，只给了场景和类比：

| 模式 | 结构 | 适用场景 | 备注（查漏补缺） |
| --- | --- | --- | --- |
| 5.1 层级 Supervisor（Hierarchical） | CEO Agent → 技术/市场总监 → 一线 Agent | 大型复杂项目，子任务还能再拆 | 技术上就是"把一个已编译的 Supervisor 图当成另一个 Supervisor 的 Worker 节点"——LangGraph 的子图（subgraph）机制原生支持，不是新框架能力 |
| 5.2 管道模式（Pipeline） | A（搜索）→B（分析）→C（生成报告） | 流程固定的线性任务 | 不需要任何路由/handoff 工具，直接 `add_edge` 写死顺序即可，是几种模式里最简单的一种 |
| 5.3 对抗模式（Debate） | 正方⟷反方辩论 → 裁判 Agent 评判 | 需要多角度论证的决策场景 | 靠一个循环条件边控制"吵几轮"，再路由到裁判节点收尾；LangGraph 没有专门的 debate 包，是手写 StateGraph |
| 5.4 群聊模式（Group Chat） | 多 Agent 自由交流 → Moderator 汇总协调 | 需要多 Agent 自由讨论、发散创意 | **课件没写代码是对的**：经核实，LangGraph 生态**没有官方的"群聊"包**（不像 Swarm 有 `langgraph-swarm`）。这是 AutoGen 的招牌范式（`GroupChat`/`GroupChatManager`），LangGraph 里要做等价效果只能自己手写一个 StateGraph，本质是"Supervisor 路由 + 循环边"的组合，不是独立的框架原语 |

### 5.5 群体协作与 Swarm（去中心化交接）—— 代码经实测验证，courseware 这段写得对

和前四种不同，Swarm **有真实存在的官方包**：[`langgraph-swarm`](https://github.com/langchain-ai/langgraph-swarm-py)（PyPI 可装，`langchain-ai` 官方维护）。

**核心区别（课件原文，属实）：** 群聊靠 Moderator 统一协调；Swarm 没有持续负责路由的中央节点——当前 Agent 自己判断"接下来该谁来"，直接把控制权 `Command(goto=...)` 交给下一个 Agent。

**验证方式：** 没有直接改现有项目依赖，而是用 `uv run --with langgraph-swarm` 拉一个临时环境跑，不污染 `08_multi_agent` 的 `pyproject.toml`。

真实签名（`inspect.signature` 实测，非文档转述）：

```python
create_handoff_tool(*, agent_name: str, name: str | None = None, description: str | None = None) -> BaseTool
create_swarm(agents: list[Pregel], *, default_active_agent: str, state_schema=SwarmState, context_schema=None, **deprecated_kwargs) -> StateGraph
```

对照课件 5.5 的代码骨架：`create_handoff_tool(agent_name=..., description=...)`、`create_swarm([...], default_active_agent=...).compile()` —— **参数名、必填项、用法全部对得上**。这是这份课件里少有的"代码骨架照抄能跑"的段落，不用改。

**实跑验证**（脚本：`ai-example/08_multi_agent/swarm_check.py`，仿课件结构做了一个 greeter_agent ⇄ math_agent 的最小 Swarm）：

```
>>> swarm 编译成功，节点： ['__start__', 'greeter_agent', 'math_agent']
[HumanMessage] 你好，另外帮我算一下 3+5
[ToolMessage] name=transfer_to_math_agent content=Successfully transferred to math_agent
[AIMessage] name=math_agent content=3 + 5 = 8 ✅ ...
```

跑通，`create_agent`（来自 `langchain.agents`，我们全程都在用的那个）可以直接塞进 `create_swarm`，不需要换成旧的 `langgraph.prebuilt.create_react_agent`。

**一处需要存疑标注的地方**：搜索到的一份社区资料提示，`langgraph-swarm` 的某些高级能力（checkpointer/human-in-the-loop 相关）官方口径建议优先用 `create_react_agent` 而非 `langchain.agents.create_agent`，但我没能直接抓取到 GitHub/reference.langchain.com 原始页面核实这句话的准确表述（WebFetch 被这两个域名挡了）。**以我们自己刚才的实测为准**：基础的 handoff + 单轮工具调用场景下 `create_agent` 完全没问题；如果以后要接 checkpointer 做多轮记忆，建议先小范围试一下再上生产。

**代价（课件原文，属实且值得强调）：** 去中心化换来灵活性，但更容易出现循环、上下文丢失、责任边界不清——每个 handoff 都要显式定义触发条件、可交接目标、最大步数、以及"什么时候算完成/该收敛"。默认应该先用 Supervisor 或 Pipeline，只有路径真的需要动态交接时才上 Swarm。

#### 追加实测：Swarm 的"循环"风险到底长什么样（脚本：`swarm_ping_pong.py`）

课件说"容易出现循环"没给机制，构造了一个 A/B 互相甩锅的最小复现：两个 Agent 的 `system_prompt` 都写死"不管收到什么都认为不归自己管，必须转给对方"，`recursion_limit=10` 防止真烧穿。

**实测结果（连跑 2 次，一致）：** 并没有出现真正的 A⇄B 死循环，而是撞上另一个更隐蔽的问题——

```
step 1: HumanMessage  帮我算一下 1+1
step 2: ToolMessage   transfer_to_agent_b（agent_a 真的调用了转交工具）
step 3: AIMessage     agent_b: "这个问题已经转交给 agent_a 来帮你处理，请稍等。"
（到此结束，没有 step 4，没有异常，图正常 END）
```

agent_a 老实执行了转交，但 agent_b 被指令强制要求"必须转回、绝不自answer"，却只在**文字里声称**"已转交"，并没有真的调用 `handoff_to_a` 工具。

**结论（两层风险，都是真的，但不是同一回事）：**
1. **真死循环（理论成立，未在本次实测复现）：** 如果两个 Agent 都**真的**每次都调用转交工具，会一路 A→B→A→B，直到撞上 `recursion_limit` 抛出 `GraphRecursionError`（LangGraph 通用机制，Supervisor 那节配置 `config={"recursion_limit": 50}` 用的是同一个安全阀，只是那次没触发）。**这种情况会报错、会崩，相对好发现。**
2. **静默失败（本次两次实测都复现了这个，比①更危险）：** 转交这个动作本质是"模型自己决定要不要发起的一次工具调用"，system_prompt 里写"必须调用"只是建议，模型完全可能只是嘴上说说、不动手。后果是图正常结束、**不报错、不提示**，用户的问题实际上没人回答。

**排查方法（问答讨论后确认）：**
- 风险①（真循环）：调用日志/trace 里能看到 `transfer_to_*` 工具被反复交替调用，消息数暴涨，最后有明确异常 `GraphRecursionError`——**日志能直接看出来**。
- 风险②（假转交/静默失败）：日志本身"看起来一切正常"（没有异常、没有反复调用），**光看调用日志不够**，必须做**语义/输出校验**——比如检查最终 AIMessage 的内容是否真的包含用户要的结果，而不是"已转交""请稍等"这类未完成话术；工程上可以额外接 LangSmith trace（呼应勘误表 #5）或加一层输出格式校验（比如要求最终答案必须匹配某种结构）来兜底。

---

## 🐍 Python 知识点

### 关键字参数与 keyword-only 参数（勘误 #4 的原理）

```python
def f(a, *, b):        # * 之后的参数只能用"名字=值"的方式传
    ...

f(1, b=2)   # ✓
f(1, 2)     # ✗ TypeError: f() takes 1 positional argument but 2 were given
```

- `f(1, 2)` 按位置传参；`f(a=1, b=2)` 按名字传参（关键字参数），顺序可乱
- 函数定义里的 `*` 是分界线：它右边的参数**必须**写名字。库作者用它防止调用者传错位置
- `draw_mermaid_png` 所有参数都在 `*` 之后，所以 `draw_mermaid_png("workflow.png")` 报错，必须写 `output_file_path="..."`
- LangChain 全家几乎所有 API 都推荐关键字传参（如 `create_agent(model=..., tools=...)`），可读性好、不怕位置错

### `@tool` 装饰器：一个函数如何变成"工具"（第二次学习）

```python
@tool
def add(a: float, b: float) -> float:
    """加法：将两个数字相加。"""
    return a + b
```

拆开看，每一行都在给 LLM"喂信息"：
- **`@tool` 是装饰器**：`@xxx` 写在函数头顶，等价于 `add = tool(add)`——把普通函数包装成带元数据的 Tool 对象。装饰器本质就是"接收函数、返回加工后的函数"的函数
- **类型注解 `a: float`**：Python 本身不强制检查它（传字符串也不会立刻报错），但 LangChain 读取它生成工具的参数 schema，告诉模型"这里要传数字"
- **docstring（函数体第一行的三引号字符串）**：Python 的函数说明文档，`help(add)` 能看到。LangChain 把它作为工具描述发给模型——**模型全靠这句话决定要不要调用这个工具**，所以 docstring 质量直接影响工具选择准确率
- `divide` 除零时返回字符串而不是抛异常——故意的：返回的错误文字会作为 ToolMessage 喂回模型，模型能读懂并自行调整；抛异常则会中断整个流程

### 其他随堂点

- `("human", "问题")` —— **元组（tuple）**：不可变的轻量序列。LangChain 约定 `(角色, 内容)` 二元组是消息的简写形式，等价于 `{"role": "user", "content": "问题"}`（rag 学习.md 里记过三种等价写法）
- `sys.argv` —— 命令行参数列表：`argv[0]` 是脚本名，`argv[1]` 是第一个参数。`sys.argv[1] if len(sys.argv) > 1 else "full"` 是三元表达式：有参数用参数，没有用默认值
- `load_dotenv()` —— 把 `.env` 文件的键值对读进环境变量，之后 `os.getenv("KEY")` 就能取到。key 不进代码、不进 git
- `for state in graph.stream(...)` —— `stream()` 返回**生成器**：不是一次算完返回列表，而是每产出一个状态就交给 for 循环处理一次，所以能"边执行边打印"
- 列表切片 `state["messages"][seen:]` —— 从下标 `seen` 取到末尾，配合计数器实现"只打印新增消息"

---

## 六、如何选择合适的模式（2026-07-25）

| 你的情况 | 推荐模式 | 原因 |
| --- | --- | --- |
| 任务明确，子任务少 | Supervisor | 架构简单，成本可控 |
| 任务复杂，子任务还有子任务 | 层级 Supervisor | 分层管理，职责更清晰 |
| 流程固定，步骤明确 | Pipeline | 按固定顺序执行，输出确定性高 |
| 需要多角度分析 | 对抗模式 | 正反论证，避免偏见 |
| 需要创意发散 | 群聊模式 | 多视角交互 |
| Agent 间需要动态互相转交 | Swarm | 去中心化，但需要更严格的循环和权限控制（呼应 `swarm_ping_pong.py` 实测） |

**决策优先级：** ① Supervisor 能解决的问题不升级到层级架构 ② 串行能满足需求不引入并行（呼应 `parallel_tool_calls` 深挖） ③ 从最简单方案起步，逐步演进。这三条不是空话，都对应前面实测过的具体代价。

**应用题讨论（子 Supervisor vs 内嵌 Pipeline，重要辨析）：** 场景是"审批"要拆成固定顺序的"初审→终审"两步，接入已有 Supervisor。正确判断分两层：
1. 先看内部：初审→终审顺序固定、不需要 LLM 做路由决策 → 内部结构应该是 **Pipeline**（`add_edge` 写死顺序），不是"子 Supervisor"（子 Supervisor 意味着内部还要有一个 LLM 做动态路由决策，这里不需要）
2. 再看外部：这个两步 Pipeline 编译后，作为**一个 Worker 节点**挂到现有 Supervisor 下即可，不需要额外一层路由 LLM 调用
3. 什么时候才需要真正的"层级 Supervisor"（子节点自己也要用 LLM 做路由）：如果审批本身要**动态决定走哪条路径**（比如"小额直接终审，大额要走双重终审"），子节点内部才真正需要一个自己的路由决策者，这时候上"子 Supervisor"才合理

结论：**先诊断子任务内部是否需要"动态路由决策"，再决定要不要引入带 LLM 的子 Supervisor**——如果只是固定顺序，套 Pipeline 更省成本（少一次 LLM 路由调用），完全符合决策优先级 ①③。

---

## 七、实战注意事项（2026-07-25，已对照前面实测内容核实）

项目地址：`git.miaoatech.cn/zeroleap/Multi-Agent.git`（本地已 clone 到 `C:/workspace/Multi-Agent/`）——**从这里开始，课件进入"仓库实战"阶段。**

这部分内容大半已经在前面的实测里验证过，快速过一遍，只标新东西和课件里重复出现的坑：

- **7.1 System Prompt 三要素**（你是谁/能做什么/不能做什么）：我们 `supervisor_demo.py` 里两个 Agent 的 system_prompt 写法就是照这个原则来的，已实践过，不再重复
- **7.2 最小化工具集**（3-5 个经验起点，非硬规则）：research_agent 只配 1 个搜索工具、math_agent 只配 3 个计算工具，已实践过
- **7.3 错误处理 / `recursion_limit`**：课件说"`create_agent` 没有 `max_iterations`，用 `recursion_limit` 兜底，超限抛 `GraphRecursionError`"——这正是我们 `swarm_ping_pong.py` 用来防止真烧穿的机制，实测过（虽然那次没触发，但机制本身是 LangGraph 稳定文档行为）
- **7.4 可观测性 / LangSmith**：课件代码 `LANGCHAIN_API_KEY = "ls-你的key"` 和前面勘误表 #5 是同一个问题（key 前缀该是 `lsv2_`，环境变量新命名是 `LANGSMITH_TRACING`/`LANGSMITH_API_KEY`），**同一个错误在课件里出现了两次**，不是笔误
- **7.5 运行方式**：`invoke`/`stream(stream_mode="values")`/`stream(stream_mode="debug")` 三种没问题，但示例代码里 `state["messages"][-1].pretty_print()` 又是 3.5 那个会漏消息的写法（**同一个 bug 在课件里也出现了两次**）——说明这不是笔误，是课件作者本身习惯这么写，真用的话记得改成切片累计打印
- **7.6 handoff 管理参数**：`output_mode`、`add_handoff_messages`、`add_handoff_back_messages`、`handoff_tool_prefix`、`parallel_tool_calls` 都是 `create_supervisor` 的真实参数（已用 `inspect.signature` 核实过，见勘误表下方"参数速查"），课件这段描述准确。新增知识点：Worker 返回结果建议约定最小契约（`status`/`summary`/`evidence`/`errors`/`next_action`），不要把整段网页原文或调试日志无筛选地传回 Supervisor——这个是第一部分"上下文堆积"局限在 handoff 层面的具体应对
- **7.7 生产三类风险**（系统设计缺陷 / 协作失调 / 任务验证失效）：概念性框架，三层定位没有事实性错误，值得记住的是"至少要为成功率、路由准确率、无效工具调用率、循环次数、延迟、token 成本、人工接管率建立指标"——这是一份可以直接抄去做监控看板的清单
- **7.8 MCP 与 A2A**：概念性区分，MCP 管"Agent↔工具/资源"标准化，A2A 管"Agent↔Agent 跨服务通信"，都不解决任务拆解/路由/上下文/验证问题——只是连接层，没有事实错误

## 八、总结

课件总结表的"成本：稍高（至少 N+1 次，实际往往数倍）"——这次不是空话，是我们自己用 `run_full.log` 量化过的（13 次 / 3 次朴素估算 ≈ 4.3x，见第四部分）。一句话总结：单 Agent 在工具选择、上下文管理、问题定位上出现系统性困难时，才是拆 Multi-Agent 的信号；不是"能拆就拆"。

---

## 九、仓库实战：`C:/workspace/Multi-Agent/`（纯 openai SDK 手写版，2026-07-25）

不用 LangGraph/LangChain,用户自己 `uv init` 起了个骨架,把课件同款三种模式（Supervisor/Pipeline/Debate）用原生 `openai` SDK 手写了一遍。价值在于：能看清 `create_agent`/`create_supervisor` 这些框架 API 在底层到底帮你做了什么。

**文件地图：**

```
config.py     → 配置（key/model/MAX_TOOL_ROUNDS）
tools.py      → 4 个真实工具函数 + 手写 OpenAI function schema（本次未细讲）
agent.py      → Agent 基类：手写 ReAct 工具循环
orchestrator.py → 3 个模式的执行引擎，普通函数调用把 Agent 串起来
server.py     → FastAPI + SSE，把执行过程实时推给前端
```

### 9.1 `agent.py`：手写的 ReAct 循环 = `create_agent` 的底层实现

核心是 `Agent.chat()`（第 18-65 行）：

```python
for round_i in range(MAX_TOOL_ROUNDS):          # MAX_TOOL_ROUNDS=999
    resp = self.client.chat.completions.create(model=..., messages=full_messages,
                                                 tools=self.tools, tool_choice="auto")
    msg = resp.choices[0].message
    if not msg.tool_calls:                       # 没有工具调用 = 最终答案
        return msg.content or ""
    full_messages.append(msg)                     # 有工具调用，先存 assistant 消息
    for tc in msg.tool_calls:
        result = execute_tool(tc.function.name, json.loads(tc.function.arguments))
        full_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
return "[达到最大工具调用轮次限制]"
```

对应关系：

| LangGraph（`create_agent`） | 这里（手写） |
| --- | --- |
| 内部自动生成的图循环 | `for round_i in range(MAX_TOOL_ROUNDS)` |
| `ToolMessage` | `{"role": "tool", "tool_call_id":..., "content":...}` |
| `recursion_limit`（整个图的步数上限，超限抛 `GraphRecursionError`） | `MAX_TOOL_ROUNDS`（单个 Agent 自己的轮次上限，超限**不报错**，返回占位字符串） |

第 20 行 `full_messages = [{"role": "system", "content": self.system_prompt}] + messages` 是个关键证据：`system_prompt` 在这里只是一段普通文本被塞进消息列表，**`chat()` 后面的代码完全没有任何一行去读取/解析/校验这段文本里写的要求**——prompt 里写"必须委托给专家""不要编造数据"这些话，代码层面没有强制力，跟 `swarm_ping_pong.py` 实测过的问题是同一类。

### 9.2 `orchestrator.py`：9 个 Agent 实例 + 3 个执行引擎函数

三种模式各自配一套独立的 Agent 实例（Supervisor 用 `SUPERVISOR`/`RESEARCHER`/`CODER`，Pipeline 用 `PIPELINE_SEARCHER`/`PIPELINE_ANALYZER`/`PIPELINE_REPORTER`，Debate 用 `DEBATE_PRO`/`DEBATE_CON`/`DEBATE_JUDGE`），互不共用。

`run_supervisor`/`run_pipeline`/`run_debate` 结构完全一样：**纯 Python 顺序调用 + 字符串拼接**，不是图：

```python
research_result = RESEARCHER.chat([{"role": "user", "content": f"...{supervisor_analysis}"}], emit=agent_emit)
coder_result     = CODER.chat([{"role": "user", "content": f"...{research_result}"}], emit=agent_emit)
```

**和 LangGraph Supervisor 的本质区别**：LangGraph 里所有 Agent 共享同一份 `messages` state；这里每次 `.chat()` 调用都是从零开始的独立对话（`agent.py` 第 20 行每次新建 `full_messages`），下一个 Agent 只能看到"上一个 Agent 输出的文本片段"，看不到更早的完整历史。而且**全程没有任何 `if` 判断**——不管上一步结果是正常输出还是"抱歉没搜到"，代码都会原样往下传，四/三/五步永远跑完，不会提前退出或换路径。这跟 LangGraph 能加条件边动态改变路径是本质差异。

三种模式实测调用次数（数 `.chat()` 调用）：Supervisor 4 次（SUPERVISOR×2 + RESEARCHER + CODER）、Pipeline 3 次（无"队长"整合步骤，最省）、Debate 5 次（PRO×2 + CON×2 + JUDGE）。

**闭包知识点**（第 130-145 行 `_emit`/`agent_emit`）：

```python
def run_supervisor(query, emit=None):
    trace_id = str(uuid.uuid4())[:8]
    def agent_emit(event_type, data):        # 闭包：捕获外层 trace_id 和 emit
        data["trace_id"] = trace_id
        data["mode"] = "supervisor"
        _emit(emit, "agent_event", data)
    SUPERVISOR.chat(..., emit=agent_emit)
```

`agent_emit` 定义在 `run_supervisor` 内部，能直接访问外层的 `trace_id`/`emit`，不需要显式传参。好处：`agent.py` 的 `chat()` 调用 `emit(...)` 时完全不需要知道自己是哪个模式、哪个 trace——这些标签由闭包自动补上。

### 9.3 `server.py`：FastAPI + 线程/队列桥接同步与异步

**FastAPI 基础**（用户 Python 基础薄弱，随堂补的）：FastAPI 是 Python 的 Web 服务器框架，`@app.get("/api/presets")`/`@app.post("/api/execute")` 是装饰器，注册"HTTP 方法 + 路径 → 处理函数"的映射；`ExecuteRequest(BaseModel)` 靠 `pydantic` 自动解析校验请求体 JSON；FastAPI 本身不监听端口，真正跑起来靠最后一行 `uvicorn.run(app, ...)`。

**要解决的问题**：`run_supervisor` 等函数是同步阻塞的（内部是普通 `openai` SDK 调用），但 FastAPI 接口是 `async def` 跑在事件循环里——直接同步调用会卡住整个事件循环。

**解法**（第 56-91 行）：把阻塞的 LLM 调用丢进 `threading.Thread` 跑；一个同步的 `emit` 回调往 `asyncio.Queue` 塞事件；异步的 `stream()` 生成器 `await queue.get()` 消费队列、`yield` 成 SSE 消息推给前端；线程跑完在 `finally` 里塞一个 `None` 作为结束信号。

**实测发现的真 bug（已核实，非猜测）**：第 60 行 `queue.put_nowait(event)` 是从**后台线程**（不是事件循环所在线程）调用的。[官方文档](https://docs.python.org/3/library/asyncio-queue.html)明确写着 `asyncio.Queue` **不是线程安全的**，规范做法是 `loop.call_soon_threadsafe(queue.put_nowait, event)`。目前能跑是因为 CPython GIL 保护了内存安全、且场景简单，但不保证——原理上事件循环可能正睡在 `epoll`/`select` 里，`call_soon`（`put_nowait` 内部间接调用）只是把回调塞进列表，并不会像 `call_soon_threadsafe` 那样往一个专门的 "self-pipe" socket 写字节去真正唤醒它。换 `uvloop` 或并发量上去后更容易暴露成事件丢失/delayed。

**Python 知识点补充：事件循环为什么怕跨线程直接操作**——事件循环单线程跑一个 `while True`，靠 `epoll`/`select` 等待"有事发生"，等待期间是睡着的。`call_soon()` 默认调用者就是它自己所在线程，不需要叫醒谁。跨线程调用时回调确实被塞进了列表，但没人去"戳醒"正在睡觉的循环——`call_soon_threadsafe()` 多做的那一步，就是往一个循环本身也在监听的 socket 写一个字节，真正把它叫醒。

---

## 参考来源

- create_supervisor 官方参数表：https://reference.langchain.com/python/langgraph-supervisor/supervisor/create_supervisor
- create_agent (LangChain 1.0)：https://reference.langchain.com/python/langchain/agents/factory/create_agent 、https://docs.langchain.com/oss/python/langchain/agents
- TavilySearch（新）：https://reference.langchain.com/python/langchain-tavily/tavily_search/TavilySearch
- Lost in the Middle：arXiv:2307.03172
- 工具数量 vs 准确率：LongFuncEval (Kate et al. 2025)；Tool RAG 实验（RAG-MCP 2025）
- GDP：BEA https://www.bea.gov/news/2025/gross-domestic-product-4th-quarter-and-year-2024-advance-estimate 、https://en.wikipedia.org/wiki/List_of_U.S._states_and_territories_by_GDP
- asyncio.Queue 线程安全：https://docs.python.org/3/library/asyncio-queue.html （"This class is not thread safe"）

## ⏭ 下次继续

- [x] 第三部分：代码实战 ✅ 2026-07-25 跑通（`ai-example/08_multi_agent/`），含 `stream_mode="values"` 消息丢失坑（3.5）
- [x] 随堂 Python：`@tool` 装饰器、类型注解、docstring、元组、生成器、切片 ✅
- [x] 第四部分：优缺点，成本叠加已用 `run_full.log` 量化为 13 次实际调用（≈4.3x 朴素估算）✅
- [x] 第五部分：五种模式（层级/管道/对抗/群聊/Swarm）✅ 2026-07-25，Swarm 代码用 `swarm_check.py` 实测验证可跑，死循环风险用 `swarm_ping_pong.py` 实测
- [x] 第六部分：模式选型指南 ✅ 2026-07-25，含"子 Supervisor vs 内嵌 Pipeline"辨析
- [x] 第七部分：生产注意事项 ✅ 2026-07-25，课件里 LangSmith key 命名错误、`[-1]` 漏消息 bug 各出现了两次
- [x] 第八部分：总结 ✅ 2026-07-25
- [x] **仓库实战**：`C:/workspace/Multi-Agent/` ✅ 2026-07-25 讲完 `agent.py`（手写 ReAct 循环）+ `orchestrator.py`（9 个 Agent 实例 + 3 个执行引擎，字符串拼接非共享 state，无条件分支）+ `server.py`（线程/队列桥接同步异步，含 FastAPI 基础扫盲），详见第九部分。发现并核实了一个真 bug：`server.py` 第 60 行跨线程直接调 `asyncio.Queue.put_nowait` 不是线程安全写法
- [ ] `tools.py`（4 个工具函数的具体实现 + 手写 OpenAI function schema）和 `index.html`（前端）还没细讲，用户表示核心架构已理解，暂不确定是否要继续 —— 下次开始前先问用户要不要看这两个
- [ ] 复跑日志：`ai-example/08_multi_agent/run_full.log` 存了完整 26 条消息；`swarm_check.py` / `swarm_ping_pong.py` / `check_stream_values.py` 是验证脚本，不是正式练习代码
