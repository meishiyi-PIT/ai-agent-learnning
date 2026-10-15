# ReAct 与 Plan-and-Execute 复习笔记
> 对应课件：`2. LangGraph实战：ReAct和Plan-and-Execute.md`

---

## 一、在知识体系中的位置

**前置依赖（学这一篇前必须先懂）**

- **08 笔记**：State / Node / Edge、条件边、Checkpointer、MessagesState。本篇的 ReAct 循环、Plan-and-Execute 三节点图，本质上都是"08 里的积木"的具体搭法。
- **Function Calling**：模型返回 `tool_calls`，你执行工具再把结果喂回去，这套协议是 ReAct 能"边想边做"的底层机制。
- **Python 中级语法**：生成器/迭代器（`for chunk in ... stream(...)`）、`Tuple`/`Union` 类型标注、`Pydantic BaseModel`。第五节会补。

**本篇讲了什么（课件骨架）**

```
一、ReAct              Think → Act → Observe 循环；create_agent 一键封装
二、Plan-and-Execute    Planner → Executor → Replanner 三节点图；大小模型分工
三、流式处理             values / updates / messages 三种 stream_mode
四、断点与人工介入        interrupt_before/after、update_state、专用人工节点
五、状态回溯             get_state_history、checkpoint_id、"类 Git 分支"
```

**往后连到哪里**

```
本篇（ReAct / Plan-and-Execute）
  └─→ 10 Middleware：ModelCallLimitMiddleware 就是给 ReAct 死循环
  │     装的"工程刹车"；HumanInTheLoopMiddleware 是把本篇手写的
  │     interrupt_before 封装成了声明式配置
  └─→ Multi-Agent 编排：Plan-and-Execute 的 Executor 本身就是一个
        ReAct Agent——"Agent 当工具用"的思路会在多智能体章节反复出现
```

一句话定位：**08 讲的是"图怎么搭"，本篇讲的是"用图搭出来的两种最常见的 Agent 范式该怎么选、怎么落地生产（流式+人工确认+回溯）"。**

---

## 二、核心知识点精讲

### 1. ReAct：Think → Act → Observe

ReAct = **Reasoning + Acting**。核心循环：想一步（要不要调工具？调哪个？）→ 调工具 → 看结果 → 再想……直到判断"可以交差了"。

这和"一锤子买卖"式的 `模型问 → 模型答` 的本质区别是：**Agent 有机会根据中间结果调整下一步**。

**新手最常踩的坑：死循环**（比如把翻译结果又当成待翻译内容再翻一遍）。课件给出一个很值得记住的判断标准：

> **Think 决定"做什么"，重试上限决定"做多久"。两者各司其职，谁也不能替代谁。**

单纯加"最大重试次数"只是治标——治本的办法是让 Think 步骤真正判断"任务是否已完成"，这是 prompt 工程的问题，不是工程兜底能解决的。（第十篇会看到，工程兜底其实也有专门的 Middleware 来做——`ModelCallLimitMiddleware`，但它和"让模型自己想清楚该不该停"是两件事，互补不互替。）

**用 `create_agent` 搭 ReAct**：

```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=[get_weather, calculator],
    system_prompt="...规则说明...",
)
response = agent.invoke({"messages": [{"role": "user", "content": "..."}]})
```

`create_agent` 内部自动构建了"LLM 节点 + 工具节点 + 条件边"这套循环——本质上就是把 08 篇学的 State/Node/Edge 按 ReAct 的模式预先搭好了。如果自己手搭，对应关系是：

```
Think  → 一个调用模型的 Node（agent_node）
Act    → ToolNode（工具执行节点）
Observe→ Act 执行完后回到 agent_node 的那条边（形成循环）
"要不要调工具"→ 条件边（router），检查最后一条消息有没有 tool_calls
```

08 篇实战里的"天气助手"就是手搭版的 ReAct，和这里 `create_agent` 封装版是同一套东西的两种写法。

### 2. Plan-and-Execute：给 Agent 一张地图

ReAct 的短板：**没有全局视野**，走到哪个路口才决定往哪拐，容易在多步骤、有依赖关系的任务里"先写结论再发现漏了一步"。

Plan-and-Execute 用三个角色解决这个问题：

| 角色 | 干什么 | 本质 |
| --- | --- | --- |
| **Planner（规划器）** | 接收用户需求，输出有序步骤列表 | 一次 LLM 结构化输出调用 |
| **Executor（执行器）** | 只拿"当前第一步"当独立任务执行 | 通常就是一个 ReAct Agent |
| **Replanner（重规划器）** | 审视已完成步骤，决定"继续/调整/结束" | 一次 LLM 结构化输出调用 |

```
START → planner → executor → replanner ─(还有步骤)→ executor
                                    └──(任务完成)──→ END
```

**为什么这个模式天然支持"大小模型混用控成本"**：规划和重规划需要**全局判断**，得用强模型；执行阶段任务边界已经很明确，换小模型也能干。ReAct 做不到这种拆分，因为它的每一步都可能涉及方向性决策，没法把"决策"和"执行"分开换模型。

**State 设计的关键细节**：

```python
class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple[str, str]], operator.add]   # ★ 用 add 累加
    response: str
```

`past_steps` 用 `Annotated[..., operator.add]`，每次 Executor 返回 `{"past_steps": [(step, result)]}`，都会**追加**而不是覆盖，这样 Replanner 才能看到完整的执行历史。这正是 08 篇讲的 reducer 机制在这里的具体应用。

**用结构化输出约束 Planner/Replanner 的返回格式**：

```python
class Plan(BaseModel):
    steps: List[str] = Field(description="...")

class Act(BaseModel):
    # Union 类型确保 Replanner 只能二选一：要么直接回复，要么给新计划
    action: Union[Response, Plan] = Field(description="...")

planner_chain = planner_prompt | planner_llm.with_structured_output(Plan)
```

`with_structured_output` 让 LLM 直接输出符合 Pydantic 模型的对象，不用自己写 JSON 解析。`Union[Response, Plan]` 是这里的巧妙之处：靠类型系统保证 Replanner 的决策"要么结束、要么继续"，不会两头都占。

**控制流的收尾逻辑**：

```python
def should_continue(state: PlanExecute) -> Literal["executor", "__end__"]:
    if state.get("response"):   # response 字段非空 = Replanner 判断任务完成
        return END
    return "executor"
```

### 3. ReAct vs Plan-and-Execute：怎么选

| 维度 | ReAct | Plan-and-Execute |
| --- | --- | --- |
| 决策粒度 | 一次想一步 | 先出完整计划，再分批执行 |
| 全局视野 | 弱 | 强 |
| 适合场景 | 单轮问答、简单工具调用、用户意图不确定 | 多步调研、有依赖关系的任务 |

判断标准（课件原话，很实用）：**如果你自己对这个问题也要先在脑子里过一遍"先做什么再做什么"，那就用 Plan-and-Execute。**

### 4. 流式处理：三种 `stream_mode`

不管 ReAct 还是 Plan-and-Execute，`invoke()` 都得等全部跑完才返回，聊天产品里体验很差。`stream()` 提供三种粒度：

| 模式 | 每次拿到什么 | 类比 |
| --- | --- | --- |
| `values` | 完整的当前 State（全量快照） | 每步一张全景照片 |
| `updates` | 只有本节点新增的内容（增量） | 每次 commit 的 diff |
| `messages` | LLM 逐 token 输出 | 打字机效果 |

`messages` 模式返回的是 `(message, metadata)` 元组，且 `message.content` **经常是空字符串**（比如工具调用参数生成阶段没有可见文本）——这不是 bug，判断 `if message.content:` 是必须的，不是可选的。

### 5. 断点与人工介入（Human-in-the-Loop）

**基础断点**：`interrupt_before=[...]` / `interrupt_after=[...]`，编译时传入，依赖 checkpointer 才能在暂停后恢复。

```python
graph = builder.compile(checkpointer=memory, interrupt_before=["notify"])
...
for event in graph.stream(initial_input, config, stream_mode="values"):
    ...
# 图在 notify 前自动停住
graph.stream(None, config, stream_mode="values")   # 传 None = 从断点继续
```

**在断点处"偷天换日"**：用 `graph.update_state(config, {...})` 直接改 State 里的内容，再继续执行。典型用法是伪造一条 `ToolMessage`，让 Agent"以为"工具已经执行过、结果是这个。核心风险提示：`tool_call_id` 必须和原始 `tool_call` 的 id 对上，否则消息对不上号。

**规范化：设计专门的人工节点**——不是临时拦截，而是在图里放一个 `human_node`，配合状态里的 `ask_human` 标志位路由过去。关键技巧是 `graph.update_state(config, {...}, as_node="human_node")`：这个参数告诉 LangGraph"这次状态更新算作 human_node 节点的输出"，恢复执行时会跳过 human_node 内部逻辑，直接用注入的结果往下走。

### 6. 状态回溯：像 Git 分支一样"穿越"

`get_state_history(config)` 遍历某个 `thread_id` 下的所有历史快照（每个快照对应一个"超步"，倒序排列，`[0]` 最新）。

关键动作是**从任意历史快照继续执行**：

```python
graph.stream(None, target_snapshot.config, stream_mode="values")
```

注意传的是 `target_snapshot.config`（带着那个历史快照的 `checkpoint_id`），不是原来的 `config`。

**这个操作会产生一条新分支**，原来那条时间线上更靠后的快照不会被删除——和 Git branch 的行为一模一样：`git checkout` 到旧提交再往下开发，旧分支的提交历史还在，只是不在当前 HEAD 的路径上了。

---

## 三、课件勘误与更新

### 已确认

**1）`ChatOpenAI(model_name="deepseek-chat", ...)` —— 模型名已过时**

- 课件原文（1.3、4.2、4.3）：多处用 `model_name="deepseek-chat"` 初始化模型。
- 问题类型：**已过时**（课件写作时这是正确、可用的名字，不算错误）。
- 现状：DeepSeek 已发布 V4（2026-04-24），当前正式模型名是 `deepseek-v4-flash` / `deepseek-v4-pro`；旧名 `deepseek-chat` / `deepseek-reasoner` 作为兼容别名过渡使用，已于 **2026-07-24 15:59 UTC 正式下线**，之后请求会报错。应统一改用 `deepseek-v4-flash`（对应旧 `deepseek-chat` 的非思考模式）。
- 来源：https://api-docs.deepseek.com/updates/

**2）`from langchain_community.tools.tavily_search import TavilySearchResults` —— 已过时**

- 课件原文（2.4/2.5）：`from langchain_community.tools.tavily_search import TavilySearchResults`，用 `TavilySearchResults(max_results=3)` 构造搜索工具。
- 问题类型：**已过时**。
- 现状：该类自 LangChain 0.3.25 起已标记弃用，计划在 `langchain-community` 1.0 中移除（当前虽未强制删除，但官方明确建议迁移）。应改为：
  ```python
  # pip install -U langchain-tavily
  from langchain_tavily import TavilySearch
  search_tool = TavilySearch(max_results=3)
  ```
- 来源：https://python.langchain.com/api_reference/community/tools/langchain_community.tools.tavily_search.tool.TavilySearchResults.html

**3）`from langgraph.checkpoint.memory import MemorySaver` —— 已过时（但仍可用）**

- 课件原文（4.1、4.2、4.3、5.1）：断点与状态回溯章节统一用 `MemorySaver`；而 08 篇课件用的是 `InMemorySaver`。
- 问题类型：**已过时**（不是错误——两者目前都能跑）。
- 现状：`InMemorySaver` 是当前官方推荐的规范名称，`MemorySaver` 作为向后兼容别名保留、指向同一个类，但文档已统一用 `InMemorySaver` 举例。新代码建议直接写 `InMemorySaver`，避免学员误以为这是两个不同的类。
- 来源：https://reference.langchain.com/python/langgraph.checkpoint/memory/InMemorySaver

### 待核实

- `from langchain_community.chat_models import ChatTongyi` 的导入路径是否为当前 `langchain-community` 版本的标准写法（是否已迁移到独立的 `langchain-qwq` / `langchain-dashscope` 一类的专用包）——未逐版本核实，建议实操前以 `pip show langchain-community` 对应版本的文档为准。
- `interrupt_before` / `interrupt_after` 这种"静态断点"写法，与 LangGraph 后续推荐的 `from langgraph.types import interrupt` 动态中断函数（在节点内部按需调用，能带任意 payload 回传前端）之间的关系和取舍——课件只讲了静态断点这一种机制，二者是否有官方层面的新旧递进关系，未做进一步核实（详见第四节说明）。

---

## 四、课件没讲透的关键点补充

**1）ReAct 循环在图里的真实执行顺序**

课件的图示是 `Think → Act → Observe → Think → ...`，但如果换算成 LangGraph 的节点执行序列，真实顺序是：

```
agent(第1次思考=Think) → [条件边判断] → tools(Act，内部含Observe，即拿到ToolMessage)
→ agent(第2次思考，此时能看到上一步的ToolMessage=Think基于Observe) → ... → END
```

也就是说，"Observe"并不是一个独立的节点——它就是**工具节点执行完毕、ToolMessage 被追加进 State** 这个动作本身；下一次 agent 节点被调用时，模型在 `state["messages"]` 里"看见"这条 ToolMessage，就是"观察"的发生时刻。理解这点后再看 `create_agent` 的自动构图，就知道它其实只有两种节点（LLM 节点、工具节点）在循环，"三段论"是概念上的划分，不是图结构上的三个节点。

**2）interrupt_before/after 是"静态断点"，还有一种"动态中断"没讲**

课件全篇用的是 `interrupt_before=["node_name"]`——编译时就固定"在哪个节点前停"。LangGraph 还提供了 `interrupt()` 函数（`from langgraph.types import interrupt`），可以**写在节点函数内部**，运行到那一行时动态暂停并把任意数据传给外层（比如让人看到"具体要审批的参数是什么"），恢复时用 `Command(resume=用户填的值)` 把值传回 `interrupt()` 的返回处，继续往下执行同一个节点剩余的代码。两者的区别：
- 静态断点：粒度是"整个节点"，配置在 `compile()` 时。
- 动态中断：粒度可以精确到"节点内某一行"，能传自定义 payload，是第十篇 `HumanInTheLoopMiddleware` 底层大概率复用的机制。
不理解这层，会以为"人工确认"只有课件教的这一种写法。

**3）`update_state()` 和 checkpoint 分支的关系**

课件第五节讲"从任意快照继续执行会开新分支"，但没点破：`update_state()` 本质上也是在**当前最新快照之上再写一个新 checkpoint**。所以"断点处修改消息"（4.2 节）和"状态回溯"（第五节）其实是同一套底层机制的两种应用——前者是在最新快照上分叉，后者是在历史快照上分叉。

**4）Executor 内部的 ReAct 与外层 Plan-and-Execute 图是两层图**

容易忽略的一点：`executor_agent = create_agent(...)` 编译出来的是一整张（内部带循环的）子图，而 `execute_step` 节点每次调用它都是一次完整的 `.invoke()`（阻塞到它自己的 ReAct 循环跑完）。也就是说 Plan-and-Execute 的 `executor` 节点，从外层主图的视角看是"一个节点、一次调用"，但内部可能已经悄悄做了好几轮 Think-Act-Observe。调试超时问题时要记住这一层嵌套。

---

## 五、Python 随堂补基础

**① `Tuple` 类型标注 —— 固定长度、固定各位置类型的"元组"**
```python
from typing import Tuple, List
past_steps: List[Tuple[str, str]]   # 一个列表，每个元素是"(步骤描述, 执行结果)"这样的二元组
past_steps.append(("查天气", "北京晴天"))
```

**② `Union` —— "要么是这个类型，要么是那个类型"**
```python
from typing import Union
from pydantic import BaseModel

class Response(BaseModel): response: str
class Plan(BaseModel): steps: list[str]

class Act(BaseModel):
    action: Union[Response, Plan]   # action 要么是 Response 实例，要么是 Plan 实例，二选一
```

**③ Pydantic `BaseModel` + `Field` —— 声明"结构化输出"的形状**
```python
from pydantic import BaseModel, Field
class Plan(BaseModel):
    steps: list[str] = Field(description="需要顺序执行的步骤列表")
# with_structured_output(Plan) 会让 LLM 直接返回一个符合这个结构的 Plan 对象
```

**④ 生成器 / `for...in stream(...)` —— 一边产出一边处理**
```python
for chunk in agent.stream(inputs, stream_mode="updates"):
    for node_name, node_output in chunk.items():   # chunk 是 dict：{节点名: 产出}
        print(node_name, node_output)
```

**⑤ `end=""` 和 `flush=True` —— 实现打字机效果**
```python
print("你", end="", flush=True)   # 不换行、立即刷新到终端，配合逐 token 输出才不会"卡顿"
print("好", end="", flush=True)
# 输出：你好（连续、没有换行）
```

---

## 六、自测清单

**是什么**
1. ReAct 的三个步骤分别是什么？"Observe"在 LangGraph 的图结构里对应的是哪个动作？
2. Plan-and-Execute 的三个角色分别负责什么？
3. `stream_mode="values"` 和 `"updates"` 返回的内容有什么区别？
4. `interrupt_before` 和 `interrupt_after` 的区别是什么？
5. `get_state_history()` 返回的快照，对应的是"每个节点"还是"每个超步"？

**为什么**
6. 为什么"加个最大重试次数"治不好 Agent 死循环？真正该修的是哪一步？
7. 为什么 `past_steps` 要用 `Annotated[..., operator.add]` 而不是普通 `List`？
8. 为什么 Plan-and-Execute 能做到"规划用强模型、执行用弱模型"，而 ReAct 做不到？
9. 为什么 `stream_mode="messages"` 里判断 `if message.content:` 是必须的？
10. 为什么从历史快照 `stream(None, target_snapshot.config, ...)` 之后，原来的后续快照不会消失？

**什么时候用**
11. 什么场景该选 ReAct，什么场景该选 Plan-and-Execute？给出课件里的判断标准。
12. 什么场景该用"临时 update_state 拦截"，什么场景该"设计专门的人工节点"？
13. `exit_behavior`/工程兜底和"让 Think 步骤自己判断该不该停"，这两件事分别解决什么问题，能互相替代吗？

---

## 七、动手小练习

**练习 A（20 分钟）：给 ReAct Agent 加断点**
拿 08 篇实战里的"天气助手"（或本篇的天气+计算器 Agent），改成 `create_agent(..., checkpointer=InMemorySaver())` 之后手动搭一层 `interrupt_before=["tools"]`（如果用 `create_agent` 不方便加断点，改用手搭版的 `StateGraph` + `ToolNode`）。验证：模型决定调 `calculator` 时图会自动停住，`graph.get_state(config).next` 打印出 `('tools',)`，输入确认后才继续执行。

**练习 B（30 分钟）：三步 Plan-and-Execute 微缩版**
不接真实搜索 API，写一个"模拟调研"版本：Planner 用结构化输出拆出 3 个步骤（可以直接硬编码返回，跳过真实 LLM 调用），Executor 每次打印"正在执行第 N 步：xxx"并返回固定字符串结果，Replanner 用简单的 Python 逻辑判断"`len(past_steps) >= len(plan)` 就返回 Response，否则返回剩余 Plan"。跑通后用 `app.stream(inputs)` 观察每个节点的中间输出，体会"三节点循环直到 response 非空"的流转过程。
